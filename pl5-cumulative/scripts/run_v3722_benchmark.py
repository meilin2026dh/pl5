"""Deterministic developer-authored tasks; no genuine third-party blind challenge."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path

from pailie5.language_evolution_v3722 import (
    create_synthetic_task, invent, falsify, freeze, evaluate, TASK_FAMILIES,
)
from pailie5.math_discovery_v3720 import read_cells


def run(root: Path, seeds: tuple[int,...]=(3722,3723,3724,3725,3726)):
    if root.exists():
        raise FileExistsError('refuse to overwrite prior experiment')
    root.mkdir(parents=True)
    rows=[]
    for family in TASK_FAMILIES:
        for seed in seeds:
            dest=root/family/str(seed)
            data=dest/'setter'; study=dest/'study'
            create_synthetic_task(data, family=family, seed=seed)
            training=read_cells(data/'training.json')
            proposal=invent(training,study)
            attack=falsify(study,read_cells(data/'challenge.json'))
            selection=freeze(study,read_cells(data/'validation.json'))
            result=evaluate(study,read_cells(data/'holdout.json'))
            rows.append({'family':family,'seed':seed,
                         'proposals':len(proposal['candidates']),
                         'rejected_by_falsifier':sum(not item['passes'] for item in attack['results']),
                         'status':result['status'],
                         'selected_feature':selection['selected_feature'] or '',
                         'holdout_errors':result['holdout_errors'] if result['holdout_errors'] is not None else '',
                         'holdout_unknown':result['holdout_unknown'] if result['holdout_unknown'] is not None else '',
                         'holdout_count':result['holdout_count']})
    with (root/'results.csv').open('x',encoding='utf-8',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    groups={}
    for family in TASK_FAMILIES:
        subset=[r for r in rows if r['family']==family]
        groups[family]={'trials':len(subset),'evaluated':sum(r['status']=='EVALUATED' for r in subset),
                        'abstained':sum(r['status']=='ABSTAIN' for r in subset),
                        'tested_cells':sum(int(r['holdout_count']) for r in subset if r['status']=='EVALUATED'),
                        'tested_errors':sum(int(r['holdout_errors']) for r in subset if r['status']=='EVALUATED')}
    summary={'schema':'pl5-v3722-developer-benchmark-1','study':'V3.7.22',
             'seed_list':list(seeds),'evaluation_is_not_external_blind':True,
             'matched_compute_budget_with_prior_version':False,
             'tasks':groups,'predictive_advantage':'NOT_ESTABLISHED'}
    (root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+'\n','utf-8')
    print(json.dumps(summary,indent=2,ensure_ascii=False))
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--seeds',type=int,nargs='+',default=[3722,3723,3724,3725,3726])
    a=p.parse_args();run(a.out,tuple(a.seeds))
