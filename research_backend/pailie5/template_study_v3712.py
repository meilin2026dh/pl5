"""Predeclared, fully reproducible V3.7.12 restricted-template transfer study.

All target truth tables are synthesized independently of fitter. No external
lottery evidence. Candidate-slot comparison does not equal full CPU-cost match.
"""
from __future__ import annotations
from hashlib import sha256
import json
from math import comb
import numpy as np

from .generated_study_v3710 import challenge_data
from .primitive_study_v377 import split_truth
from .cross_task_v3711 import FrozenBudgetedPrimitive,certify_transfer_bank
from .template_transfer_v3712 import TemplateConfig,evaluate_template_pair,source_acquisition_ledger
from .shift_windows_v3712 import monitor_preplanned_windows
from .structure_search_v372 import CellDataset

CASES=('swapped_xor','swapped_abs','lifted_gcd','canonical_early','outside_grammar','iid_random')
SOURCE_CASES=('xor_shift','abs_scaled','gcd_shift')


def _canon(o):
    return json.dumps(o,sort_keys=True,ensure_ascii=True,separators=(',',':'),allow_nan=False).encode()


def protocol(seeds=(9811,9812,9813,9814,9815,9816)):
    if (not isinstance(seeds,(tuple,list)) or not 1<=len(seeds)<=12 or
            len(seeds)!=len(set(seeds)) or
            any(type(s) is not int or not 9800<=s<10000 for s in seeds)):
        raise ValueError('invalid seed sequence')
    return {'schema':'pl5-v3712-protocol-1','cases':CASES,'seeds':tuple(seeds),
            'source_cases':SOURCE_CASES,'source_seed_first':9311,'source_seed_stride':131,
            'target_seeds_times':43,'target_seed_case_offset':127,
            'target_train_cells':70,'target_holdout_cells':30,
            'target_candidate_feature_slots_each_arm':16,
            'new_template_rule':'source specs, swapped unaries, lifted-left unary, then canonical order',
            'knowledge_source':'certified source independent train and holdout',
            'source_cost_included_in_ledger':True,
            'full_pipeline_compute_matched':False,
            'null_schedules':512,'null_seed':371201,
            'prespecified_windows':4,'window_length':20,
            'iid_noise_rate':0.02,'family_alpha':0.01,
            'holdout_selection':'no holdout used before freeze; all variants fixed in protocol',
            'scientific_scope':'synthetic digit function tables; near-class unary-template transfer only',
            'production_enabled':False,'predictive_advantage':'NOT_ESTABLISHED'}


