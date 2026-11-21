"""V3.7.24 research-only: bounded syntax expansion with blind-held-out scoring.

Single-feature polynomial baseline versus counterexample-triggered *two-feature
composition*. Both evaluate exactly MAX_EVALS pre-specified candidate programs.
The available primitives are developer-defined; no novel mathematical laws are claimed.
"""
from __future__ import annotations

import hashlib
import itertools
import time
from pathlib import Path

import numpy as np

from .language_evolution_v3722 import _features, _read_checked, _sha, _signed, _write_new, _coordinate_overlap
from .structure_search_v372 import CellDataset

VERSION = 'pl5-v3724-compositional-grammar-1'
FEATURES = ('a', 'b', 'product_mod10', 'xor_mod10', 'gcd',
            'absdiff_mod10', 'min', 'max', 'sum_mod10', 'difference_mod10')
COMBINERS = ('add', 'sub', 'mul', 'xor')
MAX_EVALS = 2200
DOMAIN = 100
EVIDENCE_GRADE = 'INTERNAL_DEVELOPER_SYNTHETIC_NOT_EXTERNAL_BLIND'


def _base_tables() -> dict[str, np.ndarray]:
    raw = _features()
    return {k: np.asarray(raw[k], dtype=np.int64) % 10 for k in FEATURES}


def _all_cells(dataset: CellDataset) -> tuple[np.ndarray, np.ndarray]:
    index = np.asarray([10*a+b for a,b,_ in dataset.rows], dtype=np.int64)
    value = np.asarray([y for _,_,y in dataset.rows], dtype=np.int64)
    return index,value


def _compose(x: np.ndarray, y: np.ndarray, op: str) -> np.ndarray:
    if op == 'add': return (x+y)%10
    if op == 'sub': return (x-y)%10
    if op == 'mul': return (x*y)%10
    if op == 'xor': return np.bitwise_xor(x,y)%10
    raise ValueError('unsupported composition')


def _proposals(arm: str):
    """Generate a fixed, reproducible 2200-candidate budget without using labels."""
    bases = _base_tables()
    if arm in ('baseline', 'expanded'):
        # Both arms receive IDENTICAL first-stage 400 affine candidates.
        for feature in FEATURES:
            x=bases[feature]
            for scale in (1,3,7,9):
                for shift in range(10):
                    yield {'grammar':'unary_affine','feature':feature,'scale':scale,'shift':shift}, \
                          (scale*x+shift).reshape(-1)%10
    if arm == 'baseline':
        # Spend the same remaining 1800 evaluations on *unary* polynomial grammar.
        for c2,c1,c0 in itertools.product(range(1,10),range(10),range(10)):
            for feature in FEATURES:
                x=bases[feature]
                yield {'grammar':'unary_poly2','feature':feature,'coefficients':[c0,c1,c2]}, \
                      (c0+c1*x+c2*x*x).reshape(-1)%10
    elif arm == 'expanded':
        # Exactly 45 unordered pairs * 4 combiners * 10 shifts = 1800.
        for left,right in itertools.combinations(FEATURES,2):
            for op in COMBINERS:
                composed=_compose(bases[left],bases[right],op)
                for shift in range(10):
                    yield {'grammar':'binary_composition','left':left,'right':right,
                           'operation':op,'shift':shift}, (composed+shift).reshape(-1)%10
    else:
        raise ValueError('unsupported arm')


def _table(spec:dict) -> np.ndarray:
    if not isinstance(spec, dict): raise ValueError('not a program')
    bases=_base_tables()
    kind=spec.get('grammar')
    if kind=='unary_poly2':
        if set(spec)!={'grammar','feature','coefficients'}: raise ValueError('program fields')
        x=bases[spec['feature']]
        p=spec['coefficients']
        if not isinstance(p,list) or len(p)!=3 or any(type(z) is not int or not 0<=z<10 for z in p):
            raise ValueError('invalid coefficients')
        return (p[0]+p[1]*x+p[2]*x*x).reshape(-1)%10
    if kind=='unary_affine':
        if set(spec)!={'grammar','feature','scale','shift'}:raise ValueError('program fields')
        x=bases[spec['feature']]
        scale,shift=spec['scale'],spec['shift']
        if type(scale) is not int or scale not in (1,3,7,9) or type(shift) is not int or not 0<=shift<10:
            raise ValueError('invalid affine')
        return (scale*x+shift).reshape(-1)%10
    if kind=='binary_composition':
        if set(spec)!={'grammar','left','right','operation','shift'}:raise ValueError('program fields')
        left,right,op,shift=spec['left'],spec['right'],spec['operation'],spec['shift']
        if left not in FEATURES or right not in FEATURES or FEATURES.index(left)>=FEATURES.index(right):
            raise ValueError('invalid source feature pair')
        if op not in COMBINERS or type(shift) is not int or not 0<=shift<10:raise ValueError('invalid operator')
        return (_compose(bases[left],bases[right],op)+shift).reshape(-1)%10
    raise ValueError('unregistered operator')


def commit_holdout(holdout: CellDataset, nonce: str) -> str:
    if not isinstance(holdout,CellDataset) or not isinstance(nonce,str) or len(nonce)<16:
        raise ValueError('holdout and secret nonce required')
    return hashlib.sha256((VERSION+'|'+nonce+'|'+holdout.fingerprint).encode()).hexdigest()


