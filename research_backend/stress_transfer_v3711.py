"""Supplemental stress set; not a preregistered primary study."""
from hashlib import sha256
import json
from pathlib import Path
import numpy as np
from pailie5.transfer_study_v3711 import SOURCE_CASES
from pailie5.generated_study_v3710 import challenge_data
from pailie5.primitive_study_v377 import split_truth
from pailie5.cross_task_v3711 import (TransferConfig,certify_transfer_bank,
  fit_budgeted_transfer,evaluate_provisional,diagnose_training_noise,detect_labeled_shift)
from pailie5.structure_search_v372 import CellDataset


def main():
    out=Path(__file__).resolve().parents[1]/'docs/v3711'
    settings={'seed_positive':list(range(9701,9707)), 'seed_negative':list(range(9711,9735)),
              'seed_noise':list(range(9741,9753)), 'seed_drift':list(range(9761,9773)),
              'source_seed':9311, 'source_operators':SOURCE_CASES,'feature_budget_each_arm':8,
              'production_enabled':False, 'study_level':'supplemental stress; not confirmatory'}
    (out/'stress_protocol.json').write_text(json.dumps(settings,sort_keys=True,indent=2)+'\n')
    sources=[]
    for i,c in enumerate(SOURCE_CASES):
        seed=9311+i*131
        sources.append(split_truth(challenge_data(c,seed),seed+17))
    bank=certify_transfer_bank(tuple(sources)); cfg=TransferConfig(8)
    record=[]
    for c in SOURCE_CASES:
        for seed in settings['seed_positive']:
            truth=challenge_data(c,seed*19)
            train,held=split_truth(truth,seed*19+17)
            m=fit_budgeted_transfer(train,bank,cfg)
            errors=evaluate_provisional(m,held)['errors'] if m.status=='provisional_identified' else None
            record.append({'case':c,'seed':seed,'status':m.status,'holdout_errors':errors})
    for seed in settings['seed_negative']:
        train,_=split_truth(challenge_data('iid_random',seed*19),seed*19+17)
        m=fit_budgeted_transfer(train,bank,cfg)
        record.append({'case':'iid_random','seed':seed,'status':m.status})
    for seed in settings['seed_noise']:
        train,_=split_truth(challenge_data('xor_shift',seed*19),seed*19+17)
        rows=list(train.rows)
        idx=seed%len(rows);a,b,y=rows[idx];rows[idx]=(a,b,(y+1)%10)
        x=CellDataset(tuple(rows))
        d=diagnose_training_noise(x,bank,cfg)
        record.append({'case':'single_noise','seed':seed,'status':d['status'],
                       'located_correctly':d['suspect_pair']==(a,b) and d['suggested_digit']==y})
    for seed in settings['seed_drift']:
        target_seed=seed*19
        train,held=split_truth(challenge_data('xor_shift',target_seed),target_seed+17)
        m=fit_budgeted_transfer(train,bank,cfg)
        alt=challenge_data('abs_scaled',target_seed)
        changed=CellDataset(tuple((a,b,int(alt[a,b])) for a,b,_ in held.rows[:20]))
        monitor=detect_labeled_shift(m,changed) if m.status=='provisional_identified' else None
        record.append({'case':'concept_drift','seed':seed,'status':None if monitor is None else monitor['status']})
    summary={'total':len(record),'positive_tested':sum(x['case'] in SOURCE_CASES for x in record),
             'positive_exact':sum(x.get('holdout_errors')==0 for x in record if x['case'] in SOURCE_CASES),
             'iid_random_tested':sum(x['case']=='iid_random' for x in record),
             'iid_random_abstained':sum(x['case']=='iid_random' and x['status']!='provisional_identified' for x in record),
             'noise_tested':sum(x['case']=='single_noise' for x in record),
             'noise_located':sum(x['case']=='single_noise' and x['status']=='single_label_suspected' and x['located_correctly'] for x in record),
             'drift_tested':sum(x['case']=='concept_drift' for x in record),
             'drift_flagged':sum(x['case']=='concept_drift' and x['status']=='shift_suspected' for x in record),
             'real_lottery_advantage_established':False}
    (out/'stress_results.json').write_text(json.dumps({'protocol':settings,'summary':summary,'trials':record},sort_keys=True,indent=2)+'\n')
    print(json.dumps(summary,sort_keys=True))

if __name__=='__main__':main()
