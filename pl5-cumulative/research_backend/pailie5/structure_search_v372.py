"""Training-only evolution of V3.0 integer expression trees.

The public fit API receives only observed cells, never a full target table.
Search novelty is relative to this finite grammar, not a claim of new mathematics.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import numpy as np

from .symbolic_operators_v30 import BINARY, eval_expr
from .structure_ast_v372 import (
    AST, ATOMS, GRAMMAR, validate_ast, normalize, describe, mutate, crossover,
)


def _digest(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class CellDataset:
    """Unique (a,b,value) observations for a 10x10 table, not lottery time series."""
    rows: tuple[tuple[int, int, int], ...]

    def __post_init__(self):
        if not isinstance(self.rows, (list, tuple)) or not 1 <= len(self.rows) <= 100:
            raise ValueError("expected 1..100 observed cells")
        validated = []
        for row in self.rows:
            if (not isinstance(row, (tuple, list)) or len(row) != 3 or
                    any(type(x) is not int or not 0 <= x <= 9 for x in row)):
                raise ValueError("cells require three plain integers in 0..9")
            validated.append(tuple(row))
        if len({(a, b) for a, b, _ in validated}) != len(validated):
            raise ValueError("duplicate input pair")
        object.__setattr__(self, "rows", tuple(sorted(validated)))

    @property
    def pairs(self):
        return tuple((a, b) for a, b, _ in self.rows)

    @property
    def fingerprint(self):
        return _digest(self.rows)


@dataclass(frozen=True)
class SearchConfig:
    seed: int = 20261102
    max_evaluations: int = 12000
    generations: int = 30
    population: int = 64
    beam_width: int = 24
    max_nodes: int = 11
    max_depth: int = 6
    complexity_penalty: float = 0.01

    def __post_init__(self):
        bounds = {
            "seed": (0, 2**32 - 1), "max_evaluations": (1, 50000),
            "generations": (1, 200), "population": (2, 256),
            "beam_width": (1, 128), "max_nodes": (3, 15), "max_depth": (2, 8),
        }
        for key, (low, high) in bounds.items():
            value = getattr(self, key)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"invalid {key}: expected integer {low}..{high}")
        if (type(self.complexity_penalty) not in (int, float) or
                not math.isfinite(self.complexity_penalty) or
                not 0 <= self.complexity_penalty <= 1):
            raise ValueError("invalid complexity_penalty")


@dataclass(frozen=True)
class FrozenOperator:
    expression: AST
    source_data_sha256: str
    source_pairs: tuple[tuple[int, int], ...]

    def __post_init__(self):
        validate_ast(self.expression)
        if (not isinstance(self.source_data_sha256, str) or len(self.source_data_sha256) != 64 or
                any(c not in '0123456789abcdef' for c in self.source_data_sha256)):
            raise ValueError("invalid training fingerprint")
        if (not isinstance(self.source_pairs, tuple) or not 1 <= len(self.source_pairs) <= 100 or
                any(not isinstance(p, tuple) or len(p) != 2 or
                    any(type(x) is not int or not 0 <= x <= 9 for x in p) for p in self.source_pairs) or
                len(set(self.source_pairs)) != len(self.source_pairs)):
            raise ValueError("invalid source input pairs")

    @property
    def identity(self):
        return _digest((GRAMMAR, self.expression))

    def to_dict(self):
        return {
            "grammar": GRAMMAR, "expression": self.expression,
            "description": describe(self.expression), "operator_id": self.identity,
            "source_data_sha256": self.source_data_sha256, "source_pairs": self.source_pairs,
            "production_enabled": False, "predictive_advantage": "NOT_ESTABLISHED",
        }


@dataclass(frozen=True)
class SearchResult:
    operator: FrozenOperator
    training_errors: int
    training_count: int
    evaluated_expressions: int
    distinct_integer_behaviors: int
    proposals: int
    config: SearchConfig
    trace: tuple[dict, ...]
    stop_reason: str

    def to_dict(self):
        # JSON roundtrip yields an independent, serializable snapshot.
        return json.loads(json.dumps({
            "operator": self.operator.to_dict(), "training_errors": self.training_errors,
            "training_count": self.training_count, "evaluated_expressions": self.evaluated_expressions,
            "distinct_integer_behaviors": self.distinct_integer_behaviors,
            "proposals": self.proposals, "config": asdict(self.config),
            "trace": self.trace, "stop_reason": self.stop_reason,
            "selection_used": "training_cells_only",
            "complexity": "node-count penalty; not proof of a minimum description",
        }, allow_nan=False))


@dataclass(frozen=True)
class _Candidate:
    expression: AST
    errors: int
    nodes: int
    score: tuple
    origin: str
    parents: tuple[str, ...]


def fit(training: CellDataset, config: SearchConfig = SearchConfig(), *,
        warm_starts: tuple[AST, ...] = ()) -> SearchResult:
    """Fit with a hard evaluation budget. No holdout parameter exists.

    Integer-vector deduplication (not final digit-table deduplication) preserves
    intermediate semantics when composing absdiff, xor, min, max and gcd.
    """
    if not isinstance(training, CellDataset) or not isinstance(config, SearchConfig):
        raise ValueError("fit accepts CellDataset training cells and SearchConfig only")
    if not isinstance(warm_starts, tuple) or len(warm_starts) > 64:
        raise ValueError("warm_starts must contain at most 64 ASTs")
    for tree in warm_starts:
        validate_ast(tree, max_nodes=config.max_nodes, max_depth=config.max_depth)
    rng = np.random.default_rng(config.seed)
    indices = np.array([10*a+b for a, b, _ in training.rows], dtype=int)
    targets = np.array([y for _, _, y in training.rows], dtype=np.int64)
    seen_expressions: set[AST] = set()
    archive: dict[bytes, _Candidate] = {}
    evaluated = 0
    proposals = 0
    trace = []

    def budget_available():
        return evaluated < config.max_evaluations and proposals < config.max_evaluations * 8

    def put(tree, origin, parents=()):
        nonlocal evaluated, proposals
        if not budget_available(): return
        proposals += 1
        try:
            validate_ast(tree, max_nodes=config.max_nodes, max_depth=config.max_depth)
            tree = normalize(tree)
        except ValueError:
            return
        if tree in seen_expressions: return
        seen_expressions.add(tree)
        evaluated += 1
        try:
            raw = eval_expr(tree)
        except (ValueError, OverflowError):
            return
        nodes, _ = validate_ast(tree)
        predicted = np.mod(raw[indices], 10)
        errors = int(np.count_nonzero(predicted != targets))
        score = (errors + config.complexity_penalty * nodes, errors, nodes, repr(tree))
        row = _Candidate(tree, errors, nodes, score, origin, tuple(parents))
        signature = raw.astype('<i8', copy=False).tobytes()
        if signature not in archive or score < archive[signature].score:
            archive[signature] = row

    def ranked():
        return sorted(archive.values(), key=lambda x: x.score)

    def snapshot(stage, generation):
        best = ranked()[0]
        trace.append({"stage": stage, "generation": generation,
                      "best_expression": best.expression, "training_errors": best.errors,
                      "nodes": best.nodes, "origin": best.origin, "parents": best.parents,
                      "evaluated_expressions": evaluated, "proposals": proposals})

    # Always reserve the first charged evaluation for a safe fallback.
    put(("a",), "safe_baseline")
    for tree in warm_starts: put(tree, "warm_start")
    for tree in ATOMS: put(tree, "atom")
    # Generic primitive basis; none of these trees depends on the target labels.
    basis = sorted({normalize(("binary", op, left, right)) for op in BINARY
                    for left in ATOMS[:2] for right in ATOMS[:2]}, key=repr)
    for tree in basis: put(tree, "primitive_basis")
    for left in ATOMS:
        for right in ATOMS:
            for op in BINARY: put(("binary", op, left, right), "atom_composition")
    snapshot("bootstrap", 0)
    # Exhaustion is a valid small-budget result; even budget=1 returns a model.
    if not budget_available():
        stop_reason = "evaluation_or_proposal_budget"
    elif ranked()[0].errors == 0 and ranked()[0].nodes <= 3:
        stop_reason = "short_exact_training_fit"
    else:
        # Compose grammar fragments, rather than enumerate a preset formula list.
        expansions = [("binary", op, left, right) for left in basis
                      for right in (*ATOMS, *basis) for op in BINARY]
        rng.shuffle(expansions)
        phase_budget = max(evaluated, int(config.max_evaluations * 0.55))
        for tree in expansions:
            if not budget_available() or evaluated >= phase_budget: break
            put(tree, "grammar_composition", (_digest(tree[2]), _digest(tree[3])))
        snapshot("grammar_composition", 0)
        stop_reason = "generation_limit"
        for generation in range(1, config.generations + 1):
            if not budget_available():
                stop_reason = "evaluation_or_proposal_budget"
                break
            elites = ranked()[:config.beam_width]
            # Keep a few target-independent fragments to reduce premature collapse.
            for _ in range(config.population * 4):
                if not budget_available(): break
                parent = elites[int(rng.integers(len(elites)))].expression
                mode = int(rng.integers(4))
                if mode == 0:
                    other = (*ATOMS, *basis)[int(rng.integers(len(ATOMS) + len(basis)))]
                    op = BINARY[int(rng.integers(len(BINARY)))]
                    tree = ("binary", op, parent, other) if int(rng.integers(2)) else ("binary", op, other, parent)
                    origin, parents = "guided_composition", (_digest(parent), _digest(other))
                elif mode == 1:
                    tree = mutate(parent, rng, max_nodes=config.max_nodes, max_depth=config.max_depth)
                    origin, parents = "subtree_mutation", (_digest(parent),)
                elif mode == 2:
                    other = elites[int(rng.integers(len(elites)))].expression
                    tree = crossover(parent, other, rng, max_nodes=config.max_nodes, max_depth=config.max_depth)
                    origin, parents = "subtree_crossover", (_digest(parent), _digest(other))
                else:
                    base = basis[int(rng.integers(len(basis)))]
                    if validate_ast(base)[0] > config.max_nodes: base = ("a",)
                    tree = mutate(base, rng, max_nodes=config.max_nodes, max_depth=config.max_depth)
                    origin, parents = "diversity_mutation", (_digest(base),)
                put(tree, origin, parents)
            snapshot("evolution", generation)
    best = ranked()[0]
    return SearchResult(
        FrozenOperator(best.expression, training.fingerprint, training.pairs),
        best.errors, len(training.rows), evaluated, len(archive), proposals,
        config, tuple(trace), stop_reason,
    )
