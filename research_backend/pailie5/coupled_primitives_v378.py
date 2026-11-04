"""V3.7.8 bounded, training-only discovery of two structured digit couplings.

This module discovers representations *within explicitly specified model classes*.
It does not invent universal mathematics and is not connected to lottery selection.
Only training observations are ever supplied to fit_coupled_primitive.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json

from .structure_search_v372 import CellDataset
from .latent_primitives_v377 import fit_additive_primitive


def _sha(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _solve_prime(rows: list[tuple[tuple[int, ...], int]], prime: int, variables: int = 5):
    """Return (solution, unique) in GF(prime), or (None, False) if inconsistent."""
    matrix = [[x % prime for x in features] + [target % prime] for features, target in rows]
    rank = 0
    pivot_cols = []
    for col in range(variables):
        pivot = next((i for i in range(rank, len(matrix)) if matrix[i][col] != 0), None)
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        inv = pow(matrix[rank][col], -1, prime)
        matrix[rank] = [(x * inv) % prime for x in matrix[rank]]
        for i in range(len(matrix)):
            if i == rank:
                continue
            ratio = matrix[i][col]
            if ratio:
                matrix[i] = [(a - ratio * b) % prime for a, b in zip(matrix[i], matrix[rank])]
        pivot_cols.append(col)
        rank += 1
        if rank == len(matrix):
            break
    if any(all(x == 0 for x in row[:variables]) and row[variables] for row in matrix):
        return None, False
    if rank < variables:
        return tuple([0] * variables), False
    answer = [0] * variables
    for i, col in enumerate(pivot_cols):
        answer[col] = matrix[i][variables]
    return tuple(answer), True


def _piecewise_features(a: int, b: int) -> tuple[int, ...]:
    return (a, b, 0, 0, 0) if a < b else (0, 0, a*b, a, 1)


def _solve_piecewise(training: CellDataset):
    data = [(_piecewise_features(a,b),y) for a,b,y in training.rows]
    p2, u2 = _solve_prime(data, 2)
    p5, u5 = _solve_prime(data, 5)
    if p2 is None or p5 is None:
        return 'rejected_inconsistent', ()
    if not (u2 and u5):
        return 'unidentifiable', ()
    params = tuple((5*a+6*b)%10 for a,b in zip(p2,p5))
    assert all(sum(w*f for w,f in zip(params, feat))%10 == y for feat,y in data)
    return 'identified', params


@dataclass(frozen=True)
class FrozenCoupledPrimitive:
    family: str
    parameters: tuple[int, ...]
    status: str
    source_pairs: tuple[tuple[int,int], ...]
    source_data_sha256: str
    alternatives: int
    reason: str

    @property
    def identity(self) -> str:
        return _sha(['pl5-v378-coupled-1', self.family, self.parameters,
                     self.status, self.source_data_sha256])

    def predict(self, a: int, b: int) -> int | None:
        if type(a) is not int or type(b) is not int or not 0 <= a <= 9 or not 0 <= b <= 9:
            raise ValueError('input digits must be ASCII-compatible integers in 0..9')
        if self.status != 'identified':
            return None
        if self.family == 'additive_mod10':
            return (self.parameters[a] + self.parameters[10+b]) % 10
        if self.family == 'bilinear_mod10':
            return (self.parameters[a] + self.parameters[10+b] + self.parameters[20]*a*b) % 10
        if self.family == 'piecewise_linear_mod10':
            return sum(w*f for w,f in zip(self.parameters, _piecewise_features(a,b))) % 10
        raise ValueError('unsupported frozen family')

    def to_dict(self) -> dict:
        return {'schema': 'pl5-v378-coupled-1', 'operator_id': self.identity,
                'family': self.family, 'parameters': self.parameters, 'status': self.status,
                'source_pairs': self.source_pairs, 'source_data_sha256': self.source_data_sha256,
                'alternative_models_consistent': self.alternatives, 'reason': self.reason,
                'production_enabled': False, 'predictive_advantage': 'NOT_ESTABLISHED',
                'provenance': 'training-only bounded synthetic digit model'}


def fit_coupled_primitive(training: CellDataset) -> FrozenCoupledPrimitive:
    """Select a model only from training cells, abstain on inconsistent or ambiguous fits.

    Priority is V3.7.7 additive maps, then a rank-one digit interaction
    k*a*b over Z10, then a five-parameter a<b piecewise algebraic model.
    Multiple distinct full-table solutions are considered unidentifiable.
    """
    if not isinstance(training, CellDataset):
        raise ValueError('expected training CellDataset')
    candidates: list[tuple[str, tuple[int,...]]] = []
    unresolved = False
    # Finite, preregistered interaction library, without access to withheld labels.
    for k in range(10):
        adjusted = CellDataset(tuple((a,b,(y-k*a*b)%10) for a,b,y in training.rows))
        fitted = fit_additive_primitive(adjusted)
        if fitted.status == 'identified':
            params = fitted.u + fitted.v + ((k,) if k else ())
            candidates.append(('additive_mod10' if k == 0 else 'bilinear_mod10',params))
        elif fitted.status == 'unidentifiable':
            unresolved = True
    piece_status, piece_params = _solve_piecewise(training)
    if piece_status == 'identified':
        candidates.append(('piecewise_linear_mod10', piece_params))
    elif piece_status == 'unidentifiable':
        unresolved = True
    if not candidates:
        status = 'unidentifiable' if unresolved else 'rejected_inconsistent'
        return FrozenCoupledPrimitive('none', (), status, training.pairs,
                                      training.fingerprint, 0,
                                      'insufficient identifying constraints' if unresolved else 'no supported model fits')
    if unresolved:
        return FrozenCoupledPrimitive('none', (), 'unidentifiable', training.pairs,
                                      training.fingerprint, len(candidates),
                                      'some supported model families admit unresolved completions')
    # Different solutions that make identical predictions on the full input grid
    # are equivalent for this fixed 10x10 domain; choose the simpler family.
    canonical = []
    for family, params in candidates:
        trial = FrozenCoupledPrimitive(family,params,'identified',training.pairs,
                                       training.fingerprint,len(candidates),'candidate')
        outputs = tuple(trial.predict(a,b) for a in range(10) for b in range(10))
        canonical.append(outputs)
    if len(set(canonical)) > 1:
        return FrozenCoupledPrimitive('none', (), 'unidentifiable', training.pairs,
                                      training.fingerprint, len(candidates), 'ambiguous training-consistent extensions')
    family, params = candidates[0]
    return FrozenCoupledPrimitive(family, params, 'identified', training.pairs,
                                  training.fingerprint, len(candidates), 'training constraints uniquely determine predictions')


def evaluate_coupled(operator: FrozenCoupledPrimitive, holdout: CellDataset) -> dict:
    if not isinstance(operator, FrozenCoupledPrimitive) or not isinstance(holdout, CellDataset):
        raise ValueError('expected frozen operator and held-out CellDataset')
    if set(operator.source_pairs).intersection(holdout.pairs):
        raise ValueError('training/holdout overlap')
    if operator.status != 'identified':
        raise ValueError('unidentified or rejected operator cannot predict')
    misses = sum(operator.predict(a,b) != y for a,b,y in holdout.rows)
    return {'operator_id':operator.identity, 'holdout_sha256':holdout.fingerprint,
            'count':len(holdout.rows), 'errors':misses,'accuracy':1-misses/len(holdout.rows),
            'refitted':False,'production_enabled':False,'predictive_advantage':'NOT_ESTABLISHED'}
