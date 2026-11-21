"""V3.7.7: preregistered synthetic experiment on learned additive digit primitives.

Fixed target families and split seeds are developer-designed controls. The
candidate primitive itself is inferred from TRAINING cells, with no formula
oracle, holdout labels, or lottery data passed to its fit interface.
"""
from __future__ import annotations

from hashlib import sha256
import json
import numpy as np

from .latent_primitives_v377 import fit_additive_primitive, evaluate_frozen_latent
from .structure_search_v372 import CellDataset, SearchConfig, fit
from .structure_evidence_v372 import evaluate_frozen

CASES = ('latent_quadratic', 'latent_cubic', 'latent_mixed',
         'coupled_product', 'coupled_threshold', 'iid_random')


def make_truth(case: str, seed: int) -> np.ndarray:
    if case not in CASES or type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError('unknown synthetic task or seed')
    rng = np.random.default_rng(seed + 937)
    a, b = np.indices((10, 10), dtype=np.int64)
    # Seed changes the underlying table, not merely the pair split.
    # The synthetic structured families are explicitly known to the designer.
    coeff = rng.choice(np.array((1, 3, 7, 9)), size=4)
    phase = rng.integers(0, 10, size=2)
    if case == 'latent_quadratic':
        out = (coeff[0]*a*a + coeff[1]*a + phase[0] +
               coeff[2]*b*b + coeff[3]*b + phase[1]) % 10
    elif case == 'latent_cubic':
        out = (coeff[0]*a**3 + coeff[1]*a + phase[0] +
               coeff[2]*b**3 + coeff[3]*b*b + phase[1]) % 10
    elif case == 'latent_mixed':
        out = (np.abs(coeff[0]*a*a - coeff[1]*a) + phase[0] +
               coeff[2]*b**3 + coeff[3]*b + phase[1]) % 10
    elif case == 'coupled_product':
        out = (coeff[0]*a*b + coeff[1]*a*a + coeff[2]*b + phase[0]) % 10
    elif case == 'coupled_threshold':
        out = np.where(a < b, coeff[0]*a + coeff[1]*b,
                       coeff[2]*a*b + coeff[3]*a + phase[0]) % 10
    else:
        out = rng.integers(0, 10, (10, 10))
    return np.asarray(out, dtype=np.uint8)


def split_truth(truth: np.ndarray, seed: int) -> tuple[CellDataset, CellDataset]:
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError('invalid split seed')
    from .math_language_v37 import validate_table
    values = validate_table(truth)
    ids = np.random.default_rng(seed).permutation(100)
    def create(indices):
        return CellDataset(tuple((int(i//10),int(i%10),int(values.flat[i])) for i in indices))
    return create(ids[:70]), create(ids[70:])


def protocol(seeds: tuple[int,...]=(712,713,714,715,716), budget: int=500) -> dict:
    if (type(budget) is not int or not 100 <= budget <= 50000 or
            not isinstance(seeds, tuple) or len(seeds) == 0 or len(seeds) > 30 or
            any(type(n) is not int or n < 0 or n >= (2**32-20000)//17 for n in seeds) or
            len(seeds) != len(set(seeds))):
        raise ValueError('invalid preregistration values')
    return {'schema':'pl5-v377-preregistered-experiment-2',
            'cases':CASES, 'seeds':seeds, 'train_pairs_per_trial':70,
            'test_pairs_per_trial':30,
            'split_seed_formula':'seed*17+8',
            'target_seed_formula':'seed*17+7',
            'target_generator_version':'seeded_coefficients_2',
            'max_baseline_evaluations_per_trial':budget,
            'model_class':'two inferred unary digit maps, additive mod10',
            'baseline_class':'V3.7.2 safe integer AST grammar',
            'baseline_config':{'generations':3,'population':24,'beam_width':12,
                               'max_nodes':9,'max_depth':5,'complexity_penalty':0.01},
            'selection':'training-only; no holdout-driven model switch',
            'statistical_scope':'descriptive synthetic paired controls, no confirmatory inference',
            'cost_comparison':'NOT_COMPUTE_MATCHED',
            'production_enabled':False,'predictive_advantage':'NOT_ESTABLISHED'}


def run_trial(case: str, seed: int, budget: int=500) -> dict:
    settings=protocol((seed,),budget)
    if case not in CASES:
        raise ValueError('unknown case')
    truth = make_truth(case, seed*17+7)
    train, unseen = split_truth(truth, seed*17+8)
    latent = fit_additive_primitive(train)
    base = fit(train, SearchConfig(
        seed=seed, max_evaluations=budget,
        **settings['baseline_config']))
    base_out = evaluate_frozen(base.operator, unseen)
    latent_out = evaluate_frozen_latent(latent, unseen) if latent.status=='identified' else None
    return {'schema':'pl5-v377-trial-result-1','case':case,'seed':seed,
            'train_pairs':len(train.rows),'test_pairs':len(unseen.rows),
            'train_sha256':train.fingerprint,'holdout_sha256':unseen.fingerprint,
            'model_status':latent.status,
            'constraint_conflicts':latent.constraint_conflicts,
            'latent_model':latent.to_dict(),
            'latent_holdout_accuracy':None if latent_out is None else latent_out['accuracy'],
            'latent_holdout_errors':None if latent_out is None else latent_out['errors'],
            'baseline_holdout_accuracy':base_out['accuracy'],
            'baseline_holdout_count':base_out['count'],
            'baseline_expressions_evaluated':base.evaluated_expressions,
            'baseline_operator':base.operator.to_dict(),
            'provenance':'synthetic target; train/holdout split before fits; no lottery evidence',
            'production_enabled':False}


def _canonical(obj: dict)->bytes:
    return json.dumps(obj,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def run_predeclared(settings: dict) -> dict:
    if (not isinstance(settings, dict) or
            _canonical(settings) != _canonical(protocol(
                tuple(settings.get('seeds',())), settings.get('max_baseline_evaluations_per_trial',0)))):
        raise ValueError('unrecognized or modified protocol')
    results=[run_trial(case,seed,settings['max_baseline_evaluations_per_trial'])
             for case in settings['cases'] for seed in settings['seeds']]
    positive=[x for x in results if x['case'].startswith('latent_')]
    negative=[x for x in results if not x['case'].startswith('latent_')]
    accepted=[x for x in positive if x['model_status']=='identified']
    total_pos=sum(x['test_pairs'] for x in positive)
    return {'schema':'pl5-v377-experiment-result-1',
            'protocol_sha256':sha256(_canonical(settings)).hexdigest(),
            'trials':results,
            'summary':{'trials':len(results),'structured_tasks':len(positive),
                       'negative_controls':len(negative),
                       'positive_identified':len(accepted),
                       'positive_holdout_accuracy':(sum(x['test_pairs']-x['latent_holdout_errors'] for x in accepted)/total_pos
                                                  if len(accepted)==len(positive) else None),
                       'negative_rejected':sum(x['model_status']=='rejected_inconsistent' for x in negative),
                       'baseline_positive_holdout_accuracy':sum((x['test_pairs']*x['baseline_holdout_accuracy']) for x in positive)/total_pos,
                       'computation_matched':False,
                       'real_lottery_advantage_established':False}}
