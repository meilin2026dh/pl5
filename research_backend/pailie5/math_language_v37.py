"""V3.7 finite-algebra language discovery research prototype.

Searches train-observed 10x10 binary tables for short algebraic descriptions,
verifies exact reconstruction, and evaluates transfer on an unseen target table.
No lottery predictive advantage is implied.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
import numpy as np

DIGITS = np.arange(10, dtype=np.uint8)
A, B = np.meshgrid(DIGITS, DIGITS, indexing="ij")

@dataclass(frozen=True)
class Expression:
    family: str
    parameters: tuple[int, ...]

    def evaluate(self) -> np.ndarray:
        if self.family == "affine":
            u, v, w = self.parameters
            return ((u * A.astype(int) + v * B.astype(int) + w) % 10).astype(np.uint8)
        if self.family == "xor":
            shift, = self.parameters
            return (((A ^ B).astype(int) + shift) % 10).astype(np.uint8)
        if self.family == "distance":
            shift, = self.parameters
            return ((np.abs(A.astype(int) - B.astype(int)) + shift) % 10).astype(np.uint8)
        raise ValueError("unknown family")

    def description(self) -> str:
        return f"{self.family}({','.join(map(str, self.parameters))})"


def candidates():
    for u in range(10):
        for v in range(10):
            for w in range(10):
                yield Expression("affine", (u, v, w))
    for s in range(10):
        yield Expression("xor", (s,))
        yield Expression("distance", (s,))


def validate_table(table) -> np.ndarray:
    x = np.asarray(table)
    if x.shape != (10, 10) or not np.issubdtype(x.dtype, np.integer) or np.any((x < 0) | (x > 9)):
        raise ValueError("expected a 10x10 digit operation table")
    return x.astype(np.uint8)


def properties(table) -> dict:
    x = validate_table(table)
    commutative = bool(np.array_equal(x, x.T))
    associative = all(int(x[int(x[a,b]),c]) == int(x[a,int(x[b,c])])
                      for a in range(10) for b in range(10) for c in range(10))
    identities = [e for e in range(10) if all(int(x[e,a]) == a and int(x[a,e]) == a for a in range(10))]
    return {"commutative": commutative, "associative": associative, "identities": identities}


def discover(table, observed_mask=None) -> dict:
    """Find a short expression on observed cells, then certify on all cells.

    The certification step is deliberately *not* a lottery holdout evaluation.
    """
    x = validate_table(table)
    mask = np.ones((10,10), dtype=bool) if observed_mask is None else np.asarray(observed_mask)
    if mask.shape != (10,10) or mask.dtype != bool or not np.any(mask):
        raise ValueError("invalid observed mask")
    selected = None
    for expr in candidates():
        y = expr.evaluate()
        errors = int(np.count_nonzero((x != y) & mask))
        key = (errors, len(expr.description()), expr.description())
        if selected is None or key < selected[0]:
            selected = (key, expr, y)
    _, expr, y = selected
    exact = bool(np.array_equal(x,y))
    return {"expression":expr.description(), "observed_errors":selected[0][0],
            "unseen_errors":int(np.count_nonzero((x!=y)&~mask)),
            "exact_certified":exact, "table_sha256":sha256(x.tobytes()).hexdigest(),
            "properties":properties(x), "candidate_count":1020,
            "predictive_advantage":"NOT_ESTABLISHED"}


def transfer(source_table, target_table) -> dict:
    source = discover(source_table)
    target = discover(target_table)
    return {"source":source, "target":target,
            "shared_expression":source["expression"] == target["expression"] and
                                source["exact_certified"] and target["exact_certified"],
            "predictive_advantage":"NOT_ESTABLISHED"}
