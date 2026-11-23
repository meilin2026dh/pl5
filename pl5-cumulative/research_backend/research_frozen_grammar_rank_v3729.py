"""V3.7.29: independent *rank-consistency* feasibility certificates for frozen grammars.

Proof scope: existence of SOME mod-10 linear combination of the grammar's
whitelisted feature vectors that exactly fits the OBSERVED TRAINING cells.

For an integer matrix A and labels y, A c = y (mod 10) is feasible iff
both systems (mod 2) and (mod 5) are feasible, by the Chinese Remainder
Theorem. Over prime fields, a system is feasible exactly when
rank(A) == rank([A|y]). This oracle checks ranks WITHOUT calling the
frozen algorithm's coefficient solver or reading holdout labels.

Consequences:
- Every frozen V3.7.25 stage and every whitelisted V3.7.26 predicate is
  enumerated. If all fail, no exact fit exists IN THESE FIXED BANKS on
  the provided train sample; increasing their search time cannot help.
- A feasible training span does not imply correct validation/holdout or
  a unique mathematical law, and says nothing about lottery prediction.
- The candidate grammar itself is imported from the frozen baseline;
  a future grammar change requires a new explicit version, not silently
  reinterpreting these results.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np

from pailie5.structure_search_v372 import CellDataset
from pailie5.open_grammar_v3725 import _features, _stage_names
from pailie5.gate_induction_v3726 import _full_bank, predicate_specs

EVIDENCE_GRADE = "INTERNAL_SYNTHETIC_OR_SEEN_DEVELOPMENT_ONLY"
PRIMES = (2, 5)
SCHEMA = "pl5-v3729-frozen-grammar-training-feasibility-1"


def rank_prime(matrix: np.ndarray, prime: int) -> int:
    """Exact Gaussian elimination modulo 2 or 5; no floating point rank."""
    if prime not in PRIMES:
        raise ValueError("unsupported prime field")
    x = np.asarray(matrix)
    if x.ndim != 2 or not np.issubdtype(x.dtype, np.integer):
        raise ValueError("integer 2-D matrix required")
    a = (x.astype(np.int64) % prime).copy()
    m, n = a.shape
    row = 0
    for col in range(n):
        pivot = next((k for k in range(row, m) if a[k, col] != 0), None)
        if pivot is None:
            continue
        if pivot != row:
            a[[row, pivot]] = a[[pivot, row]]
        a[row] = (a[row] * pow(int(a[row, col]), -1, prime)) % prime
        for other in range(row + 1, m):
            if a[other, col] != 0:
                a[other] = (a[other] - int(a[other, col]) * a[row]) % prime
        row += 1
        if row == m:
            break
    return row



def contradiction_witness(matrix: np.ndarray, labels: np.ndarray, prime: int) -> dict | None:
    """Construct a public-training-only, directly verifiable non-fit proof.

    If A*c=y is impossible over F_p, find row weights w with w*A=0 and
    w*y=1 (mod p). The latter equality disproves every possible c.
    All indices refer solely to the ordered TRAINING rows. The proof is
    sufficient to verify independently, without rerunning the solver.
    """
    if prime not in PRIMES:
        raise ValueError("unsupported prime field")
    x = np.asarray(matrix)
    y = np.asarray(labels)
    if (x.ndim != 2 or y.ndim != 1 or len(y) != x.shape[0]
            or x.shape[0] == 0 or not np.issubdtype(x.dtype, np.integer)
            or not np.issubdtype(y.dtype, np.integer)):
        raise ValueError("integer training matrix and matching labels required")
    m, n = x.shape
    # Row operations on [A | y | I] accumulate a witness in the last m cols.
    work = np.column_stack((x.astype(np.int64) % prime,
                            y.astype(np.int64) % prime,
                            np.eye(m, dtype=np.int64)))
    row = 0
    for col in range(n):
        pivot = next((k for k in range(row, m) if work[k, col] != 0), None)
        if pivot is None:
            continue
        if pivot != row:
            work[[row, pivot]] = work[[pivot, row]]
        work[row] = work[row] * pow(int(work[row, col]), -1, prime) % prime
        for other in range(m):
            if other != row and work[other, col]:
                work[other] = (work[other] - int(work[other, col]) * work[row]) % prime
        row += 1
        if row == m:
            break
    for k in range(row, m):
        if not np.any(work[k, :n]) and work[k, n] != 0:
            scale = pow(int(work[k, n]), -1, prime)
            weights = (work[k, n+1:] * scale) % prime
            witness = {
                "prime": prime,
                "weighted_target_mod_prime": 1,
                "nonzero_row_weights": [[int(i), int(c)] for i, c in
                                        enumerate(weights) if c],
            }
            if not verify_contradiction_witness(x, y, witness):
                raise RuntimeError("invalid modular contradiction witness")
            return witness
    return None


def verify_contradiction_witness(matrix: np.ndarray, labels: np.ndarray, witness: dict) -> bool:
    """Public and pure verifier for the two modular identities in a witness."""
    if not isinstance(witness, dict) or set(witness) != {
            "prime", "weighted_target_mod_prime", "nonzero_row_weights"}:
        return False
    prime = witness["prime"]
    if type(prime) is not int or prime not in PRIMES:
        return False
    if type(witness["weighted_target_mod_prime"]) is not int or witness[
            "weighted_target_mod_prime"] != 1:
        return False
    x = np.asarray(matrix)
    y = np.asarray(labels)
    if (x.ndim != 2 or y.ndim != 1 or x.shape[0] != len(y)
            or not np.issubdtype(x.dtype, np.integer)
            or not np.issubdtype(y.dtype, np.integer)):
        return False
    terms = witness["nonzero_row_weights"]
    if not isinstance(terms, list) or not terms or len(terms) > len(y):
        return False
    weights = np.zeros(len(y), dtype=np.int64)
    previous = -1
    for term in terms:
        if (not isinstance(term, list) or len(term) != 2 or
                any(type(v) is not int for v in term)):
            return False
        idx, coeff = term
        if not previous < idx < len(y) or not 1 <= coeff < prime:
            return False
        previous = idx
        weights[idx] = coeff
    return (not np.any((weights @ x.astype(np.int64)) % prime) and
            int(weights @ y.astype(np.int64)) % prime == 1)

def feasibility_certificate(matrix: np.ndarray, labels: np.ndarray) -> dict:
    x = np.asarray(matrix)
    y = np.asarray(labels)
    if (x.ndim != 2 or not np.issubdtype(x.dtype, np.integer)
            or y.ndim != 1 or not np.issubdtype(y.dtype, np.integer)
            or x.shape[0] != y.shape[0] or x.shape[0] == 0):
        raise ValueError("integer training matrix and matching labels required")
    expanded = np.column_stack((x, y))
    ranks = {}
    possible = True
    witness = None
    for p in PRIMES:
        base = rank_prime(x, p)
        aug = rank_prime(expanded, p)
        if aug < base or aug > base + 1:
            raise AssertionError("modular augmented rank consistency violation")
        inconsistent = aug != base
        ranks[str(p)] = {"rank_basis": base, "rank_augmented": aug,
                         "inconsistent": inconsistent}
        if inconsistent and witness is None:
            witness = contradiction_witness(x, y, p)
            if witness is None:
                raise RuntimeError("rank detected contradiction but no witness exists")
        possible = possible and not inconsistent
    return {"exact_mod10_training_fit_exists": bool(possible),
            "ranks_mod_primes": ranks,
            "contradiction_witness": witness}


def rank_audit(training: CellDataset) -> dict:
    if not isinstance(training, CellDataset):
        raise TypeError("training must be typed CellDataset")
    idx = np.asarray([10*a + b for a, b, _ in training.rows], dtype=np.int64)
    y = np.asarray([value for _, _, value in training.rows], dtype=np.int64)
    f = _features()
    stages = _stage_names()
    v25 = []
    for stage, names in stages.items():
        bank = np.column_stack([f[k][idx] for k in names])
        v25.append({"stage": stage, "basis_columns": len(names),
                    **feasibility_certificate(bank, y)})
    v26 = []
    for pred in (None,) + predicate_specs():
        names, whole_bank = _full_bank(pred)
        v26.append({"predicate": pred, "basis_columns": len(names),
                    **feasibility_certificate(whole_bank[idx], y)})
    return {
        "schema": SCHEMA,
        "grammar_ids": ["v3725_ring", "v3726_gate"],
        "train_cells": len(training.rows),
        "v3725_stages": v25,
        "v3726_predicates": v26,
        "v3725_any_train_fit": any(row["exact_mod10_training_fit_exists"] for row in v25),
        "v3726_any_train_fit": any(row["exact_mod10_training_fit_exists"] for row in v26),
        "holdout_labels_seen": False,
        "validation_labels_seen": False,
        "evidence_grade": EVIDENCE_GRADE,
        "external_blind_verified": False,
        "lottery_predictive_advantage": "NOT_ESTABLISHED",
    }


def read_public_train(public_json: str | Path) -> CellDataset:
    """Strict public V3.7.25 input reader; ignores validation and commitment."""
    path = Path(public_json)
    if path.stat().st_size > 500_000:
        raise ValueError("oversized public task")
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict) or record.get("schema") != "pl5-v3725-ring-grammar-1:challenge":
        raise ValueError("invalid public challenge")
    rows = record.get("train")
    if not isinstance(rows, list) or len(rows) != 48:
        raise ValueError("expected 48 public train cells")
    return CellDataset(tuple(tuple(row) for row in rows))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError("study evidence cannot overwrite prior result")
    cert = rank_audit(read_public_train(args.public))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(cert, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    print(json.dumps({"v3725_train_feasible": cert["v3725_any_train_fit"],
                      "v3726_train_feasible": cert["v3726_any_train_fit"],
                      "evidence_grade": cert["evidence_grade"]}))
