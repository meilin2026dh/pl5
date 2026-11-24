"""V3.7.36 scalable inclusion-minimal pruning of frozen filter conjunctions.

A 60-rule limit is supported without 2^m exhaustive enumeration.
The result is a *locally irredundant* (inclusion-minimal) filter family:
it preserves the exact final bitmap, and deleting ANY remaining rule
changes that bitmap. It is not generally minimum-cardinality globally.
Only static candidate masks are used; no historical outcome data.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .ga_cs_optimizer_v3715 import SearchProblem

SCHEMA = "pl5-scalable-filter-irredundant-pruning-v3736-1"
MAX_RULES = 60
MAX_UNIVERSE = 100_000


def _digest(mask: int, width: int) -> str:
    return sha256(mask.to_bytes(width, "little")).hexdigest()


def _intersection(masks: tuple[int, ...], hard: int, selected: tuple[int, ...]) -> int:
    answer = hard
    for index in selected:
        answer &= masks[index]
    return answer


def prune_inclusion_minimal(
    problem: SearchProblem, *, priority: tuple[int, ...] | None = None
) -> dict:
    """Delete redundant optional rules in a fixed, auditable priority order.

    The priority is a permutation of every rule index; earlier indices get
    first chance to be discarded. Output is deterministic given the input.
    The hard mask is never optional. This algorithm is O(m^2) bitset ANDs
    in the worst case, instead of an exponential subset search.
    """
    if not isinstance(problem, SearchProblem):
        raise ValueError("validated SearchProblem required")
    m = len(problem.masks)
    if not 1 <= m <= MAX_RULES or problem.universe_size > MAX_UNIVERSE:
        raise ValueError("pruning restricted to 1..60 static rules and <=100000 identities")
    if priority is None:
        priority = tuple(range(m - 1, -1, -1))
    if (not isinstance(priority, tuple) or len(priority) != m
            or any(type(i) is not int or i < 0 or i >= m for i in priority)
            or len(set(priority)) != m):
        raise ValueError("priority must be a permutation of all rule indices")

    hard = ((1 << problem.universe_size) - 1
            if problem.hard_mask is None else problem.hard_mask)
    full = _intersection(problem.masks, hard, tuple(range(m)))
    remaining = list(range(m))
    removed = []
    # Only one monotonically shrinking pass is needed: if a rule could not
    # be removed with a larger rule family, removing other constraints later
    # cannot make it redundant. Rechecking below certifies the result.
    for index in priority:
        trial = tuple(i for i in remaining if i != index)
        if _intersection(problem.masks, hard, trial) == full:
            removed.append(index)
            remaining = list(trial)

    chosen = tuple(remaining)
    recomputed = _intersection(problem.masks, hard, chosen)
    if recomputed != full:
        raise AssertionError("pruning changed the candidate set")

    witnesses = []
    for index in chosen:
        without = _intersection(problem.masks, hard,
                                tuple(i for i in chosen if i != index))
        difference = without & ~full
        if difference == 0:
            raise AssertionError("selected family is not inclusion-minimal")
        representative = (difference & -difference).bit_length() - 1
        witnesses.append({
            "rule_name": problem.rule_names[index],
            "rule_index": index,
            "new_candidates_if_removed": difference.bit_count(),
            "first_restored_candidate_index": representative,
        })

    width = (problem.universe_size + 7) // 8
    provenance = sha256()
    provenance.update(f"v3736|{problem.universe_size}|{m}|".encode("ascii"))
    provenance.update(hard.to_bytes(width, "little"))
    for name, mask in zip(problem.rule_names, problem.masks):
        encoded = name.encode("utf8")
        provenance.update(len(encoded).to_bytes(4, "little"))
        provenance.update(encoded)
        provenance.update(mask.to_bytes(width, "little"))
    return {
        "schema": SCHEMA,
        "inventory_sha256": provenance.hexdigest(),
        "hard_mask_sha256": _digest(hard, width),
        "original_full_bitmap_sha256": _digest(full, width),
        "simplified_bitmap_sha256": _digest(recomputed, width),
        "exact_full_bitmap_preserved": True,
        "optional_rule_count_before": m,
        "optional_rule_count_after": len(chosen),
        "removed_rule_indices": removed,
        "removed_rule_names": [problem.rule_names[i] for i in removed],
        "kept_rule_indices": list(chosen),
        "kept_rule_names": [problem.rule_names[i] for i in chosen],
        "chosen_bitmap_survivors": full.bit_count(),
        "removal_priority": list(priority),
        "retained_rule_necessity_witnesses": witnesses,
        "all_remaining_rules_individually_necessary": True,
        "global_minimum_rule_count_proven": False,
        "bound": "INCLUSION_MINIMAL_NOT_MINIMUM_CARDINALITY",
        "historical_outcomes_read": False,
        "historical_coverage_measured": False,
        "limits": [
            "A deterministic inclusion-minimal family is not guaranteed to have globally fewest rules.",
            "Pruning applies only to static frozen Boolean conjunctions and the declared hard-mask population.",
            "The bitmap is unchanged, but execution cost may not be minimized and is not measured here.",
            "Retained-rule witnesses are candidate IDs in the declared universe, not external historical evidence.",
        ],
    }