def target_truth(case,seed):
    """Independent mathematical reference; does not call fitter grammar/feature."""
    if case not in CASES or type(seed) is not int or not 0<=seed<2**32:
        raise ValueError('invalid synthetic task case or seed')
    rng=np.random.default_rng(seed+371212)
    a,b=np.indices((10,10),dtype=np.int64)
    u=rng.integers(0,10,size=10)[a]
    v=rng.integers(0,10,size=10)[b]
    k=int(rng.choice([1,3,7,9]))
    if case=='swapped_xor':feature=np.bitwise_xor(a*a,b+1)
    elif case=='swapped_abs':feature=np.abs((a+1)-(2*b+1))
    elif case=='lifted_gcd':feature=np.gcd(a*a,b+1)
    elif case=='canonical_early':feature=a*a*(b//3)
    elif case=='outside_grammar':feature=np.where((a+3*b)%7<3,np.bitwise_xor(a+1,b*b),np.gcd(a+1,b+1))
    else:return rng.integers(0,10,size=(10,10),dtype=np.uint8)
    return np.asarray((u+v+k*feature)%10,dtype=np.uint8)


def _window_schedule(rng,errors=(0,0,0,0)):
    order=rng.permutation(100)
    rows=[]
    for t in range(4):
        sample=order[t*20:(t+1)*20]
        rows.append(CellDataset(tuple((int(i//10),int(i%10),int(j<errors[t]))
                                      for j,i in enumerate(sample))))
    return tuple(rows)


def false_alarm_experiment(settings):
    """Empirical Monte Carlo under an expressly iid artificial zero-truth model.

    Preplanned four windows only. This DOES NOT validate real-world stationary
    noise, real chronology, or drift prediction before labels arrive.
    """
    rng=np.random.default_rng(settings['null_seed'])
    completion=tuple([0]*100)
    fixed=FrozenBudgetedPrimitive('provisional_identified',completion,
                                  ('id','mul','id'),tuple(),'0'*64,None,1,1,'synthetic zero oracle')
    false_alarms=0
    for _ in range(settings['null_schedules']):
        windows=[]
        ids=rng.permutation(100)
        for w in range(4):
            block=ids[w*20:(w+1)*20]
            noisy=rng.binomial(1,settings['iid_noise_rate'],size=20)
            windows.append(CellDataset(tuple((int(i//10),int(i%10),int(noisy[j]))
                                             for j,i in enumerate(block))))
        result=monitor_preplanned_windows(fixed,tuple(windows),
                                        alpha_total=settings['family_alpha'],
                                        expected_error_rate=settings['iid_noise_rate'])
        false_alarms+=result['status']=='shift_suspected'
    shifted=monitor_preplanned_windows(fixed,_window_schedule(np.random.default_rng(371299),
                                              (0,0,14,14)),
                                       alpha_total=settings['family_alpha'],
                                       expected_error_rate=settings['iid_noise_rate'])
    p=settings['iid_noise_rate'];threshold=None
    for k in range(21):
        tail=sum(comb(20,i)*p**i*(1-p)**(20-i) for i in range(k,21))
        if tail<=settings['family_alpha']/4:
            threshold=k;break
    single=sum(comb(20,i)*p**i*(1-p)**(20-i) for i in range(threshold,21))
    return {'schema':'pl5-v3712-shift-null-evaluation-1',
            'null_schedules':settings['null_schedules'],'false_alarms':false_alarms,
            'empirical_null_fpr':false_alarms/settings['null_schedules'],
            'fixed_family_alpha':settings['family_alpha'],
            'prespecified_windows_per_schedule':4,
            'per_window_alpha':settings['family_alpha']/4,
            'min_errors_to_trigger_per_window':threshold,
            'theoretical_familywise_iid_null_rate':1-(1-single)**4,
            'shift_alarm':shifted['status']=='shift_suspected',
            'first_shift_window':shifted['first_flagged_window'],
            'drift_is_observed_not_predicted':True,'production_enabled':False,
            'null_assumptions':'independent iid label errors at fixed 2% rate; 4 nonadaptive looks'}


def run_study(settings):
    if not isinstance(settings,dict):
        raise ValueError('invalid protocol')
    try:expected=protocol(tuple(settings.get('seeds',())))
    except (TypeError,ValueError) as e:raise ValueError('invalid protocol') from e
    if _canon(settings)!=_canon(expected):
        raise ValueError('modified protocol refused')
    source_tasks=[]
    for i,case in enumerate(SOURCE_CASES):
        seed=settings['source_seed_first']+i*settings['source_seed_stride']
        source_tasks.append(split_truth(challenge_data(case,seed),seed+17))
    bank=certify_transfer_bank(tuple(source_tasks))
    ledger=source_acquisition_ledger(bank,tuple(source_tasks))
    trials=[]
    for case_i,case in enumerate(CASES):
        for seed in settings['seeds']:
            target_seed=seed*settings['target_seeds_times']+case_i*settings['target_seed_case_offset']
            truth=target_truth(case,target_seed)
            train,held=split_truth(truth,target_seed+17)
            paired=evaluate_template_pair(train,held,bank,TemplateConfig(
                settings['target_candidate_feature_slots_each_arm']))
            trials.append({'case':case,'seed':seed,'target_seed':target_seed,
                           'target_truth_sha256':sha256(truth.tobytes()).hexdigest(),
                           'fit_used_target_holdout_labels':False,
                           'frozen_before_holdout':True,
                           **paired})
    positive=[t for t in trials if t['case'] in CASES[:3]]
    negative=[t for t in trials if t['case'] in CASES[3:]]
    null=false_alarm_experiment(settings)
    n=len(trials)
    summary={'schema':'pl5-v3712-summary-1','target_trials':n,
             'related_unary_target_trials':len(positive),
             'related_exact_transfer':sum(t['source_informed']['heldout_errors']==0 for t in positive),
             'related_canonical_exact':sum(t['canonical']['heldout_errors']==0 for t in positive),
             'canonical_early_control_trials':len([t for t in negative if t['case']=='canonical_early']),
             'canonical_early_exact':sum(t['canonical']['heldout_errors']==0 for t in negative if t['case']=='canonical_early'),
             'canonical_early_negative_transfer':sum(t['source_informed']['status']!='provisional_identified' and
                  t['canonical']['heldout_errors']==0 for t in negative if t['case']=='canonical_early'),
             'out_of_grammar_abstained':sum(t['source_informed']['status']!='provisional_identified' for t in negative if t['case']=='outside_grammar'),
             'iid_random_abstained':sum(t['source_informed']['status']!='provisional_identified' for t in negative if t['case']=='iid_random'),
             'source_feature_tables_examined':ledger['source_feature_tables_examined'],
             'source_coefficient_proposals':ledger['source_coefficient_proposals'],
             'target_feature_slots_each_arm':settings['target_candidate_feature_slots_each_arm'],
             'total_target_slots_guided':n*settings['target_candidate_feature_slots_each_arm'],
             'total_target_slots_canonical':n*settings['target_candidate_feature_slots_each_arm'],
             'guided_plus_source_feature_table_lower_bound':n*settings['target_candidate_feature_slots_each_arm']+ledger['source_feature_tables_examined'],
             'amortized_source_feature_tables_per_target':ledger['source_feature_tables_examined']/n,
             'full_pipeline_compute_matched':False,
             'source_cost_included_in_ledger':True,
             'production_enabled':False,'real_lottery_advantage_established':False}
    return {'schema':'pl5-v3712-study-results-1',
            'protocol_sha256':sha256(_canon(settings)).hexdigest(),
            'protocol':settings,'source_bank':bank.to_dict(),
            'source_cost_ledger':ledger,'shift_controls':null,
            'trials':trials,'summary':summary}
