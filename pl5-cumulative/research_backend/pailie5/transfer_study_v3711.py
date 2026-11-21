"""Predeclared, independent-source synthetic transfer study (PL5 V3.7.11)."""
from __future__ import annotations
from hashlib import sha256
import json
import numpy as np
from .structure_search_v372 import CellDataset
from .primitive_study_v377 import split_truth
from .generated_study_v3710 import challenge_data
from .cross_task_v3711 import (TransferConfig, certify_transfer_bank,
    fit_budgeted_transfer, evaluate_provisional, diagnose_training_noise,
    detect_labeled_shift)

CASES=('xor_shift','abs_scaled','gcd_shift','iid_random','train_noise','concept_drift')
SOURCE_CASES=('xor_shift','abs_scaled','gcd_shift')


def _canon(x):
    return json.dumps(x,ensure_ascii=True,sort_keys=True,
                      separators=(',',':'),allow_nan=False).encode()


def protocol(seeds=(9541,9542,9543,9544,9545,9546)):
    if (not isinstance(seeds,(tuple,list)) or not 1<=len(seeds)<=12 or
            any(type(s) is not int or not 9500<=s<9900 for s in seeds) or
            len(set(seeds))!=len(seeds)):
        raise ValueError('invalid target seed list')
    return {'schema':'pl5-v3711-cross-task-protocol-1',
            'source_cases':SOURCE_CASES,'source_seeds':(9311,),
            'target_cases':CASES,'target_seeds':tuple(seeds),
            'source_train_cells':70,'source_holdout_cells':30,
            'target_train_cells':70,'target_holdout_cells':30,
            'feature_budget_each_arm':8,
            'source_validation':'independent source holdout, zero mistakes',
            'target_model_selection':'frozen-source-priority vs canonical grammar order',
            'comparison_unit':'candidate full-table feature evaluations',
            'source_training_cost_included_in_budget':False,
            'fixed_window_size':20,'iid_noise_rate_null':0.02,'alpha':0.001,
            'noisy_training_intervention':'first training label +1 mod10',
            'drift_intervention':'target test labels from independent new rule',
            'production_enabled':False,'predictive_advantage':'NOT_ESTABLISHED'}


def run_study(settings):
    if not isinstance(settings,dict):
        raise ValueError('invalid preregistration')
    try:
        expected=protocol(tuple(settings.get('target_seeds',())))
    except (TypeError,ValueError) as exc:
        raise ValueError('invalid preregistration') from exc
    if _canon(settings)!=_canon(expected):
        raise ValueError('modified preregistration')
    source_tasks=[]
    source_table_hashes=[]
    for case_i,case in enumerate(SOURCE_CASES):
        seed=settings['source_seeds'][0]+case_i*131
        truth=challenge_data(case,seed)
        train,held=split_truth(truth,seed+17)
        source_tasks.append((train,held))
        source_table_hashes.append(sha256(truth.tobytes()).hexdigest())
    bank=certify_transfer_bank(tuple(source_tasks))
    cfg=TransferConfig(max_features=settings['feature_budget_each_arm'])
    output=[]
    for case_i,case in enumerate(CASES):
        for seed in settings['target_seeds']:
            target_seed=seed*17+case_i*101
            base_case=case if case in SOURCE_CASES or case=='iid_random' else 'xor_shift'
            truth=challenge_data(base_case,target_seed)
            train,held=split_truth(truth,target_seed+17)
            noisy=False
            if case=='train_noise':
                edited=list(train.rows)
                a,b,y=edited[0]
                edited[0]=(a,b,(y+1)%10)
                train=CellDataset(tuple(edited))
                noisy=True
            if case=='concept_drift':
                shifted=challenge_data('abs_scaled',target_seed)
                held=CellDataset(tuple((a,b,int(shifted[a,b])) for a,b,_ in held.rows))
            transfer=fit_budgeted_transfer(train,bank,cfg)
            baseline=fit_budgeted_transfer(train,None,cfg)
            score=(evaluate_provisional(transfer,held) if transfer.status=='provisional_identified' else None)
            base_score=(evaluate_provisional(baseline,held) if baseline.status=='provisional_identified' else None)
            row={
                'case':case,'target_seed':target_seed,'seed':seed,
                'target_truth_sha256':sha256(truth.tobytes()).hexdigest(),
                'train_sha256':train.fingerprint,'holdout_sha256':held.fingerprint,
                'source_bank_id':bank.identity,
                'fit_access_to_target_holdout_labels':False,'frozen_before_target_holdout':True,
                'transfer_status':transfer.status,'transfer_operator_id':transfer.identity,
                'baseline_status':baseline.status,'baseline_operator_id':baseline.identity,
                'feature_evaluations_transfer':transfer.features_checked,
                'feature_evaluations_baseline':baseline.features_checked,
                'transfer_holdout_errors':None if score is None else score['errors'],
                'baseline_holdout_errors':None if base_score is None else base_score['errors'],
                'transfer_provisional_grammar_only':True,
                'production_enabled':False,
                'noise_diagnosis':None,
                'drift_window':None,
            }
            if noisy:
                row['noise_diagnosis']=diagnose_training_noise(train,bank,cfg)
            if case=='concept_drift' and transfer.status=='provisional_identified':
                row['drift_window']=detect_labeled_shift(transfer,CellDataset(held.rows[:20]))
            output.append(row)
    pos=[r for r in output if r['case'] in SOURCE_CASES]
    neg=[r for r in output if r['case']=='iid_random']
    noisy=[r for r in output if r['case']=='train_noise']
    drift=[r for r in output if r['case']=='concept_drift']
    return {'schema':'pl5-v3711-cross-task-results-1',
            'protocol_sha256':sha256(_canon(settings)).hexdigest(),
            'source_bank':bank.to_dict(),
            'source_truth_sha256':source_table_hashes,
            'trials':output,
            'summary':{
                'trials':len(output),'structured_tasks':len(pos),
                'positive_transfer_identified':sum(r['transfer_status']=='provisional_identified' for r in pos),
                'positive_transfer_exact_holdout':sum(r['transfer_holdout_errors']==0 for r in pos),
                'positive_baseline_identified':sum(r['baseline_status']=='provisional_identified' for r in pos),
                'negative_controls':len(neg),
                'negative_abstained':sum(r['transfer_status']!='provisional_identified' for r in neg),
                'noise_cases':len(noisy),
                'noisy_suspected':sum(r['noise_diagnosis']['status']=='single_label_suspected' for r in noisy),
                'drift_cases':len(drift),
                'drift_flagged':sum(r['drift_window'] is not None and r['drift_window']['status']=='shift_suspected' for r in drift),
                'drift_heldout_errors':sum(r['transfer_holdout_errors'] or 0 for r in drift),
                'source_training_cost_included_in_budget':False,
                'compute_matched_full_pipeline':False,
                'production_enabled':False,
                'real_lottery_advantage_established':False,
                'open_ended_mathematics_invented':False,
            }}
