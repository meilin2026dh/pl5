"""V3.7.59 exact signed-literal filtering grammar on ten frozen Boolean rules.

One new *grammar*, not ten new operators: each rule may be required true,
required false, or omitted. Exact full-assignment atoms certify attainable
cardinalities. Historical outcomes are read only after all atoms are frozen.
"""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from historical_operator_walkforward_v3756 import (
    DOMAIN, WARMUP, TEST_WINDOWS, RULE_NAMES, masks, all_coalitions,
    verified_rows,
)
from coverage_floor_v3758 import exact_target_floor

N = len(RULE_NAMES)
FULL_ASSIGNMENT = (1 << N) - 1
FULL_DOMAIN = (1 << DOMAIN) - 1
CAP = 100


def mask_hash(bitmap):
    return sha256(bitmap.to_bytes(DOMAIN // 8, "little")).hexdigest()


def signature_for_id(n, raw_masks):
    return sum((((mask >> n) & 1) << j)
               for j, mask in enumerate(raw_masks))


def compile_atoms(raw_masks):
    """Construct each exact Boolean signature by intersection of signed masks."""
    negatives = [FULL_DOMAIN ^ mask for mask in raw_masks]
    atoms = []
    for signature in range(1 << N):
        kept = FULL_DOMAIN
        for j in range(N):
            kept &= raw_masks[j] if (signature >> j) & 1 else negatives[j]
            if not kept:
                break
        atoms.append(kept)
    return tuple(atoms)


def audit():
    raw = masks()
    if len(raw) != N:
        raise AssertionError("frozen ten-rule inventory changed")
    atoms = compile_atoms(raw)

    # Independent direct per-ID predicate-signature oracle.
    signatures = [signature_for_id(n, raw) for n in range(DOMAIN)]
    counts = Counter(signatures)
    for s, atom in enumerate(atoms):
        if atom.bit_count() != counts[s]:
            raise AssertionError("atom count vs direct signature oracle mismatch")
    if sum(a.bit_count() for a in atoms) != DOMAIN:
        raise AssertionError("atomic partition does not conserve domain")
    union = 0
    for atom in atoms:
        if atom & union:
            raise AssertionError("two signed atoms overlap")
        union |= atom
    if union != FULL_DOMAIN:
        raise AssertionError("partition union is not the universe")

    # Crucially, all atom choices, full bitmap digests and capped support are
    # decided before opening historical targets.
    nonempty = [(s, m) for s, m in enumerate(atoms) if m]
    eligible = [(s, m) for s, m in nonempty if m.bit_count() <= CAP]
    eligible_union = 0
    for _, m in eligible:
        eligible_union |= m
    selected = min(eligible, key=lambda row: (row[1].bit_count(), row[0]))
    selected_sig, selected_mask = selected
    selected_k = selected_mask.bit_count()
    # This frozen smallest-cardinality test arm is a domain-only mechanical
    # choice; it is NOT a retained-history optimized rule.
    positive_only = all_coalitions(raw)
    target_rows = verified_rows()[WARMUP:]
    if len(target_rows) != TEST_WINDOWS:
        raise AssertionError("historical evaluation window changed")
    history = []
    for issue, digits in target_rows:
        number = int(digits)
        signature = signatures[number]
        atomic_k = counts[signature]
        old_sig, positive_k, _ = exact_target_floor(number, raw, positive_only)
        if signature != old_sig or atomic_k > positive_k:
            raise AssertionError("signed grammar floor must not exceed positive-only")
        if not ((atoms[signature] >> number) & 1):
            raise AssertionError("history identity excluded by its own atom")
        history.append({
            "issue": issue,
            "exact_signature": signature,
            "signed_minimum_k": atomic_k,
            "positive_only_minimum_k": positive_k,
            "meets_k100_in_an_existing_signed_atom": atomic_k <= CAP,
            "retained_by_frozen_minimum_k_arm": bool((selected_mask >> number) & 1),
        })
    covered = sum(row["meets_k100_in_an_existing_signed_atom"]
                  for row in history)
    if covered != sum(int((eligible_union >> int(digits)) & 1)
                      for _, digits in target_rows):
        raise AssertionError("direct target floor vs eligible atom union mismatch")

    return {
        "schema": "pl5-signed-literal-cubes-v3759-1",
        "source": "INTERNAL/AI_AUTHORED_FROZEN_TEN_RULE_GRAMMAR",
        "historical_source": "RETROSPECTIVE_CROSSCHECKED_TRANSCRIPTS_NOT_AUTHENTICATED",
        "domain": DOMAIN,
        "frozen_rule_count": N,
        "signed_literal_choices_per_rule": ["KEEP_TRUE", "KEEP_FALSE", "OMIT"],
        "full_assignment_atoms": len(atoms),
        "nonempty_atoms": len(nonempty),
        "empty_atoms": len(atoms) - len(nonempty),
        "nonempty_k_at_most_100_atoms": len(eligible),
        "eligible_union_k": eligible_union.bit_count(),
        "eligible_union_sha256": mask_hash(eligible_union),
        "smallest_nonempty_atom_k": min(m.bit_count() for _,m in nonempty),
        "largest_nonempty_atom_k": max(m.bit_count() for _,m in nonempty),
        "domain_only_frozen_arm": {
            "signature": selected_sig, "k": selected_k,
            "candidate_sha256": mask_hash(selected_mask),
            "historical_covered": sum(r["retained_by_frozen_minimum_k_arm"]
                                      for r in history),
        },
        "historical_windows": len(history),
        "historical_signed_atoms_k100_coverable": covered,
        "historical_signed_atoms_k100_removed": TEST_WINDOWS - covered,
        "historical_positive_only_k100_coverable": sum(
            row["positive_only_minimum_k"] <= CAP for row in history),
        "per_window_retrospective_floor": history,
        "hypothetical_uniform_expected_eligible_union_coverage":
            TEST_WINDOWS * eligible_union.bit_count() / DOMAIN,
        "historical_rule_selection_prohibited": True,
        "historical_target_used_to_construct_masks": False,
        "new_signed_grammar_tested_not_validated_for_future": True,
    }


class SignedCubeTests(unittest.TestCase):
    def test_toy_signed_atoms_and_oracle(self):
        # Domain of 4, two masks; one point for each of 4 Boolean signatures.
        small_full = 15
        old = (0b1010, 0b1100)
        atoms = []
        for s in range(4):
            a = small_full
            for j, m in enumerate(old):
                a &= m if (s >> j) & 1 else (small_full ^ m)
            atoms.append(a)
        self.assertEqual(sorted(x.bit_count() for x in atoms), [1,1,1,1])
        self.assertEqual(sum(atoms), 15)
        for n in range(4):
            s = sum(((m >> n) & 1) << i for i,m in enumerate(old))
            self.assertEqual((atoms[s] >> n) & 1, 1)

    def test_exact_domain_and_non_leaking_historical_floor(self):
        r = audit()
        self.assertEqual(r["full_assignment_atoms"], 1024)
        self.assertEqual(r["historical_windows"], 20)
        self.assertGreater(r["nonempty_k_at_most_100_atoms"], 0)
        self.assertEqual(r["historical_positive_only_k100_coverable"], 0)
        self.assertEqual(
            r["historical_signed_atoms_k100_coverable"] +
            r["historical_signed_atoms_k100_removed"], 20)
        for row in r["per_window_retrospective_floor"]:
            self.assertLessEqual(row["signed_minimum_k"],
                                 row["positive_only_minimum_k"])

    def test_deterministic_replay(self):
        self.assertEqual(audit(), audit())


if __name__ == "__main__":
    if not unittest.TextTestRunner().run(
        unittest.defaultTestLoader.loadTestsFromTestCase(SignedCubeTests)
    ).wasSuccessful():
        raise SystemExit(1)
    print("V3759_SIGNED_JSON=" + json.dumps(audit(), sort_keys=True))
