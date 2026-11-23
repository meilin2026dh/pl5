"""V3.7.35 exact static-filter pruning: independent brute-force oracles."""
from itertools import permutations

import pytest

from pailie5.ga_cs_optimizer_v3715 import SearchProblem
from pailie5.filter_equivalent_pruning_v3735 import exact_equivalent_pruning


def p(masks, *, n=8, hard=None):
    return SearchProblem(masks=tuple(masks),
        rule_names=tuple(f"r{i}" for i in range(len(masks))),
        universe_size=n, target=1, min_survivors=1,
        max_survivors=n, hard_mask=hard)


def mask_for(problem, subset):
    bits = (1 << problem.universe_size) - 1 if problem.hard_mask is None else problem.hard_mask
    for i, mask in enumerate(problem.masks):
        if subset & (1 << i):
            bits &= mask
    return bits


def oracle(problem):
    full = (1 << len(problem.masks)) - 1
    want = mask_for(problem, full)
    cores = [s for s in range(full + 1) if mask_for(problem, s) == want]
    def cost(s):
        active = tuple(i for i in range(len(problem.masks)) if s & (1 << i))
        options = []
        for order in permutations(active):
            bits = ((1 << problem.universe_size) - 1 if problem.hard_mask is None
                    else problem.hard_mask)
            checks = 0
            for i in order:
                checks += bits.bit_count()
                bits &= problem.masks[i]
            options.append(checks)
        return min(options)
    return min(cores, key=lambda s: (s.bit_count(), cost(s), s)), cores, cost


def test_duplicate_rule_prunes_to_one_and_preserves_bitmap():
    prob = p((0b00001111, 0b00001111))
    result = exact_equivalent_pruning(prob)
    assert result["chosen_genome"] == 1
    assert result["chosen_rule_names"] == ["r0"]
    assert result["removed_rule_names"] == ["r1"]
    assert result["inclusion_minimal_core_count"] == 2
    assert result["essential_across_all_equivalent_subsets"] == []
    assert result["exact_bitmap_preserved"]
    assert result["scalar_checks_saved"] == 4
    assert mask_for(prob, result["chosen_genome"]) == mask_for(prob, 3)


def test_independent_rules_have_unique_core_with_no_spurious_removal():
    prob = p((0b11111110, 0b11111101))
    r = exact_equivalent_pruning(prob)
    assert r["chosen_genome"] == 3
    assert r["inclusion_minimal_core_count"] == 1
    assert r["essential_across_all_equivalent_subsets"] == ["r0", "r1"]
    assert r["scalar_checks_saved"] == 0


def test_hard_mask_can_render_every_optional_rule_redundant():
    prob = p((0b00001111, 0b11110000), hard=0b00000011)
    r = exact_equivalent_pruning(prob)
    assert r["chosen_genome"] == 2
    assert r["all_rules_survivors"] == 0
    assert mask_for(prob, r["chosen_genome"]) == 0
    assert r["candidate_count_changed"] is False


def test_exhaustive_small_instance_matches_independent_permutation_oracle():
    prob = p((0b11111000, 0b01101101, 0b01011111, 0b00110110))
    result = exact_equivalent_pruning(prob)
    selected, equivalents, cost = oracle(prob)
    assert result["chosen_genome"] == selected
    assert result["exactly_equivalent_subset_count"] == len(equivalents)
    assert result["simplified_minimum_scalar_checks"] == cost(selected)
    assert result["original_all_rules_minimum_scalar_checks"] == cost(15)
    assert result == exact_equivalent_pruning(prob)


def test_full_100k_static_space_prunes_a_genuine_duplicate():
    a = (1 << 10000) - 1
    b = sum(((1 << 1000) - 1) << (i * 10000) for i in range(10))
    c = sum(((1 << 100) - 1) << (i * 1000) for i in range(100))
    prob = p((a, b, c, a), n=100000)
    r = exact_equivalent_pruning(prob)
    assert r["all_rules_survivors"] == 100
    assert r["chosen_rule_count"] == 3
    assert r["scalar_checks_saved"] > 0
    assert mask_for(prob, r["chosen_genome"]) == mask_for(prob, 15)
    assert len(r["full_candidate_mask_sha256"]) == 64
    assert not r["historical_outcomes_read"]


def test_exact_bound_rejects_13_rules():
    with pytest.raises(ValueError, match="twelve"):
        exact_equivalent_pruning(p((255,) * 13))
