"""V3.7.23: verified V3.7.22 lookup -> compact program -> target-task transfer.

Research-only, bounded digit domain. No arbitrary code evaluation. The source bank
has certified V3.7.22 studies, while target programs are fitted only to target
training labels, validated independently, and scored once on a disjoint holdout.
Synthetic tests here are developer designed, NOT an external blind study.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

import numpy as np
from .language_evolution_v3722 import (
    VERSION as SOURCE_VERSION, _features, _validate_spec, _read_checked,
    _sha, _signed, _write_new, _coordinate_overlap, RESEARCH_ONLY,
)
from .structure_search_v372 import CellDataset

VERSION = 'pl5-v3723-cross-task-program-1'
KINDS = ('constant', 'parity', 'step', 'poly1', 'poly2', 'poly3')
CANDIDATE_BUDGET = 8


def _outputs(program: dict, xs: np.ndarray) -> np.ndarray:
    if not isinstance(program, dict) or program.get('kind') not in KINDS:
        raise ValueError('unregistered program')
    params = program.get('params')
    if not isinstance(params, list) or any(type(p) is not int or not 0 <= p <= 9 for p in params):
        raise ValueError('invalid parameters')
    kind = program['kind']
    if kind == 'constant' and len(params) == 1:
        return np.full_like(xs, params[0], dtype=np.int64)
    if kind == 'parity' and len(params) == 2:
        return np.where(xs % 2 == 0, params[0], params[1]).astype(np.int64)
    if kind == 'step' and len(params) == 3 and 1 <= params[0] <= 9:
        return np.where(xs < params[0], params[1], params[2]).astype(np.int64)
    if kind.startswith('poly') and len(params) == int(kind[-1]) + 1:
        out = np.zeros_like(xs, dtype=np.int64)
        # coefficients stored constant-first
        for c in reversed(params):
            out = (out * xs + c) % 10
        return out
    raise ValueError('malformed program')


def _mdl_bits(program: dict) -> int:
    # Explicit simple prefix-cost proxy; NOT an optimal universal code.
    return 5 + 4 * len(program['params'])


def compress_lookup(spec: dict, source_train_sha256: str) -> dict | None:
    """Exhaustively fit short grammar to one COMPLETE, verified V3.7.22 source map."""
    _validate_spec(spec, source_train_sha256)
    if any(v is None for v in spec['mapping']):
        return None
    feature = spec['feature']
    xs = np.asarray(spec['domain'], dtype=np.int64)
    ys = np.asarray(spec['mapping'], dtype=np.int64)
    candidates = []
    # Fixed bounded DSL: no dynamic Python and no arbitrary AST deserialization.
    candidates += [{'kind':'constant','params':[v]} for v in range(10)]
    candidates += [{'kind':'parity','params':[e,o]} for e in range(10) for o in range(10)]
    candidates += [{'kind':'step','params':[threshold,lo,hi]}
                   for threshold in range(1,10) for lo in range(10) for hi in range(10)]
    for degree in (1,2,3):
        for coef in itertools.product(range(10), repeat=degree+1):
            candidates.append({'kind':f'poly{degree}','params':list(coef)})
    valid = [p for p in candidates if np.array_equal(_outputs(p,xs),ys)]
    if not valid:
        return None
    selected = min(valid,key=lambda p:(_mdl_bits(p),KINDS.index(p['kind']),p['params']))
    lookup_bits = 5 + 4 * len(xs)
    if _mdl_bits(selected) >= lookup_bits:
        return None
    base = _features()[feature]
    _, original = _validate_spec(spec,source_train_sha256)
    reconstructed = _outputs(selected,base)
    if not np.array_equal(reconstructed, original):
        raise ValueError('compressed program does not reconstruct verified source model')
    return {'schema':VERSION+':program','feature':feature,'kind':selected['kind'],
            'params':selected['params'],'mdl_proxy_bits':_mdl_bits(selected),
            'lookup_proxy_bits':lookup_bits,
            'source_candidate_id':spec['candidate_id'],
            'source_training_sha256':source_train_sha256,
            'finite_table_sha256':hashlib.sha256(reconstructed.astype('uint8').tobytes()).hexdigest(),
            'finite_domain_only':True}


def _check_program(program: dict):
    if not isinstance(program,dict) or program.get('schema')!=VERSION+':program' or program.get('feature') not in _features():
        raise ValueError('invalid program grammar')
    _outputs({'kind':program['kind'],'params':program['params']},np.array([0],dtype=np.int64))
    if not isinstance(program.get('source_candidate_id'),str) or len(program['source_candidate_id'])!=64:
        raise ValueError('unbound source program')


def certify_source_bank(source_studies: list[str|Path], dest: str|Path):
    """Accept only certified, frozen, evaluated V3.7.22 studies, never source test labels for fitting."""
    if not 1 <= len(source_studies) <= 20:
        raise ValueError('source study count outside research limit')
    templates = []
    seen_sources = set()
    for source in source_studies:
        folder=Path(source)
        proposal=_read_checked(folder/'proposal.json',SOURCE_VERSION+':proposal')
        falsification=_read_checked(folder/'falsification.json',SOURCE_VERSION+':challenge')
        freeze=_read_checked(folder/'freeze.json',SOURCE_VERSION+':freeze')
        evaluated=_read_checked(folder/'evaluation.json',SOURCE_VERSION+':evaluation')
        final=_read_checked(folder/'final_operator.json',SOURCE_VERSION+':operator')
        if (proposal['training_sha256'] in seen_sources or
            falsification['proposal_sha256']!=_sha(proposal) or
            freeze['challenge_sha256']!=_sha(falsification) or
            freeze['proposal_sha256']!=_sha(proposal) or
            freeze['status']!='FROZEN' or evaluated['status']!='EVALUATED' or
            evaluated['holdout_errors']!=0 or evaluated['holdout_unknown']!=0 or
            final['proposal_sha256']!=_sha(proposal) or
            final['spec']['candidate_id'] != freeze['selected_id']):
            raise ValueError('source not independently certified or provenance broken')
        selected=next((c for c in proposal['candidates'] if c['spec']==final['spec']),None)
        if selected is None:
            raise ValueError('source operator not among pre-registered proposals')
        seen_sources.add(proposal['training_sha256'])
        program=compress_lookup(final['spec'],proposal['training_sha256'])
        if program is not None:
            templates.append({**program,'source_evaluation_sha256':_sha(evaluated)})
    # Different source studies may discover identical templates; retain one.
    unique={}
    for p in templates:
        key=(p['feature'],p['kind'],tuple(p['params']))
        unique.setdefault(key,p)
    bank={'schema':VERSION+':bank','templates':list(unique.values()),
          'source_training_sha256':sorted(seen_sources),'source_count':len(seen_sources),
          'source_full_holdout_evaluated':True,'origin':'V3722 source-certified lookup compression',
          'lottery_predictive_advantage':'NOT_ESTABLISHED','external_blind':False}
    _write_new(Path(dest),_signed(bank))
    return bank


def _bank(path:Path)->dict:
    b=_read_checked(path,VERSION+':bank')
    if b['source_count']<1 or len(b['source_training_sha256'])!=b['source_count'] or len(b['templates'])>20:
        raise ValueError('invalid source inventory')
    for p in b['templates']:
        _check_program(p)
    return b


def _table(template:dict,scale:int,shift:int)->np.ndarray:
    _check_program(template)
    feature=_features()[template['feature']]
    base=_outputs({'kind':template['kind'],'params':template['params']},feature)
    return (scale*base+shift)%10


def public_holdout_digest(holdout:CellDataset, nonce:str) -> str:
    """Opaque external-setter hash; nonce MUST be withheld until after freeze.

    This is a hash commitment, NOT a trusted timestamp or access control.
    """
    if not isinstance(holdout,CellDataset) or not isinstance(nonce,str) or len(nonce)<16:
        raise ValueError('holdout and >=16 character nonce required')
    return hashlib.sha256((VERSION+'|holdout|'+nonce+'|'+holdout.fingerprint).encode()).hexdigest()


def fit_target(training:CellDataset,bank_path:str|Path,study_path:str|Path, *,
               candidate_budget:int=CANDIDATE_BUDGET, holdout_commitment:str|None=None):
    if not isinstance(training,CellDataset) or type(candidate_budget) is not int or not 1 <= candidate_budget <= 8:
        raise ValueError('bad target fit inputs')
    if holdout_commitment is not None and (len(holdout_commitment)!=64 or any(c not in '0123456789abcdef' for c in holdout_commitment)):
        raise ValueError('invalid public holdout commitment')
    bank=_bank(Path(bank_path))
    if training.fingerprint in bank['source_training_sha256']:
        raise ValueError('source/target training data reuse prohibited')
    pool=[]
    # Budget is template evaluations, NOT total CPU or source-discovery compute.
    for idx,template in enumerate(bank['templates'][:candidate_budget]):
        for scale in (1,3,7,9):
            for shift in range(10):
                grid=_table(template,scale,shift)
                if all(int(grid[a,b])==v for a,b,v in training.rows):
                    definition={'template_index':idx,'scale':scale,'shift':shift,
                                'table_sha256':hashlib.sha256(grid.astype('uint8').tobytes()).hexdigest()}
                    pool.append(definition)
    record=_signed({'schema':VERSION+':fit','bank_sha256':_sha(bank),
                    'training_sha256':training.fingerprint,
                    'training_pairs':[list(pair) for pair in training.pairs],
                    'candidate_budget':candidate_budget,'templates_examined':min(candidate_budget,len(bank['templates'])),
                    'parameterizations_examined':40*min(candidate_budget,len(bank['templates'])),
                    'candidates':pool, 'test_labels_used':False, 'source_cost_excluded':True,
                    'precommitted_holdout_digest':holdout_commitment,
                    'external_blind':False,'lottery_predictive_advantage':'NOT_ESTABLISHED'})
    _write_new(Path(study_path)/'fit.json',record)
    return record


def freeze_target(study_path:str|Path,bank_path:str|Path,validation:CellDataset):
    if not isinstance(validation,CellDataset):
        raise ValueError('invalid validation')
    root=Path(study_path)
    fit=_read_checked(root/'fit.json',VERSION+':fit')
    bank=_bank(Path(bank_path))
    if _sha(bank)!=fit['bank_sha256']:
        raise ValueError('bank content changed')
    if _coordinate_overlap(fit['training_pairs'],[list(p) for p in validation.pairs]):
        raise ValueError('target train/validation overlap')
    survivors=[]
    for c in fit['candidates']:
        template=bank['templates'][c['template_index']]
        grid=_table(template,c['scale'],c['shift'])
        digest=hashlib.sha256(grid.astype('uint8').tobytes()).hexdigest()
        if c['table_sha256']!=digest:
            raise ValueError('candidate table changed')
        if all(int(grid[a,b])==y for a,b,y in validation.rows):
            survivors.append(c)
    unique={c['table_sha256']:c for c in survivors}
    status='FROZEN' if len(unique)==1 else 'ABSTAIN'
    winner=sorted(unique.values(),key=lambda c:(c['template_index'],c['scale'],c['shift']))[0] if status=='FROZEN' else None
    record=_signed({'schema':VERSION+':freeze','fit_sha256':_sha(fit),
                    'validation_sha256':validation.fingerprint,
                    'validation_pairs':[list(p) for p in validation.pairs],
                    'status':status,'reason':None if winner else ('no_survivors' if not survivors else 'ambiguous_distinct_tables'),
                    'selected':winner,'surviving_parameterizations':len(survivors),
                    'distinct_surviving_tables':len(unique),'holdout_used':False})
    _write_new(root/'freeze.json',record)
    return record


def evaluate_target(study_path:str|Path,bank_path:str|Path,holdout:CellDataset,*,reveal_nonce:str|None=None):
    if not isinstance(holdout,CellDataset):
        raise ValueError('invalid holdout')
    root=Path(study_path)
    fit=_read_checked(root/'fit.json',VERSION+':fit')
    frozen=_read_checked(root/'freeze.json',VERSION+':freeze')
    bank=_bank(Path(bank_path))
    if frozen['fit_sha256']!=_sha(fit) or fit['bank_sha256']!=_sha(bank):
        raise ValueError('provenance chain broken')
    if _coordinate_overlap(fit['training_pairs'],frozen['validation_pairs'],[list(p) for p in holdout.pairs]):
        raise ValueError('target holdout overlaps used data')
    if fit['precommitted_holdout_digest'] is not None:
        if reveal_nonce is None or public_holdout_digest(holdout,reveal_nonce)!=fit['precommitted_holdout_digest']:
            raise ValueError('external holdout commitment mismatch or missing nonce')
    if frozen['status']=='ABSTAIN':
        status,errors,unknown='ABSTAIN',None,None
    else:
        c=frozen['selected']
        grid=_table(bank['templates'][c['template_index']],c['scale'],c['shift'])
        if hashlib.sha256(grid.astype('uint8').tobytes()).hexdigest()!=c['table_sha256']:
            raise ValueError('frozen table altered')
        errors=sum(int(grid[a,b]!=y) for a,b,y in holdout.rows)
        status,unknown='EVALUATED',0
    record=_signed({'schema':VERSION+':evaluation','freeze_sha256':_sha(frozen),
                    'holdout_sha256':holdout.fingerprint,'holdout_count':len(holdout.rows),
                    'status':status,'errors':errors,'unknown':unknown,
                    'evidence_grade':'INTERNAL_SYNTHETIC_NOT_EXTERNAL_BLIND',
                    'holdout_commitment_matched':fit['precommitted_holdout_digest'] is not None,
                    'lottery_predictive_advantage':'NOT_ESTABLISHED'})
    _write_new(root/'evaluation.json',record)
    return record
