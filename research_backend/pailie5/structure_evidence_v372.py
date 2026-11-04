"""Frozen evaluation, finite-domain certificates, and tamper-evident artifacts."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import numpy as np
from .math_language_v37 import validate_table
from .symbolic_operators_v30 import eval_expr_scalar
from .structure_ast_v372 import GRAMMAR, load_ast, table, validate_ast
from .structure_search_v372 import CellDataset, FrozenOperator


def evaluate_frozen(operator: FrozenOperator, data: CellDataset, *, allow_overlap=False) -> dict:
    """No fitting, parameter updates, threshold tuning or model selection here."""
    if not isinstance(operator, FrozenOperator) or not isinstance(data, CellDataset):
        raise ValueError("expected frozen operator and CellDataset")
    if type(allow_overlap) is not bool:
        raise ValueError("allow_overlap must be boolean")
    overlap = len(set(operator.source_pairs) & set(data.pairs))
    if overlap and not allow_overlap:
        raise ValueError("evaluation/training pair overlap")
    predicted = table(operator.expression)
    errors = sum(int(predicted[a, b]) != y for a, b, y in data.rows)
    return {"operator_id": operator.identity, "data_sha256": data.fingerprint,
            "errors": errors, "count": len(data.rows), "accuracy": 1-errors/len(data.rows),
            "overlapping_pairs": overlap, "refitted": False,
            "production_enabled": False, "predictive_advantage": "NOT_ESTABLISHED"}


def _properties(t: np.ndarray) -> dict:
    comm = next(([a, b] for a in range(10) for b in range(10) if t[a, b] != t[b, a]), None)
    assoc = next(([a, b, c] for a in range(10) for b in range(10) for c in range(10)
                  if t[int(t[a, b]), c] != t[a, int(t[b, c])]), None)
    identities = [e for e in range(10) if all(int(t[e, a]) == a == int(t[a, e]) for a in range(10))]
    return {"commutative": comm is None, "commutativity_counterexample": comm,
            "associative": assoc is None, "associativity_counterexample": assoc,
            "identities": identities,
            "all_rows_permutations": all(len(set(map(int, row))) == 10 for row in t),
            "all_columns_permutations": all(len(set(map(int, row))) == 10 for row in t.T),
            "scope": "candidate operation on exactly the digit domain 0..9"}


def certify_table(operator: FrozenOperator, truth) -> dict:
    """Read the reference table only after the expression has been frozen.

    Whole-domain equivalence is not a time-series holdout and confers no
    predictive evidence. Properties below always describe the candidate table.
    """
    if not isinstance(operator, FrozenOperator):
        raise ValueError("expected a frozen operator")
    target = validate_table(truth)
    predicted = table(operator.expression)
    independent = np.array([[eval_expr_scalar(operator.expression, a, b) % 10
                             for b in range(10)] for a in range(10)], dtype=np.uint8)
    if not np.array_equal(predicted, independent):
        raise ValueError("independent scalar and vector evaluators disagree")
    mismatch = np.argwhere(predicted != target)
    first = None
    if len(mismatch):
        a, b = map(int, mismatch[0])
        first = {"a": a, "b": b, "predicted": int(predicted[a, b]), "target": int(target[a, b])}
    nodes, depth = validate_ast(operator.expression)
    # Explicit, fixed shared codebook: 18 tokens at 5 bits, 40-bit header.
    # Exception coordinates use 7 bits; digit values use 4, with 7-bit count.
    formula_bits = 40 + 5 * nodes
    patched_bits = formula_bits + 7 + 11 * len(mismatch)
    return {"operator_id": operator.identity,
            "candidate_table_sha256": sha256(predicted.tobytes()).hexdigest(),
            "target_table_sha256": sha256(target.tobytes()).hexdigest(),
            "exact_on_all_100_pairs": len(mismatch) == 0,
            "whole_table_errors": len(mismatch), "first_mismatch": first,
            "independent_scalar_check": True, "properties": _properties(predicted),
            "nodes": nodes, "depth": depth,
            "coding_diagnostic": {"raw_table_bits": 400, "formula_bits": formula_bits,
                                  "formula_plus_exceptions_bits": patched_bits,
                                  "preferred": "formula" if patched_bits < 400 else "raw_table",
                                  "model": "shared 18-token codebook; 40-bit header; 7-bit exception count; 11 bits per exception",
                                  "is_minimum_description_proof": False},
            "production_enabled": False, "predictive_advantage": "NOT_ESTABLISHED"}


def _canonical(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode()


def save_operator(operator: FrozenOperator, destination: str | Path) -> None:
    payload = {"schema": "pl5-v372-frozen-operator-1", "operator": operator.to_dict()}
    card = {**payload, "integrity_sha256": sha256(_canonical(payload)).hexdigest()}
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Never silently overwrite a previously exported research artifact.
    with path.open('x', encoding='utf-8') as file:
        json.dump(card, file, ensure_ascii=False, indent=2, allow_nan=False)
        file.write('\n')


def load_operator(source: str | Path) -> FrozenOperator:
    path = Path(source)
    if path.stat().st_size > 65536:
        raise ValueError("operator artifact too large")
    try:
        card = json.loads(path.read_text('utf-8'))
        digest = card.pop('integrity_sha256')
        if sha256(_canonical(card)).hexdigest() != digest:
            raise ValueError("operator artifact integrity mismatch")
        if card['schema'] != 'pl5-v372-frozen-operator-1':
            raise ValueError("unknown operator schema")
        op = card['operator']
        if (op['grammar'] != GRAMMAR or op['production_enabled'] is not False or
                op['predictive_advantage'] != 'NOT_ESTABLISHED'):
            raise ValueError("unsupported or unsafe operator metadata")
        result = FrozenOperator(load_ast(op['expression']), op['source_data_sha256'],
                                tuple(tuple(p) for p in op['source_pairs']))
        if op['operator_id'] != result.identity:
            raise ValueError("operator identity mismatch")
        return result
    except (KeyError, TypeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("invalid operator artifact") from exc
