"""PL5 V3.7.26 finite-domain *predicate grammar search*.

Research-only candidate for 10x10 Z10 tasks. Fixed whitelisted predicate grammar;
not a newly invented mathematical law. Fit sees training labels only, freeze sees
validation, evaluate sees holdout once. Use third-party *physical isolation* for
independent blind evidence; no such external validation is implied here.
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path
import numpy as np

from .grammar_discovery_v3724 import _all_cells
from .language_evolution_v3722 import _read_checked, _sha, _signed, _write_new, _coordinate_overlap
from .open_grammar_v3725 import _solve_ring, _features as _previous_features
from .structure_search_v372 import CellDataset

VERSION = 'pl5-v3726-gate-grammar-1'
EVIDENCE_GRADE = 'INTERNAL_DEVELOPER_SYNTHETIC_NOT_EXTERNAL_BLIND'
BASIS = ('constant', 'a', 'b', 'product_mod10', 'xor_mod10', 'absdiff_mod10')
MASK_BASES = ('constant', 'a', 'b', 'product_mod10', 'xor_mod10')


def predicate_specs() -> tuple[dict, ...]:
    """Closed, label-free grammar: relations and modular/threshold predicates."""
    result = [{'kind': 'equal'}, {'kind': 'less'}, {'kind': 'greater'}]
    result.extend({'kind': 'sum_ge', 'threshold': t} for t in (5, 8, 10, 12, 15))
    for mod in (2, 3, 4, 5):
        for remainder in range(mod):
            result.append({'kind':'congruence', 'source':'difference',
                           'modulus':mod,'remainder':remainder})
    for remainder in range(3):
        result.append({'kind':'congruence','source':'sum',
                       'modulus':3,'remainder':remainder})
    return tuple(result)


def _predicate(spec:dict) -> np.ndarray:
    if not isinstance(spec,dict) or spec not in predicate_specs():
        raise ValueError('unregistered predicate')
    a,b=np.indices((10,10),dtype=np.int64)
    if spec['kind']=='equal':mask=a==b
    elif spec['kind']=='less':mask=a<b
    elif spec['kind']=='greater':mask=a>b
    elif spec['kind']=='sum_ge':mask=a+b>=spec['threshold']
    elif spec['kind']=='congruence':
        z=a-b if spec['source']=='difference' else a+b
        mask=z%spec['modulus']==spec['remainder']
    else:raise ValueError('unknown predicate')
    return mask.reshape(100).astype(np.int64)


def _full_bank(spec:dict|None) -> tuple[tuple[str,...],np.ndarray]:
    features=_previous_features()
    names=list(BASIS)
    vectors=[features[n].reshape(100) for n in names]
    if spec is not None:
        mask=_predicate(spec)
        names += ['gate_'+n for n in MASK_BASES]
        vectors += [(mask*features[n].reshape(100))%10 for n in MASK_BASES]
    return tuple(names), np.column_stack(vectors).astype(np.int64)%10


def program_table(spec:dict) -> np.ndarray:
    if not isinstance(spec,dict) or set(spec)!={'syntax','predicate','features','coefficients'}:
        raise ValueError('invalid program shape')
    if spec['syntax']!='induced_gate_mod10':raise ValueError('unregistered program syntax')
    predicate=spec['predicate']
    if predicate is not None:
        _predicate(predicate)  # exact whitelist; no code execution
    names,bank=_full_bank(predicate)
    terms=spec['features'];coeff=spec['coefficients']
    if not isinstance(terms,list) or not isinstance(coeff,list) or not terms or len(terms)!=len(coeff):
        raise ValueError('invalid terms')
    if len(terms)>len(names) or len(set(terms))!=len(terms):raise ValueError('duplicated features')
    if any(type(x) is not str or x not in names for x in terms):raise ValueError('unknown feature')
    if any(type(c) is not int or not 0<=c<=9 for c in coeff):raise ValueError('invalid coefficient')
    lookup={name:i for i,name in enumerate(names)}
    return (bank[:,[lookup[x] for x in terms]]@np.asarray(coeff,dtype=np.int64))%10


def commit_holdout(holdout:CellDataset,nonce:str)->str:
    if not isinstance(holdout,CellDataset) or not isinstance(nonce,str) or len(nonce)<16:
        raise ValueError('typed holdout and nonce length >=16 required')
    return hashlib.sha256((VERSION+'|'+nonce+'|'+holdout.fingerprint).encode()).hexdigest()


def fit(training:CellDataset, study_dir:str|Path,*,holdout_digest:str|None=None,
        protocol_sha256:str|None=None)->dict:
    if not isinstance(training,CellDataset):raise ValueError('training must be CellDataset')
    for digest in (holdout_digest,protocol_sha256):
        if digest is not None and (not isinstance(digest,str) or len(digest)!=64 or
                any(c not in '0123456789abcdef' for c in digest)):
            raise ValueError('bad sha256 digest')
    idx,labels=_all_cells(training)
    options=(None,)+predicate_specs()
    trace=[];candidates={}
    begin=time.process_time_ns()
    for pred in options:
        names,bank=_full_bank(pred)
        coefs=_solve_ring(bank[idx],labels)
        entry={'predicate':pred,'basis_columns':len(names),'exact_train_fit':coefs is not None}
        if coefs is not None:
            terms=[(k,int(v)) for k,v in zip(names,coefs) if v!=0]
            if not terms:terms=[('constant',0)]
            program={'syntax':'induced_gate_mod10','predicate':pred,
                     'features':[k for k,_ in terms], 'coefficients':[v for _,v in terms]}
            table=program_table(program)
            if not np.array_equal(table[idx],labels):raise RuntimeError('internal fit inconsistency')
            digest=hashlib.sha256(table.astype('uint8').tobytes()).hexdigest()
            candidates.setdefault(digest,{'spec':program,'table_sha256':digest})
            entry['nonzero_terms']=len(terms)
        trace.append(entry)
    cpu_ns=time.process_time_ns()-begin
    record=_signed({'schema':VERSION+':fit','training_sha256':training.fingerprint,
      'train_pairs':[list(p) for p in training.pairs], 'trace':trace,
      'candidate_evaluations':len(options),'cpu_ns_fit':cpu_ns,
      'exact_fit_tables':list(candidates.values()),'holdout_commitment':holdout_digest,
      'protocol_sha256':protocol_sha256,'training_only':True,
      'evidence_grade':EVIDENCE_GRADE,'lottery_predictive_advantage':'NOT_ESTABLISHED'})
    _write_new(Path(study_dir)/'fit.json',record)
    return record


def freeze(study_dir:str|Path,validation:CellDataset)->dict:
    if not isinstance(validation,CellDataset):raise ValueError('validation must be typed')
    root=Path(study_dir)
    rec=_read_checked(root/'fit.json',VERSION+':fit')
    if _coordinate_overlap(rec['train_pairs'],[list(x) for x in validation.pairs]):
        raise ValueError('training/validation overlap')
    idx,labels=_all_cells(validation)
    survivors=[]
    for candidate in rec['exact_fit_tables']:
        table=program_table(candidate['spec'])
        if hashlib.sha256(table.astype('uint8').tobytes()).hexdigest()!=candidate['table_sha256']:
            raise ValueError('changed fitted program')
        if np.array_equal(table[idx],labels):survivors.append(candidate)
    record=_signed({'schema':VERSION+':freeze','fit_sha256':_sha(rec),
      'validation_sha256':validation.fingerprint,
      'validation_pairs':[list(p) for p in validation.pairs],
      'status':'FROZEN' if len(survivors)==1 else 'ABSTAIN',
      'selected':survivors[0] if len(survivors)==1 else None,
      'survivors':len(survivors),
      'reason':'no_candidate' if not survivors else 'ambiguous' if len(survivors)>1 else None,
      'holdout_seen':False})
    _write_new(root/'freeze.json',record)
    return record


def evaluate(study_dir:str|Path,holdout:CellDataset,*,nonce:str|None=None)->dict:
    if not isinstance(holdout,CellDataset):raise ValueError('holdout must be typed')
    root=Path(study_dir)
    rec=_read_checked(root/'fit.json',VERSION+':fit')
    frozen=_read_checked(root/'freeze.json',VERSION+':freeze')
    if frozen['fit_sha256']!=_sha(rec):raise ValueError('provenance mismatch')
    if _coordinate_overlap(rec['train_pairs'],frozen['validation_pairs'],[list(p) for p in holdout.pairs]):
        raise ValueError('partition overlap')
    if rec['holdout_commitment'] is not None:
        if nonce is None or commit_holdout(holdout,nonce)!=rec['holdout_commitment']:
            raise ValueError('holdout commitment mismatch')
    errors=None
    if frozen['status']=='FROZEN':
        candidate=frozen['selected']
        table=program_table(candidate['spec'])
        if hashlib.sha256(table.astype('uint8').tobytes()).hexdigest()!=candidate['table_sha256']:
            raise ValueError('program changed after freeze')
        idx,labels=_all_cells(holdout)
        errors=int(np.count_nonzero(table[idx]!=labels))
    record=_signed({'schema':VERSION+':evaluation','freeze_sha256':_sha(frozen),
      'holdout_sha256':holdout.fingerprint,'test_count':len(holdout.rows),
      'status':'EVALUATED' if errors is not None else 'ABSTAIN','test_errors':errors,
      'commitment_verified':rec['holdout_commitment'] is not None,
      'evidence_grade':EVIDENCE_GRADE,'lottery_predictive_advantage':'NOT_ESTABLISHED'})
    _write_new(root/'evaluation.json',record)
    return record
