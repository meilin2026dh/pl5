"""V3.7.10: contradiction-guided, bounded generation of compositional digits.

Human-specified safe DSL, with compositions generated programmatically. This
algorithm is a *research-only* synthesizer, NOT a new mathematical axiom and
NOT evidence of lottery predictability. Fitting never accesses held-out labels.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import numpy as np

from .structure_search_v372 import CellDataset
from .latent_primitives_v377 import fit_additive_primitive
from .adaptive_primitives_v379 import FrozenAdaptivePrimitive, fit_adaptive_primitive


UNARIES = ('id', 'square', 'cube', 'inc', 'twice_inc', 'parity', 'bucket3', 'dist4')
BINARIES = ('mul', 'absdiff', 'min', 'max', 'xor', 'gcd')
DOMAIN = tuple((a,b) for a in range(10) for b in range(10))


def _hash(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                             allow_nan=False).encode()).hexdigest()


def _unary(kind: str, x: np.ndarray) -> np.ndarray:
    if kind == 'id': return x
    if kind == 'square': return x*x
    if kind == 'cube': return x*x*x
    if kind == 'inc': return x+1
    if kind == 'twice_inc': return 2*x+1
    if kind == 'parity': return x%2
    if kind == 'bucket3': return x//3
    if kind == 'dist4': return np.abs(x-4)
    raise ValueError('invalid unary transformation')


def _binary(kind: str, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    if kind == 'mul': return x*y
    if kind == 'absdiff': return np.abs(x-y)
    if kind == 'min': return np.minimum(x,y)
    if kind == 'max': return np.maximum(x,y)
    if kind == 'xor': return np.bitwise_xor(x,y)
    if kind == 'gcd': return np.gcd(x,y)
    raise ValueError('invalid binary transformation')


def _feature(spec: tuple[str,str,str]) -> np.ndarray:
    ua, op, ub = spec
    a,b=np.indices((10,10),dtype=np.int64)
    return np.asarray(_binary(op,_unary(ua,a),_unary(ub,b)) % 10,dtype=np.int64)


@dataclass(frozen=True)
class GeneratorConfig:
    max_features: int = 400
    max_fits: int = 256

    def __post_init__(self):
        if type(self.max_features) is not int or not 1 <= self.max_features <= 2048:
            raise ValueError('max_features must be an integer in 1..2048')
        if type(self.max_fits) is not int or not 1 <= self.max_fits <= 1024:
            raise ValueError('max_fits must be an integer in 1..1024')


@dataclass(frozen=True)
class FrozenGeneratedPrimitive:
    status: str
    family: str
    spec: tuple[str,str,str] | None
    coefficient: int | None
    u: tuple[int,...]
    v: tuple[int,...]
    prior: FrozenAdaptivePrimitive | None
    source_pairs: tuple[tuple[int,int],...]
    source_sha256: str
    witness_rectangles: int
    proposals: int
    distinct_features: int
    candidate_models: int
    reason: str

    @property
    def identity(self):
        return _hash(('pl5-v3710-generated-1', self.status, self.family, self.spec,
                      self.coefficient, self.u, self.v,
                      self.prior.identity if self.prior is not None else None,
                      self.source_sha256))

    def predict(self, a: int, b: int) -> int | None:
        if type(a) is not int or type(b) is not int or not 0 <= a <= 9 or not 0 <= b <= 9:
            raise ValueError('digit inputs must be integers 0..9')
        if self.status != 'identified': return None
        if self.family == 'legacy_v379':
            return self.prior.predict(a,b)
        if self.family == 'generated_interaction':
            return (self.u[a]+self.v[b]+self.coefficient*int(_feature(self.spec)[a,b]))%10
        raise AssertionError('invalid identified model family')

    def to_dict(self):
        return {
            'schema':'pl5-v3710-generated-1', 'operator_id':self.identity,
            'status':self.status, 'family':self.family,
            'spec':self.spec, 'coefficient':self.coefficient,
            'unary_a':self.u, 'unary_b':self.v,
            'legacy_operator_id':self.prior.identity if self.prior is not None else None,
            'source_pairs':self.source_pairs, 'source_sha256':self.source_sha256,
            'witness_rectangles':self.witness_rectangles,
            'proposals':self.proposals, 'distinct_features':self.distinct_features,
            'candidate_models':self.candidate_models, 'reason':self.reason,
            'generation_source':'train_only_contradiction_witnesses',
            'novel_relative_to_v379': self.status=='identified' and self.family=='generated_interaction',
            'production_enabled':False, 'predictive_advantage':'NOT_ESTABLISHED',
            'limitations':'bounded human-designed compositional DSL; no real lottery claim'
        }


def _rectangles(training: CellDataset):
    observations={(a,b):y for a,b,y in training.rows}
    rectangles=[]
    for a0 in range(9):
        for a1 in range(a0+1,10):
            for b0 in range(9):
                for b1 in range(b0+1,10):
                    if all((a,b) in observations for a,b in ((a0,b0),(a1,b1),(a0,b1),(a1,b0))):
                        y=(observations[a0,b0]+observations[a1,b1] -
                           observations[a0,b1]-observations[a1,b0])%10
                        rectangles.append((a0,a1,b0,b1,y))
    return tuple(rectangles)


def _all_specs():
    return tuple((ua,op,ub) for op in BINARIES for ua in UNARIES for ub in UNARIES)


def fit_counterexample_primitive(training: CellDataset,
                                 config: GeneratorConfig=GeneratorConfig()) -> FrozenGeneratedPrimitive:
    if not isinstance(training,CellDataset) or not isinstance(config,GeneratorConfig):
        raise ValueError('expected CellDataset and GeneratorConfig')
    pairs=training.pairs
    fp=training.fingerprint
    rects=_rectangles(training)
    violations=sum(row[4]!=0 for row in rects)

    def result(status, reason, *, family='none', spec=None, coefficient=None, u=(), v=(),
               prior=None, proposals=0, distinct=0, matches=0):
        return FrozenGeneratedPrimitive(status,family,spec,coefficient,u,v,prior,pairs,
                                        fp,violations,proposals,distinct,matches,reason)

    # First falsify the previous model family before allocating discovery budget.
    prior=fit_adaptive_primitive(training)
    if prior.status=='identified':
        return result('identified','existing V3.7.9 grammar already explains training',
                      family='legacy_v379',prior=prior)
    if not rects or not violations:
        return result('unidentifiable','insufficient additive contradiction witnesses')

    specs=_all_specs()
    proposals=0
    distinct=0
    seen_features=set()
    matches=[]
    unresolved=False
    exhausted=False
    for index,spec in enumerate(specs):
        if index >= config.max_features:
            exhausted=True
            break
        raw=_feature(spec)
        signature=raw.tobytes()
        if signature in seen_features: continue
        seen_features.add(signature)
        distinct+=1
        phi=np.array([(raw[a0,b0]+raw[a1,b1]-raw[a0,b1]-raw[a1,b0])%10
                      for a0,a1,b0,b1,_ in rects],dtype=np.int64)
        target=np.array([y for *_,y in rects],dtype=np.int64)
        for k in range(1,10):
            proposals+=1
            if np.any((k*phi-target)%10):
                continue
            if len(matches)>=config.max_fits:
                exhausted=True
                break
            adjusted=CellDataset(tuple((a,b,(y-k*int(raw[a,b]))%10)
                                       for a,b,y in training.rows))
            latent=fit_additive_primitive(adjusted)
            if latent.status=='identified':
                completion=tuple((latent.u[a]+latent.v[b]+k*int(raw[a,b]))%10
                                 for a,b in DOMAIN)
                matches.append((spec,k,latent.u,latent.v,completion))
            elif latent.status=='unidentifiable':
                unresolved=True
        if exhausted: break

    if exhausted:
        return result('budget_exhausted','bounded search did not cover full candidate language',
                      proposals=proposals,distinct=distinct,matches=len(matches))
    if unresolved:
        return result('unidentifiable','some compatible completions cannot be identified',
                      proposals=proposals,distinct=distinct,matches=len(matches))
    if not matches:
        return result('rejected_inconsistent','no generated composition explains all training witnesses',
                      proposals=proposals,distinct=distinct)
    full_tables={row[4] for row in matches}
    if len(full_tables)!=1:
        return result('unidentifiable','training-consistent compositions disagree outside training',
                      proposals=proposals,distinct=distinct,matches=len(matches))
    spec,k,u,v,_=matches[0]
    return result('identified','all train-consistent generated compositions agree on full 10x10 domain',
                  family='generated_interaction',spec=spec,coefficient=k,u=u,v=v,
                  proposals=proposals,distinct=distinct,matches=len(matches))


def evaluate_generated(frozen: FrozenGeneratedPrimitive, held: CellDataset) -> dict:
    if not isinstance(frozen,FrozenGeneratedPrimitive) or not isinstance(held,CellDataset):
        raise ValueError('expected frozen generator model and held-out CellDataset')
    if set(frozen.source_pairs).intersection(held.pairs):
        raise ValueError('train/holdout overlap')
    if frozen.status!='identified':
        raise ValueError('cannot evaluate abstaining model')
    errors=sum(frozen.predict(a,b)!=y for a,b,y in held.rows)
    return {'operator_id':frozen.identity,'holdout_sha256':held.fingerprint,
            'count':len(held.rows),'errors':errors,'accuracy':1-errors/len(held.rows),
            'refitted':False,'production_enabled':False,
            'predictive_advantage':'NOT_ESTABLISHED'}
