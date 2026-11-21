"""V3.7.23 developer-authored synthetic migration exercise (NOT external blind)."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import numpy as np

from pailie5.language_evolution_v3722 import create_synthetic_task,invent,falsify,freeze,evaluate,_write_new,_sha
from pailie5.math_discovery_v3720 import read_cells
from pailie5.transfer_language_v3723 import certify_source_bank,_table,fit_target,freeze_target,evaluate_target,public_holdout_digest

SOURCES=('cubic_sum','step_sum','square_difference','parity_difference')


def execute(out:Path,seeds:int=6):
    if out.exists():raise FileExistsError('benchmark destination already exists')
    if type(seeds) is not int or not 1 <= seeds <= 12:raise ValueError('seed count out of bounds')
    out.mkdir(parents=True)
    sources=[]
    for index,family in enumerate(SOURCES):
        task=out/'sources'/f'{index:02d}_dataset'
        study=out/'sources'/f'{index:02d}_study'
        create_synthetic_task(task,family=family,seed=3722)
        invent(read_cells(task/'training.json'),study)
        falsify(study,read_cells(task/'challenge.json'))
        assert freeze(study,read_cells(task/'validation.json'))['status']=='FROZEN'
        assert evaluate(study,read_cells(task/'holdout.json'))['holdout_errors']==0
        sources.append(study)
    bank=certify_source_bank(sources,out/'frozen_source_bank.json')
    if len(bank['templates'])!=4:raise RuntimeError('expected four distinct source structures')
    rows=[]
    for cls in range(8):
        for seedindex in range(seeds):
            seed=43000+cls*100+seedindex
            rng=np.random.default_rng(seed)
            if cls<4:
                template=bank['templates'][cls]
                scale=(1,3,7,9)[(seedindex+cls)%4]
                shift=(seedindex*3+cls+2)%10
                truth=_table(template,scale,shift)
                kind=f'transferred_{SOURCES[cls]}'
            elif cls==4:
                truth=rng.integers(0,10,size=(10,10),dtype=np.int64)
                kind='iid_random_null'
            elif cls==5:
                a,b=np.indices((10,10))
                truth=(a*a*b+3*a+b*b+seedindex)%10
                kind='novel_interaction_negative'
            elif cls==6:
                a,b=np.indices((10,10))
                truth=np.where((a+b)%10 >= 3,7,2)
                kind='unseen_threshold_negative'
            else:
                truth=_table(bank['templates'][0],3,4).copy()
                # One adversarial corruption in target training, impossible to fit
                # with the source model if its mutated cell is observed.
                kind='one_corrupted_training_label'
            perm=rng.permutation(100)
            counts=(24,20,56)
            if cls==7:
                corrupted_at=int(perm[0])
                truth.flat[corrupted_at]=(truth.flat[corrupted_at]+1)%10
            splits={};start=0
            for name,count in zip(('training','validation','holdout'),counts):
                idx=perm[start:start+count];start+=count
                records=[[int(i//10),int(i%10),int(truth.flat[i])] for i in idx]
                path=out/'targets'/f'{cls:02d}_{seedindex:02d}'/f'{name}.json'
                _write_new(path,records)
                splits[name]=read_cells(path)
            study=out/'targets'/f'{cls:02d}_{seedindex:02d}'/'transfer_study'
            nonce=f'v3723-internal-evaluator-only-{seed}-research'
            committed=public_holdout_digest(splits['holdout'],nonce)
            fit=fit_target(splits['training'],out/'frozen_source_bank.json',study,candidate_budget=4,
                           holdout_commitment=committed)
            locked=freeze_target(study,out/'frozen_source_bank.json',splits['validation'])
            measured=evaluate_target(study,out/'frozen_source_bank.json',splits['holdout'],reveal_nonce=nonce)
            baseline_unknown=None
            if cls<4:
                # A source-feature-aware lookup comparator (not full prior V3722).
                from pailie5.language_evolution_v3722 import _features
                feature=_features()[bank['templates'][cls]['feature']]
                learned={}
                for a,b,y in splits['training'].rows:
                    learned[int(feature[a,b])]=int(y)
                baseline_unknown=sum(int(feature[a,b]) not in learned for a,b,y in splits['holdout'].rows)
            rows.append({'family':kind,'seed':seed,'status':measured['status'],
                         'holdout_errors':measured['errors'],'holdout_count':measured['holdout_count'],
                         'training_count':len(splits['training'].rows),'validation_count':len(splits['validation'].rows),
                         'candidates':len(fit['candidates']),
                         'distinct_after_validation':locked['distinct_surviving_tables'],
                         'templates_examined':fit['templates_examined'],
                         'source_feature_lookup_unknown':baseline_unknown})
    with (out/'results.csv').open('x',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    accepted=[r for r in rows if r['status']=='EVALUATED']
    per_family={}
    for family in sorted({r['family'] for r in rows}):
        group=[r for r in rows if r['family']==family]
        scored=[r for r in group if r['status']=='EVALUATED']
        per_family[family]={'runs':len(group),'accepted':len(scored),
                             'abstained':len(group)-len(scored),
                             'tested_cells':sum(r['holdout_count'] for r in scored),
                             'errors':sum(r['holdout_errors'] for r in scored)}
    summary={'schema':'pl5-v3723-development-benchmark-1','synthetic_task_count':len(rows),
             'source_count':len(sources),'bank_programs':len(bank['templates']),
             'accepted_count':len(accepted),'abstained_count':len(rows)-len(accepted),
             'tested_cells_on_accepts':sum(r['holdout_count'] for r in accepted),
             'errors_on_accepts':sum(r['holdout_errors'] for r in accepted),
             'per_family':per_family,'results_sha256':_sha(rows),
             'external_blind':False,'same_or_related_developer_task_families':True,
             'source_discovery_cost_not_compute_matched':True,
             'lottery_predictive_advantage':'NOT_ESTABLISHED'}
    _write_new(out/'summary.json',summary)
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--seeds',type=int,default=6)
    a=p.parse_args();print(json.dumps(execute(a.out,a.seeds),ensure_ascii=False,indent=2))
