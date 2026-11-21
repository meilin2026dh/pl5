"""PL5 V3.7.25: bounded, data-driven grammar expansion + blind challenge interfaces.

Research only. No claim to independent external blind validation, general mathematics
invention, or lottery prediction. All algebra takes place in the 10x10 Z/10Z
finite table. Training labels are the ONLY labels available to grammar synthesis;
validation selects frozen candidates and heldout scoring is one-shot.
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path

import numpy as np

from .grammar_discovery_v3724 import _base_tables, _all_cells, _table as old_table
from .language_evolution_v3722 import _read_checked, _sha, _signed, _write_new, _coordinate_overlap
from .structure_search_v372 import CellDataset

VERSION = 'pl5-v3725-ring-grammar-1'
EVIDENCE_GRADE = 'INTERNAL_SYNTHETIC_EXTERNAL_CHALLENGE_INTERFACE_ONLY'
STAGES = ('original_primitives', 'polynomial_degree3', 'piecewise_gate', 'parity_gate')


def _features() -> dict[str, np.ndarray]:
    base = {k: np.asarray(v,dtype=np.int64).reshape(100) for k,v in _base_tables().items()}
    a,b=base['a'],base['b']
    lt = (a<b).astype(np.int64)
    same = ((a%2)==(b%2)).astype(np.int64)
    # Each stage only adds available syntactic operations; no target-family ID.
    more = {
        'constant':np.ones(100,dtype=np.int64),
        'a_squared': a*a,
        'b_squared': b*b,
        'a_cubed':a*a*a,
        'b_cubed':b*b*b,
        'a_squared_b':a*a*b,
        'a_b_squared':a*b*b,
        'gcd_absdiff_product':base['gcd']*base['absdiff_mod10'],
        'xor_absdiff_product':base['xor_mod10']*base['absdiff_mod10'],
        'lt_mask':lt,
        'lt_mask_product':lt*base['product_mod10'],
        'lt_mask_xor':lt*base['xor_mod10'],
        'lt_mask_a':lt*a,
        'lt_mask_b':lt*b,
        'parity_equal_mask':same,
        'parity_mask_product':same*base['product_mod10'],
        'parity_mask_xor':same*base['xor_mod10'],
        'parity_mask_a':same*a,
        'parity_mask_b':same*b,
    }
    return {**{'constant':more['constant']},**base,**{k:v%10 for k,v in more.items() if k!='constant'}}


def _stage_names():
    base = ('constant',)+tuple(_base_tables())
    poly = base + ('a_squared','b_squared','a_cubed','b_cubed','a_squared_b',
                   'a_b_squared','gcd_absdiff_product','xor_absdiff_product')
    piece = poly + ('lt_mask','lt_mask_product','lt_mask_xor','lt_mask_a','lt_mask_b')
    parity = piece + ('parity_equal_mask','parity_mask_product','parity_mask_xor',
                      'parity_mask_a','parity_mask_b')
    return dict(zip(STAGES,(base,poly,piece,parity)))


def _solve_prime(a:np.ndarray,y:np.ndarray,prime:int) -> np.ndarray|None:
    """RREF solution of Ax=y in F_p, with free variables fixed at zero."""
    if prime not in (2,5): raise ValueError('only CRT prime components 2 and 5')
    m,n=a.shape
    aug=np.concatenate((a%prime,y.reshape(-1,1)%prime),axis=1).astype(np.int64)
    row=0; pivots=[]
    for col in range(n):
        k=next((r for r in range(row,m) if aug[r,col]!=0),None)
        if k is None:continue
        if k!=row:aug[[row,k]]=aug[[k,row]]
        aug[row] = (aug[row]*pow(int(aug[row,col]),-1,prime))%prime
        for r in range(m):
            if r!=row and aug[r,col]!=0:
                aug[r]=(aug[r]-int(aug[r,col])*aug[row])%prime
        pivots.append(col)
        row+=1
        if row==m:break
    if np.any((aug[row:, :n]==0).all(axis=1)&(aug[row:, n]!=0)):
        return None
    coefficients=np.zeros(n,dtype=np.int64)
    for r,col in enumerate(pivots):coefficients[col]=aug[r,n]
    if not np.array_equal((a@coefficients)%prime,y%prime):raise RuntimeError('finite field solver bug')
    return coefficients


def _solve_ring(a:np.ndarray,y:np.ndarray) -> np.ndarray|None:
    # Chinese Remainder Theorem: 5*x2+6*x5 is x2 mod 2 and x5 mod 5.
    c2=_solve_prime(a,y,2)
    c5=_solve_prime(a,y,5)
    if c2 is None or c5 is None:return None
    solution=(5*c2+6*c5)%10
    if not np.array_equal((a@solution)%10,y%10):raise RuntimeError('CRT reconstruction bug')
    return solution


def _validate_spec(spec:dict) -> tuple[str,...]:
    if not isinstance(spec,dict) or set(spec)!={'syntax','stage','coefficients','features'}:
        raise ValueError('unregistered program shape')
    if spec['syntax']!='mod10_sparse_basis':raise ValueError('unknown program type')
    stage=spec['stage']
    bank=_stage_names()
    if stage not in bank:raise ValueError('unknown program stage')
    names=spec['features'];coeffs=spec['coefficients']
    if not isinstance(names,list) or not isinstance(coeffs,list) or not names or len(names)!=len(coeffs):
        raise ValueError('invalid coefficients/features')
    if len(names)>len(bank[stage]) or len(set(names))!=len(names):raise ValueError('duplicate program feature')
    if any(not isinstance(k,str) or k not in bank[stage] for k in names):raise ValueError('unregistered feature')
    if any(type(k) is not int or not 0<=k<=9 for k in coeffs):raise ValueError('bad coefficient')
    return tuple(names)


def program_table(spec:dict) -> np.ndarray:
    names=_validate_spec(spec)
    f=_features()
    coefficients=np.array(spec['coefficients'],dtype=np.int64)
    table=np.column_stack([f[k] for k in names])@coefficients%10
    return table.reshape(100)


def fit(training:CellDataset, study_dir:str|Path, *, holdout_digest:str|None=None,
        protocol_sha256:str|None=None) -> dict:
    if not isinstance(training,CellDataset):raise ValueError('must supply typed training set')
    for fingerprint in (holdout_digest,protocol_sha256):
        if fingerprint is not None and (not isinstance(fingerprint,str) or len(fingerprint)!=64 or
                                        any(c not in '0123456789abcdef' for c in fingerprint)):
            raise ValueError('bad commitment')
    idx,labels=_all_cells(training)
    f=_features(); stages=_stage_names()
    trace=[]; candidates={}
    t0=time.perf_counter_ns()
    for stage,names in stages.items():
        matrix=np.column_stack([f[k][idx] for k in names])
        coeffs=_solve_ring(matrix,labels)
        stage_result={'stage':stage,'basis_columns':len(names),'attempted':True,'exact_train_fit':coeffs is not None}
        if coeffs is not None:
            # Sparse serialized representation; length bounded by fixed whitelisted bank.
            terms=[(k,int(c)) for k,c in zip(names,coeffs) if c]
            if not terms:terms=[('constant',0)]
            spec={'syntax':'mod10_sparse_basis','stage':stage,
                  'features':[k for k,_ in terms],'coefficients':[c for _,c in terms]}
            table=program_table(spec)
            if not np.array_equal(table[idx],labels):raise RuntimeError('trained candidate mismatch')
            digest=hashlib.sha256(table.astype('uint8').tobytes()).hexdigest()
            candidates.setdefault(digest,{'spec':spec,'table_sha256':digest})
            stage_result['terms']=len(terms)
        trace.append(stage_result)
    duration=time.perf_counter_ns()-t0
    output=_signed({'schema':VERSION+':fit','training_sha256':training.fingerprint,
        'train_pairs':[list(p) for p in training.pairs],
        'stage_trace':trace,'candidate_evaluations':len(STAGES),
        'exact_fit_tables':list(candidates.values()),'fit_wall_ns':duration,
        'holdout_commitment':holdout_digest,'protocol_sha256':protocol_sha256,
        'evidence_grade':EVIDENCE_GRADE,'training_only':True,'lottery_predictive_advantage':'NOT_ESTABLISHED'})
    _write_new(Path(study_dir)/'fit.json',output)
    return output


def freeze(study_dir:str|Path,validation:CellDataset)->dict:
    if not isinstance(validation,CellDataset):raise ValueError('typed validation required')
    root=Path(study_dir)
    record=_read_checked(root/'fit.json',VERSION+':fit')
    if _coordinate_overlap(record['train_pairs'],[list(p) for p in validation.pairs]):
        raise ValueError('training/validation overlap')
    idx,labels=_all_cells(validation)
    passing=[]
    for candidate in record['exact_fit_tables']:
        table=program_table(candidate['spec'])
        if hashlib.sha256(table.astype('uint8').tobytes()).hexdigest()!=candidate['table_sha256']:
            raise ValueError('changed training program')
        if np.array_equal(table[idx],labels):passing.append(candidate)
    result=_signed({'schema':VERSION+':freeze','fit_sha256':_sha(record),
      'validation_sha256':validation.fingerprint,
      'validation_pairs':[list(p) for p in validation.pairs],
      'status':'FROZEN' if len(passing)==1 else 'ABSTAIN',
      'selected':passing[0] if len(passing)==1 else None,
      'distinct_survivors':len(passing),'reason':('no_candidate' if not passing else
          'ambiguous' if len(passing)>1 else None),'test_labels_seen':False})
    _write_new(root/'freeze.json',result)
    return result


def commit_holdout(holdout:CellDataset,nonce:str)->str:
    if not isinstance(holdout,CellDataset) or not isinstance(nonce,str) or len(nonce)<16:
        raise ValueError('holdout and nonce with 16+ chars required')
    return hashlib.sha256((VERSION+'|'+nonce+'|'+holdout.fingerprint).encode()).hexdigest()


def evaluate(study_dir:str|Path,holdout:CellDataset,*,nonce:str|None=None)->dict:
    if not isinstance(holdout,CellDataset):raise ValueError('typed holdout required')
    root=Path(study_dir)
    record=_read_checked(root/'fit.json',VERSION+':fit')
    frozen=_read_checked(root/'freeze.json',VERSION+':freeze')
    if frozen['fit_sha256']!=_sha(record):raise ValueError('fit lineage mismatch')
    if _coordinate_overlap(record['train_pairs'],frozen['validation_pairs'],[list(p) for p in holdout.pairs]):
        raise ValueError('training/validation/holdout overlap')
    if record['holdout_commitment'] is not None:
        if nonce is None or commit_holdout(holdout,nonce)!=record['holdout_commitment']:
            raise ValueError('holdout commitment mismatch')
    errors=None
    if frozen['status']=='FROZEN':
        candidate=frozen['selected'];table=program_table(candidate['spec'])
        if hashlib.sha256(table.astype('uint8').tobytes()).hexdigest()!=candidate['table_sha256']:
            raise ValueError('changed frozen program')
        idx,labels=_all_cells(holdout)
        errors=int(np.count_nonzero(table[idx]!=labels))
    result=_signed({'schema':VERSION+':evaluation','freeze_sha256':_sha(frozen),
         'holdout_sha256':holdout.fingerprint,'test_count':len(holdout.rows),
         'status':'EVALUATED' if errors is not None else 'ABSTAIN','test_errors':errors,
         'commitment_verified':record['holdout_commitment'] is not None,
         'evidence_grade':EVIDENCE_GRADE,'lottery_predictive_advantage':'NOT_ESTABLISHED'})
    _write_new(root/'evaluation.json',result)
    return result