def fit(training: CellDataset, study_dir: str|Path, *, arm: str,
        holdout_digest: str|None=None, protocol_sha256: str|None=None) -> dict:
    if not isinstance(training,CellDataset):raise ValueError('training dataset required')
    if arm not in ('baseline','expanded'):raise ValueError('unknown arm')
    if holdout_digest is not None and (len(holdout_digest)!=64 or any(c not in '0123456789abcdef' for c in holdout_digest)):
        raise ValueError('invalid holdout hash')
    if protocol_sha256 is not None and (len(protocol_sha256)!=64 or any(c not in '0123456789abcdef' for c in protocol_sha256)):
        raise ValueError('invalid protocol hash')
    coords, labels = _all_cells(training)
    winners={}
    best=101
    best_firststage=101
    count=0
    triggered=False
    t0=time.perf_counter_ns()
    for spec,table in itertools.islice(_proposals(arm),MAX_EVALS):
        err=int(np.count_nonzero(table[coords]!=labels))
        best=min(best,err)
        count+=1
        if arm=='expanded' and count==400:
            best_firststage=best
            triggered=best>0
        if err==0:
            digest=hashlib.sha256(table.astype('uint8').tobytes()).hexdigest()
            winners.setdefault(digest,spec)
    elapsed=time.perf_counter_ns()-t0
    if count!=MAX_EVALS:raise RuntimeError('research candidate budget not fully charged')
    rec=_signed({'schema':VERSION+':fit','arm':arm,'training_sha256':training.fingerprint,
       'train_pairs':[list(p) for p in training.pairs], 'candidate_budget':MAX_EVALS,
       'candidate_evaluations':count,'wall_ns_fit':elapsed,'best_training_errors':best,
       'base_stage_errors':best_firststage if arm=='expanded' else None,
       'grammar_expansion_triggered':triggered,
       'exact_fit_programs':[{'spec':s,'table_sha256':h} for h,s in winners.items()],
       'holdout_commitment':holdout_digest,'protocol_sha256':protocol_sha256,
       'training_only':True,'external_blind':False,'evidence_grade':EVIDENCE_GRADE})
    _write_new(Path(study_dir)/'fit.json',rec)
    return rec


def freeze(study_dir: str|Path, validation: CellDataset) -> dict:
    if not isinstance(validation,CellDataset):raise ValueError('validation required')
    root=Path(study_dir)
    fitted=_read_checked(root/'fit.json',VERSION+':fit')
    if _coordinate_overlap(fitted['train_pairs'],[list(p) for p in validation.pairs]):
        raise ValueError('training/validation overlap')
    coords,labels=_all_cells(validation)
    survivors=[]
    for cand in fitted['exact_fit_programs']:
        table=_table(cand['spec'])
        if hashlib.sha256(table.astype('uint8').tobytes()).hexdigest()!=cand['table_sha256']:
            raise ValueError('candidate modified')
        if np.array_equal(table[coords],labels):survivors.append(cand)
    status='FROZEN' if len(survivors)==1 else 'ABSTAIN'
    record=_signed({'schema':VERSION+':freeze','fit_sha256':_sha(fitted),
       'validation_sha256':validation.fingerprint,
       'validation_pairs':[list(p) for p in validation.pairs],
       'status':status,'selected':survivors[0] if status=='FROZEN' else None,
       'distinct_survivors':len(survivors),
       'reason':None if status=='FROZEN' else ('none' if not survivors else 'ambiguous'),
       'test_labels_seen':False})
    _write_new(root/'freeze.json',record)
    return record


def evaluate(study_dir: str|Path, holdout: CellDataset, *, nonce: str|None=None) -> dict:
    if not isinstance(holdout,CellDataset):raise ValueError('holdout required')
    root=Path(study_dir)
    fitted=_read_checked(root/'fit.json',VERSION+':fit')
    frozen=_read_checked(root/'freeze.json',VERSION+':freeze')
    if frozen['fit_sha256']!=_sha(fitted):raise ValueError('broken fit/freeze provenance')
    if _coordinate_overlap(fitted['train_pairs'],frozen['validation_pairs'],[list(p) for p in holdout.pairs]):
        raise ValueError('heldout overlap')
    if fitted['holdout_commitment'] is not None:
        if nonce is None or commit_holdout(holdout,nonce)!=fitted['holdout_commitment']:
            raise ValueError('holdout commitment mismatch or no nonce')
    if frozen['status']=='FROZEN':
        candidate=frozen['selected']
        table=_table(candidate['spec'])
        if hashlib.sha256(table.astype('uint8').tobytes()).hexdigest()!=candidate['table_sha256']:
            raise ValueError('frozen table altered')
        coords,labels=_all_cells(holdout)
        errors=int(np.count_nonzero(table[coords]!=labels))
    else:errors=None
    out=_signed({'schema':VERSION+':evaluation','freeze_sha256':_sha(frozen),
       'holdout_sha256':holdout.fingerprint,'status':'EVALUATED' if errors is not None else 'ABSTAIN',
       'test_errors':errors,'test_count':len(holdout.rows),
       'commitment_verified':fitted['holdout_commitment'] is not None,
       'evidence_grade':EVIDENCE_GRADE,'lottery_predictive_advantage':'NOT_ESTABLISHED'})
    _write_new(root/'evaluation.json',out)
    return out
