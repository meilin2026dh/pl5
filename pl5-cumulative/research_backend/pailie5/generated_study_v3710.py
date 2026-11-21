"""Preregistered finite trial set for generated mathematical compositions.

This benchmark deliberately exposes the limited distribution of tested toy
functions. No external source is queried, no lottery predictive power claimed.
"""
from __future__ import annotations

from hashlib import sha256
import json
import numpy as np

from .structure_search_v372 import CellDataset
from .primitive_study_v377 import split_truth
from .adaptive_primitives_v379 import fit_adaptive_primitive
from .generated_primitives_v3710 import (GeneratorConfig,
    fit_counterexample_primitive, evaluate_generated)

CASES = ('xor_shift','abs_scaled','gcd_shift','min_bucket',
         'iid_random','two_component','outside_language','train_noise','concept_drift')
POSITIVE = frozenset(CASES[:4])
NEGATIVE_CONTROLS = frozenset(CASES[4:8])
DRIFT = 'concept_drift'


def _stable(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=True,
                      separators=(',', ':'),allow_nan=False).encode()


def protocol(seeds=(8811,8812,8813,8814,8815,8816,8817,8818)):
    if (not isinstance(seeds,(tuple,list)) or not 1<=len(seeds)<=20 or
            any(type(s) is not int or not 0<=s<2**32 for s in seeds) or
            len(set(seeds))!=len(seeds)):
        raise ValueError('invalid frozen seed list')
    return {'schema':'pl5-v3710-study-protocol-1', 'cases':CASES,
            'seeds':tuple(seeds), 'train_cells':70,'hold_cells':30,
            'max_features':400,'max_fits':256,
            'model_selection':'training labels only, no holdout tuning',
            'grammar':'generated compositions of 8 unary and 6 binary operations',
            'controls':tuple(sorted(NEGATIVE_CONTROLS)),
            'drift_intervention':'heldout operator changed after training',
            'preregistered_noise':'one train label altered by +1 mod10',
            'budget_comparison':'not compute matched against V3.7.9',
            'production_enabled':False, 'predictive_advantage':'NOT_ESTABLISHED'}


def challenge_data(case: str, seed: int) -> np.ndarray:
    """Independent ground-truth implementation, separate from fitter's DSL."""
    if case not in CASES or type(seed) is not int or not 0<=seed<2**32:
        raise ValueError('invalid study case / seed')
    rng=np.random.default_rng(seed+371011)
    a,b=np.indices((10,10),dtype=np.int64)
    u=rng.integers(0,10,size=10,dtype=np.int64)[a]
    v=rng.integers(0,10,size=10,dtype=np.int64)[b]
    k=int(rng.choice([1,3,7,9]))
    if case in ('xor_shift','train_noise','concept_drift'):
        feature=np.bitwise_xor(a+1,b*b)
    elif case=='abs_scaled':
        feature=np.abs((2*a+1)-(b+1))
    elif case=='gcd_shift':
        feature=np.gcd(a+1,b+1)
    elif case=='min_bucket':
        feature=np.minimum(a//3,b*b)
    elif case=='iid_random':
        return rng.integers(0,10,size=(10,10),dtype=np.uint8)
    elif case=='two_component':
        feature=np.bitwise_xor(a+1,b*b)+np.gcd(a+1,b+1)
    elif case=='outside_language':
        feature=np.where((3*a+2*b)%7 < 3,
                         np.bitwise_xor(a+1,b*b), np.gcd(a+1,b+1))
    else:
        raise AssertionError(case)
    return np.asarray((u+v+k*feature)%10,dtype=np.uint8)


def run_predeclared(settings: dict):
    if not isinstance(settings,dict): raise ValueError('invalid preregistration')
    try:
        expected=protocol(tuple(settings.get('seeds',())))
    except (TypeError,ValueError) as exc:
        raise ValueError('invalid preregistration') from exc
    if _stable(settings)!=_stable(expected): raise ValueError('modified preregistration')
    rows=[]
    for case_idx,case in enumerate(settings['cases']):
        for seed in settings['seeds']:
            task_seed=seed*37+case_idx*131
            train,held=split_truth(challenge_data(case,task_seed),task_seed+11)
            if case=='train_noise':
                edited=list(train.rows)
                a,b,y=edited[0]
                edited[0]=(a,b,(y+1)%10)
                train=CellDataset(tuple(edited))
            if case==DRIFT:
                alt=challenge_data('abs_scaled',task_seed)
                held=CellDataset(tuple((a,b,int(alt[a,b])) for a,b,_ in held.rows))
            frozen=fit_counterexample_primitive(train,
                                               GeneratorConfig(settings['max_features'],settings['max_fits']))
            prior=fit_adaptive_primitive(train)
            check=evaluate_generated(frozen,held) if frozen.status=='identified' else None
            rows.append({
                'case':case,'seed':seed,'task_seed':task_seed,
                'train_sha256':train.fingerprint,'held_sha256':held.fingerprint,
                'fit_access_to_holdout_labels':False,'frozen_before_holdout':True,
                'status':frozen.status,'family':frozen.family,'spec':frozen.spec,
                'operator_id':frozen.identity,'model':frozen.to_dict(),
                'held_count':len(held.rows),'held_errors':None if check is None else check['errors'],
                'held_accuracy':None if check is None else check['accuracy'],
                'prior_v379_status':prior.status,
                'train_generated_from_clean_truth':case==DRIFT,
                'evaluated_on_shifted_truth':case==DRIFT,
                'noisy_training_label':case=='train_noise',
                'production_enabled':False,
            })
    positives=[r for r in rows if r['case'] in POSITIVE]
    negatives=[r for r in rows if r['case'] in NEGATIVE_CONTROLS]
    drifting=[r for r in rows if r['case']==DRIFT]
    return {
        'schema':'pl5-v3710-study-results-1',
        'protocol_sha256':sha256(_stable(settings)).hexdigest(),
        'trials':rows,
        'summary':{
            'trials':len(rows),'positives':len(positives),
            'positive_generated':sum(r['family']=='generated_interaction' and r['status']=='identified' for r in positives),
            'positive_identified':sum(r['status']=='identified' for r in positives),
            'positive_exact_holdout':sum(r['held_errors']==0 for r in positives),
            'negative_controls':len(negatives),
            'negative_abstained':sum(r['status']!='identified' for r in negatives),
            'drift_trials':len(drifting),
            'drift_identified_on_training':sum(r['status']=='identified' for r in drifting),
            'drift_heldout_errors':sum(r['held_errors'] or 0 for r in drifting),
            'real_lottery_advantage_established':False,
            'compute_matched_comparison':False,
            'open_ended_mathematics_invented':False,
        }
    }
