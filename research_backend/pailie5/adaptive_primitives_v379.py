"""V3.7.9: train-only finite grammar search for interactions and split boundaries.

Only proposes members of an explicitly bounded grammar. It does NOT invent
unrestricted mathematics, learn from held-out targets, or authorize betting.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json

from .structure_search_v372 import CellDataset
from .latent_primitives_v377 import fit_additive_primitive
from .coupled_primitives_v378 import _solve_prime


def _hash(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _basis(name: str, a: int, b: int) -> int:
    if name == 'a*b': return a*b
    if name == 'a²*b': return a*a*b
    if name == 'a*b²': return a*b*b
    if name == 'a²*b²': return a*a*b*b
    if name == 'parity(a)*b': return (a%2)*b
    if name == 'bucket(a)*b': return (a//3)*b
    if name == 'a³*b': return a*a*a*b
    if name == 'a*b³': return a*b*b*b
    raise ValueError('unknown interaction basis')


BASIS = ('a*b', 'a²*b', 'a*b²', 'a²*b²', 'parity(a)*b',
         'bucket(a)*b', 'a³*b', 'a*b³')
PREDICATES = tuple([('a<b', 0)] +
                   [('sum<', k) for k in range(5, 15)] +
                   [('difference<', k) for k in range(-3, 4)])


def _pred(kind: str, threshold: int, a: int, b: int) -> bool:
    if kind == 'a<b': return a < b
    if kind == 'sum<': return a+b < threshold
    if kind == 'difference<': return a-b < threshold
    raise ValueError('unknown boundary')


def _piece_features(kind: str, threshold: int, a: int, b: int) -> tuple[int, ...]:
    return (a,b,0,0,0) if _pred(kind,threshold,a,b) else (0,0,a*b,a,1)


def _solve_piecewise(rows: tuple[tuple[int,int,int], ...], predicate: tuple[str,int]):
    kind, threshold = predicate
    inputs = [(_piece_features(kind,threshold,a,b),y) for a,b,y in rows]
    r2, u2 = _solve_prime(inputs, 2, variables=5)
    r5, u5 = _solve_prime(inputs, 5, variables=5)
    if r2 is None or r5 is None: return 'inconsistent', ()
    if not (u2 and u5): return 'unidentifiable', ()
    params = tuple((5*x+6*y)%10 for x,y in zip(r2,r5))
    if not all(sum(p*f for p,f in zip(params,features))%10==v for features,v in inputs):
        raise AssertionError('modular CRT solver inconsistent')
    return 'identified', params


@dataclass(frozen=True)
class FrozenAdaptivePrimitive:
    family: str
    descriptor: str
    parameters: tuple[int, ...]
    status: str
    source_pairs: tuple[tuple[int,int], ...]
    source_data_sha256: str
    alternative_models: int
    reason: str

    @property
    def identity(self):
        return _hash(('pl5-v379-adaptive-1', self.family, self.descriptor,
                      self.parameters, self.source_data_sha256))

    def predict(self, a: int, b: int) -> int | None:
        if type(a) is not int or type(b) is not int or a not in range(10) or b not in range(10):
            raise ValueError('inputs must be digits 0..9')
        if self.status != 'identified': return None
        if self.family == 'interaction_basis':
            return (self.parameters[a]+self.parameters[10+b] +
                    self.parameters[20]*_basis(self.descriptor,a,b))%10
        if self.family == 'dynamic_piecewise':
            kind, threshold = self.descriptor.split(':',1)
            return sum(x*y for x,y in zip(self.parameters,
                       _piece_features(kind,int(threshold),a,b)))%10
        raise ValueError('unknown family')

    def to_dict(self):
        return {'schema':'pl5-v379-adaptive-1', 'operator_id':self.identity,
                'family':self.family,'descriptor':self.descriptor,'parameters':self.parameters,
                'status':self.status,'reason':self.reason,
                'source_pairs':self.source_pairs,'source_data_sha256':self.source_data_sha256,
                'alternative_models':self.alternative_models,
                'production_enabled':False,'predictive_advantage':'NOT_ESTABLISHED',
                'provenance':'training-only finite candidate grammar'}


def fit_adaptive_primitive(training: CellDataset) -> FrozenAdaptivePrimitive:
    """Enumerate grammar with training data only and refuse inconsistent extensions.

    Selection sees NO holdout observations. If train-consistent candidate
    classes imply different values anywhere on the 10x10 grid, abstain.
    """
    if not isinstance(training,CellDataset): raise ValueError('expected CellDataset')
    found: list[tuple[str,str,tuple[int,...]]] = []
    unresolved = False
    for basis in BASIS:
        for k in range(10):
            adjusted = CellDataset(tuple((a,b,(y-k*_basis(basis,a,b))%10)
                                         for a,b,y in training.rows))
            fit = fit_additive_primitive(adjusted)
            if fit.status == 'identified':
                found.append(('interaction_basis',basis,fit.u+fit.v+(k,)))
            elif fit.status == 'unidentifiable':
                unresolved = True
    for kind,thresh in PREDICATES:
        status,params = _solve_piecewise(training.rows,(kind,thresh))
        if status == 'identified': found.append(('dynamic_piecewise',f'{kind}:{thresh}',params))
        elif status == 'unidentifiable': unresolved=True
    if not found:
        status = 'unidentifiable' if unresolved else 'rejected_inconsistent'
        return FrozenAdaptivePrimitive('none','',(),status,training.pairs,training.fingerprint,
                                       0,'no unique supported candidate')
    if unresolved:
        return FrozenAdaptivePrimitive('none','',(),'unidentifiable',training.pairs,training.fingerprint,
                                       len(found),'some candidate classes have unresolved completions')
    signatures = set()
    for family,descriptor,params in found:
        model = FrozenAdaptivePrimitive(family,descriptor,params,'identified',training.pairs,
                                        training.fingerprint,len(found),'candidate')
        signatures.add(tuple(model.predict(a,b) for a in range(10) for b in range(10)))
        if len(signatures)>1:
            return FrozenAdaptivePrimitive('none','',(),'unidentifiable',training.pairs,
                                           training.fingerprint,len(found),
                                           'training-consistent alternatives disagree outside observed cells')
    family,descriptor,params = found[0]
    return FrozenAdaptivePrimitive(family,descriptor,params,'identified',training.pairs,
                                   training.fingerprint,len(found),'all identified candidates agree on full domain')


def evaluate_adaptive(frozen: FrozenAdaptivePrimitive, held: CellDataset) -> dict:
    if not isinstance(frozen,FrozenAdaptivePrimitive) or not isinstance(held,CellDataset):
        raise ValueError('expected frozen operator and CellDataset')
    if set(frozen.source_pairs).intersection(held.pairs):
        raise ValueError('train/holdout overlap')
    if frozen.status!='identified': raise ValueError('cannot evaluate unidentified model')
    errors = sum(frozen.predict(a,b)!=v for a,b,v in held.rows)
    return {'operator_id':frozen.identity, 'held_sha256':held.fingerprint,
            'count':len(held.rows),'errors':errors,'accuracy':1-errors/len(held.rows),
            'refitted':False,'production_enabled':False,'predictive_advantage':'NOT_ESTABLISHED'}
