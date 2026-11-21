"""V3.7.7: induce finite unary transformations and compose them additively mod 10.

The learner sees only labeled training pairs. Its 20 latent digit values are
inferred from congruences u[a] + v[b] == y (mod 10). This is an inductive
factorization, not discovery of a previously unknown universal math operation.

No arbitrary code execution, outside data, or real-money filtering.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from hashlib import sha256
import json

from .structure_search_v372 import CellDataset


def _digest(value: object) -> str:
    return sha256(json.dumps(value, ensure_ascii=True, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class FrozenLatentPrimitive:
    u: tuple[int, ...]
    v: tuple[int, ...]
    components: tuple[int, ...]
    source_pairs: tuple[tuple[int, int], ...]
    source_sha256: str
    status: str
    constraint_conflicts: int
    training_errors: int | None

    @property
    def identity(self) -> str:
        return _digest(('pl5-v377-additive-latent-1', self.u, self.v,
                        self.components, self.source_sha256, self.status))

    def predict(self, a: int, b: int) -> int | None:
        if type(a) is not int or type(b) is not int or not 0 <= a <= 9 or not 0 <= b <= 9:
            raise ValueError('input digits must be plain integers in 0..9')
        # No prediction if the latent coordinates are not fully identifiable.
        if self.status != 'identified':
            return None
        return (self.u[a] + self.v[b]) % 10

    def to_dict(self) -> dict:
        return {'schema': 'pl5-v377-additive-latent-1', 'operator_id': self.identity,
                'unary_a': self.u, 'unary_b': self.v,
                'status': self.status, 'constraint_conflicts': self.constraint_conflicts,
                'training_errors': self.training_errors, 'source_sha256': self.source_sha256,
                'source_pairs': self.source_pairs,
                'components': self.components, 'production_enabled': False,
                'predictive_advantage': 'NOT_ESTABLISHED',
                'scope': '10x10 synthetic operation tables; no lottery inference'}


def fit_additive_primitive(training: CellDataset) -> FrozenLatentPrimitive:
    """Solve modular graph constraints without ever seeing the holdout labels.

    Each node is A0..A9 or B0..B9, each observed pair is an edge with
    constraint u[a] + v[b] = y mod 10. Within a connected component the
    gauge can be fixed arbitrarily; disconnected graphs are unidentifiable.
    Contradictory cycles prove the additive model wrong on its training data.
    """
    if not isinstance(training, CellDataset):
        raise ValueError('expected CellDataset containing training observations')
    graph: list[list[tuple[int, int]]] = [[] for _ in range(20)]
    for a, b, y in training.rows:
        graph[a].append((10+b, y))
        graph[10+b].append((a, y))
    coords: list[int | None] = [None] * 20
    groups: list[int] = [-1] * 20
    contradictions = 0
    components = 0
    for start in range(20):
        if coords[start] is not None:
            continue
        coords[start] = 0
        groups[start] = components
        q = deque([start])
        while q:
            here = q.popleft()
            for nxt, output in graph[here]:
                # Sum, not difference: the other latent value is y-current.
                value = (output - coords[here]) % 10
                if coords[nxt] is None:
                    coords[nxt] = value
                    groups[nxt] = components
                    q.append(nxt)
                elif coords[nxt] != value:
                    contradictions += 1
        components += 1
    lhs = tuple(int(x) for x in coords[:10])
    rhs = tuple(int(x) for x in coords[10:])
    if contradictions:
        status = 'rejected_inconsistent'
        errors = None
    elif components > 1:
        status = 'unidentifiable'
        errors = None
    else:
        status = 'identified'
        errors = sum((lhs[a]+rhs[b])%10 != y for a, b, y in training.rows)
        if errors:
            raise AssertionError('constraint solver returned an inconsistent identified table')
    return FrozenLatentPrimitive(lhs, rhs, tuple(groups), training.pairs,
                                 training.fingerprint, status, contradictions, errors)


def evaluate_frozen_latent(operator: FrozenLatentPrimitive, holdout: CellDataset) -> dict:
    """Post-fit evaluation; disjoint coordinates required, no refitting."""
    if not isinstance(operator, FrozenLatentPrimitive) or not isinstance(holdout, CellDataset):
        raise ValueError('expected frozen latent primitive and CellDataset')
    if set(operator.source_pairs).intersection(holdout.pairs):
        raise ValueError('training and holdout overlap')
    if operator.status != 'identified':
        raise ValueError('latent primitive not identified; no held-out predictions')
    predicted = [operator.predict(a, b) for a, b, _ in holdout.rows]
    if any(p is None for p in predicted):
        raise AssertionError('identified primitive unexpectedly abstained')
    errors = sum(p != row[2] for p, row in zip(predicted, holdout.rows))
    return {'operator_id': operator.identity, 'data_sha256': holdout.fingerprint,
            'errors': int(errors), 'count': len(holdout.rows), 'accuracy': 1-errors/len(holdout.rows),
            'coverage': 1.0, 'overlapping_pairs': 0, 'refitted': False,
            'production_enabled': False, 'predictive_advantage': 'NOT_ESTABLISHED'}
