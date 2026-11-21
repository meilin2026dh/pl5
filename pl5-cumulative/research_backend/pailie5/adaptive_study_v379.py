"""V3.7.9 sealed, deterministic synthetic study of bounded grammar search.

Study case labels are used only to generate datasets and summarize outcomes.
Fitter receives CellDataset(training) and never the case label or heldout cells.
"""
from __future__ import annotations
from hashlib import sha256
import json
import numpy as np

from .structure_search_v372 import CellDataset
from .primitive_study_v377 import split_truth
from .adaptive_primitives_v379 import fit_adaptive_primitive, evaluate_adaptive, BASIS, PREDICATES
from .coupled_primitives_v378 import fit_coupled_primitive, evaluate_coupled

CASES = ('rank_a2b','rank_ab2','rank_parityb','rank_bucketb',
         'split_sum','split_difference','legacy_coupled_product','legacy_threshold',
         'iid_random','two_interactions','unmodeled_abs')
POSITIVE = frozenset(CASES[:8])


def _encode(data):
    return json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(',',':'),allow_nan=False).encode()


def protocol(seeds: tuple[int,...]=(9201, 9202, 9203, 9204, 9205,
                                   9206, 9207, 9208, 9209, 9210, 9211, 9212)) -> dict:
    if not isinstance(seeds,tuple) or len(seeds)<1 or len(seeds)>40 or len(set(seeds))!=len(seeds) or any(
        type(s) is not int or not 1<=s<=1_000_000 for s in seeds
    ):
        raise ValueError('invalid study seeds')
    return {'schema':'pl5-v379-preregistered-1','cases':CASES,'seeds':seeds,
            'train_count':70,'holdout_count':30,'truth_seed_formula':'seed*37 + case-index*311',
            'split_seed_formula':'seed*37 + case-index*311 + 1',
            'candidate_basis':BASIS,'candidate_boundaries':PREDICATES,
            'selection':'training-cells only; freeze before holdout evaluation',
            'uncertainty':'abstain on missing identification or disagreeing model completions',
            'random_controls':('iid_random','two_interactions','unmodeled_abs'),
            'compare':'v378 prior fit; algorithmic costs NOT equal',
            'scope':'predefined synthetic structures; no out-of-distribution advantage claim',
            'production_enabled':False, 'predictive_advantage':'NOT_ESTABLISHED'}


def challenge_truth(case: str, seed: int) -> np.ndarray:
    if case not in CASES or type(seed) is not int or not 0<=seed<2**32:
        raise ValueError('invalid synthetic case/seed')
    rng=np.random.default_rng(seed+117)
    a,b=np.indices((10,10),dtype=np.int64)
    coeff=rng.choice(np.array([1,3,7,9]),size=5)
    phase=int(rng.integers(0,10))
    u=coeff[0]*a*a+coeff[1]*a+phase
    v=coeff[2]*b*b+coeff[3]*b
    k=int(coeff[4])
    if case=='rank_a2b': y=u+v+k*a*a*b
    elif case=='rank_ab2': y=u+v+k*a*b*b
    elif case=='rank_parityb': y=u+v+k*(a%2)*b
    elif case=='rank_bucketb': y=u+v+k*(a//3)*b
    elif case=='split_sum':
        threshold=int(rng.integers(8,12))
        y=np.where(a+b<threshold, coeff[0]*a+coeff[1]*b,
                   coeff[2]*a*b+coeff[3]*a+phase)
    elif case=='split_difference':
        threshold=int(rng.integers(-2,3))
        y=np.where(a-b<threshold, coeff[0]*a+coeff[1]*b,
                   coeff[2]*a*b+coeff[3]*a+phase)
    elif case=='legacy_coupled_product': y=coeff[0]*a*b+coeff[1]*a*a+coeff[2]*b+phase
    elif case=='legacy_threshold':
        y=np.where(a<b,coeff[0]*a+coeff[1]*b,
                   coeff[2]*a*b+coeff[3]*a+phase)
    elif case=='iid_random': return rng.integers(0,10,(10,10),dtype=np.uint8)
    elif case=='two_interactions': y=u+v+k*a*a*b+coeff[3]*a*b*b
    elif case=='unmodeled_abs': y=coeff[0]*np.abs(a-b)+coeff[1]*(a*b)**2+phase
    else: raise AssertionError(case)
    return np.asarray(y%10,dtype=np.uint8)


def run_predeclared(settings: dict) -> dict:
    if not isinstance(settings,dict): raise ValueError('invalid preregistration')
    try: expected=protocol(tuple(settings.get('seeds',())))
    except (TypeError,ValueError) as exc: raise ValueError('invalid preregistration') from exc
    if _encode(settings)!=_encode(expected): raise ValueError('modified preregistration')
    trials=[]
    for case_index,case in enumerate(settings['cases']):
        for seed in settings['seeds']:
            task_seed=seed*37+case_index*311
            train,held=split_truth(challenge_truth(case,task_seed),task_seed+1)
            frozen=fit_adaptive_primitive(train)
            audit=evaluate_adaptive(frozen,held) if frozen.status=='identified' else None
            prior=fit_coupled_primitive(train)
            prior_audit=evaluate_coupled(prior,held) if prior.status=='identified' else None
            trials.append({
                'case':case,'seed':seed,'truth_instance':task_seed,
                'train_pairs':len(train.rows),'held_pairs':len(held.rows),
                'train_sha256':train.fingerprint,'holdout_sha256':held.fingerprint,
                'frozen_without_holdout':True, 'model':frozen.to_dict(),
                'status':frozen.status,'family':frozen.family,'descriptor':frozen.descriptor,
                'holdout_errors':None if audit is None else audit['errors'],
                'holdout_correct':None if audit is None else len(held.rows)-audit['errors'],
                'v378_status':prior.status,
                'v378_holdout_errors':None if prior_audit is None else prior_audit['errors'],
                'production_enabled':False
            })
    pos=[r for r in trials if r['case'] in POSITIVE]
    neg=[r for r in trials if r['case'] not in POSITIVE]
    return {'schema':'pl5-v379-synthetic-results-1',
            'protocol_sha256':sha256(_encode(settings)).hexdigest(),
            'trials':trials,
            'summary':{
                'all_trials':len(trials),'compatible_trials':len(pos),
                'negative_controls':len(neg),
                'compatible_identified':sum(r['status']=='identified' for r in pos),
                'compatible_exact_holdout':sum(r['holdout_errors']==0 for r in pos),
                'negative_abstentions':sum(r['status']!='identified' for r in neg),
                'new_only_identified':sum(r['status']=='identified' and r['v378_status']!='identified' for r in pos),
                'known_model_families_only':True,'real_lottery_advantage_established':False,
                'comparisons_compute_matched':False
            }}
