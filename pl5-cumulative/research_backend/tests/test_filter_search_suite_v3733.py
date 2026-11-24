"""V3.7.33 synthetic filter search suite: bounded, exact, audit-friendly."""
import json

import pytest

from pailie5.filter_search_suite_v3733 import (
    DOMAIN, EVALUATIONS, FAMILIES, SEEDS, make_inventory, run_benchmark,
)


def test_fixed_suite_repeatable_paired_budget_and_all_families():
    first = run_benchmark(seeds=(17, 18), evaluations=12)
    assert first == run_benchmark(seeds=(17, 18), evaluations=12)
    assert first["family_order"] == list(FAMILIES)
    assert first["total_trials"] == 8
    assert first["candidate_evaluations_per_arm_and_trial"] == 12
    assert first["oracle_evaluations_per_family"] == 256
    assert sum(first["paired_exact_optimum_table"].values()) == 8
    assert len(set(first["input_inventory_hashes"].values())) == len(FAMILIES)
    assert not first["historical_outcomes_read"]
    assert not first["historical_coverage_measured"]
    assert not first["algorithm_superiority_claim"]
    assert not first["predictive_advantage_claim"]
    for study in first["full_studies"]:
        comp = study["comparison"]
        assert comp["evaluation_budget_per_arm"] == 12
        assert comp["oracle"]["evaluations"] == 256
        assert comp["inventory_sha256"] == first["input_inventory_hashes"][study["family"]]
        assert len(comp["trials"]) == 2
        for trial in comp["trials"]:
            assert trial["arms"]["random"]["evaluations"] == 12
            assert trial["arms"]["ga_cs"]["evaluations"] == 12
            assert sum(trial["arms"]["ga_cs"]["stage_evaluations"].values()) == 12
    assert json.loads(json.dumps(first)) == first


def test_family_invariants_include_adversarial_no_feasible_and_redundant_masks():
    for family in FAMILIES:
        p = make_inventory(family)
        assert p.universe_size == DOMAIN
        assert len(p.masks) == 8
        assert p.target == 64 and p.max_survivors == 128
    redundant = make_inventory("redundant")
    assert redundant.masks[0] == redundant.masks[2]
    assert redundant.masks[1] == redundant.masks[3]
    conflicting = make_inventory("conflicting")
    assert conflicting.masks[0] & conflicting.masks[1] == 0
    nested = make_inventory("nested")
    assert nested.masks[-1].bit_count() == 100


def test_suite_rejects_bad_protocol_without_running():
    for kwargs in (
        {"seeds": ()}, {"seeds": (1, 1)}, {"seeds": (True,)},
        {"seeds": [1]}, {"evaluations": 0},
        {"evaluations": 1025}, {"evaluations": True},
    ):
        with pytest.raises(ValueError):
            run_benchmark(**kwargs)
    with pytest.raises(ValueError):
        make_inventory("unknown")
