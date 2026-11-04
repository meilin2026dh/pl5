"""V3.7.8 predeclared synthetic challenge; no real draw observations."""
from __future__ import annotations
from hashlib import sha256
import json
import numpy as np

from .coupled_primitives_v378 import fit_coupled_primitive, evaluate_coupled
from .latent_primitives_v377 import fit_additive_primitive, evaluate_frozen_latent
from .primitive_study_v377 import make_truth, split_truth

CASES = ('latent_quadratic','latent_cubic','latent_mixed',
         'coupled_product','coupled_threshold','iid_random', 'piecewise_absolute', 'rank_one_quadratic')


def _serialize(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',',':'),allow_nan=False).encode()


def preregister(seeds: tuple[int,...]=(8101,8102,8103,8104,8105,8106,8107,8108,8109,8110)) -> dict:
    if (type(seeds) is not tuple or not 1 <= len(seeds) <= 100 or
            any(type(s) is not int or not 0 <= s < 1_000_000 for s in seeds) or
            len(set(seeds)) != len(seeds)):
        raise ValueError('invalid seeds')
    return {'schema':'pl5-v378-preregistered-1','seeds':seeds,'cases':CASES,
            'train_pairs':70,'test_pairs':30,'truth_seed':'s*17+7',
            'split_seed':'s*17+8','selection':'train-only, no holdout model switch',
            'family_policy':'additive-first, then rank-one bilinear, then threshold piecewise; abstain on ambiguity',
            'scope':'fixed synthetic classes; no model advantage claim for real lottery',
            'production_enabled':False}


def challenge_truth(case: str, seed: int) -> np.ndarray:
    if case not in CASES or type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError('invalid case or seed')
    if case not in ('piecewise_absolute','rank_one_quadratic'):
        return make_truth(case,seed)
    a,b = np.indices((10,10),dtype=np.int64)
    rng = np.random.default_rng(seed+278)
    coeff = int(rng.choice((1,3,7,9)))
    phase = int(rng.integers(0,10))
    if case == 'rank_one_quadratic':
        return np.asarray((coeff*a*a*b + 3*a + 7*b + phase) % 10, dtype=np.uint8)
    return np.asarray((coeff * np.abs(a-b) + (a*b)**2 + phase) % 10,dtype=np.uint8)


def run_registered(settings: dict) -> dict:
    if not isinstance(settings,dict) or _serialize(settings) != _serialize(preregister(tuple(settings.get('seeds',())))):
        raise ValueError('modified or invalid preregistration')
    results=[]
    for case in settings['cases']:
        for seed in settings['seeds']:
            truth = challenge_truth(case,seed*17+7)
            train, holdout = split_truth(truth,seed*17+8)
            fitted = fit_coupled_primitive(train)
            audit = evaluate_coupled(fitted,holdout) if fitted.status=='identified' else None
            old = fit_additive_primitive(train)
            old_audit = evaluate_frozen_latent(old,holdout) if old.status=='identified' else None
            results.append({'case':case,'seed':seed,'training_sha256':train.fingerprint,
                            'holdout_sha256':holdout.fingerprint,
                            'train_pairs':len(train.rows),'test_pairs':len(holdout.rows),
                            'frozen':fitted.to_dict(),'identified':fitted.status=='identified',
                            'new_family':fitted.family,'holdout_errors':audit['errors'] if audit else None,
                            'holdout_accuracy':audit['accuracy'] if audit else None,
                            'v377_additive_identified':old.status=='identified',
                            'v377_additive_holdout_accuracy':old_audit['accuracy'] if old_audit else None,
                            'production_enabled':False})
    positives=[r for r in results if r['case'] in ('latent_quadratic','latent_cubic','latent_mixed','coupled_product','coupled_threshold')]
    negatives=[r for r in results if r['case'] in ('iid_random','piecewise_absolute','rank_one_quadratic')]
    identified=[r for r in positives if r['identified']]
    return {'schema':'pl5-v378-results-1',
            'protocol_sha256':sha256(_serialize(settings)).hexdigest(),
            'trials':results,
            'summary':{'trials':len(results),'positive_trials':len(positives),
                       'negative_trials':len(negatives),
                       'positives_identified':len(identified),
                       'positives_exact_holdout':sum(r['holdout_errors']==0 for r in positives),
                       'negative_abstentions':sum(not r['identified'] for r in negatives),
                       'no_real_lottery_advantage':True,
                       'not_compute_matched_to_v377':True}}
