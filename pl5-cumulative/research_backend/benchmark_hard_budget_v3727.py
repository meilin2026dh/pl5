"""V3.7.27 INTERNAL time-budgeted reproduction on developer-authored synthetic tasks.

Separate PUBLIC / PRIVATE files, hard worker deadlines; not an externally blinded
trial. Full startup+model fit/freeze/evidence writing is charged. Grading occurs
only when both worker statuses have been written. Offline source discovery,
issuer preparation and grading time are excluded; do not claim total science cost.
"""
from __future__ import annotations
import csv
import json
import secrets
import sys
from pathlib import Path

import numpy as np

from research_open_grammar_v3725 import prepare
from research_hard_budget_v3727 import solve, grade, ARMS, SCHEMA
from pailie5.language_evolution_v3722 import _sha

FAMILIES=('equal_gate','difference_mod3','sum_threshold','cubic_polynomial',
          'parity_gate','linear_control','independent_random','opaque_power')
SEEDS=(372701,372702)
BUDGETS_MS=(800,3000)


def target(family:str,seed:int)->np.ndarray:
    if family not in FAMILIES or seed not in SEEDS:raise ValueError('internal seeded study only')
    a,b=np.indices((10,10),dtype=np.int64)
    shift=seed%10
    xor=np.bitwise_xor(a,b)
    if family=='equal_gate': y=np.where(a==b,a*b+shift,xor+shift)
    elif family=='difference_mod3': y=np.where((a-b)%3==1,a*b+shift,xor+shift)
    elif family=='sum_threshold': y=np.where(a+b>=10,a+shift,xor+shift)
    elif family=='cubic_polynomial': y=a*a*b+b*b+shift
    elif family=='parity_gate':y=np.where((a%2)==(b%2),a*b+shift,xor+shift)
    elif family=='linear_control':y=a+b+shift
    elif family=='independent_random':y=np.random.default_rng(seed+32911).integers(0,10,(10,10))
    elif family=='opaque_power':y=(a+1)**(b%4+1)+b**3+shift
    else:raise AssertionError('unknown')
    return np.asarray(y,dtype=np.int64).reshape(100)%10


def task(family:str,seed:int):
    table=target(family,seed)
    idx=np.random.default_rng(seed*13+FAMILIES.index(family)).permutation(100)
    split=(idx[:48],idx[48:64],idx[64:])
    rows=[[[int(i//10),int(i%10),int(table[i])] for i in part] for part in split]
    return {'task_id':f'int_{FAMILIES.index(family):02d}_{seed}',
            'source_description':'INTERNAL_DEVELOPER_AUTHORED_BENCHMARK_NOT_EXTERNAL',
            'train':rows[0],'validation':rows[1],'holdout':rows[2]}


def run(out:str|Path,*,families=FAMILIES,seeds=SEEDS,budgets=BUDGETS_MS)->dict:
    out=Path(out)
    out.mkdir(parents=True,exist_ok=False)
    protocol={'schema':SCHEMA+':internal_benchmark',
       'families':list(families),'seeds':list(seeds),'budgets_ms':list(budgets),
       'model_arms':list(ARMS),'portfolio_total_budget_multiplier':2,
       'task_partitions':{'train':48,'validation':16,'holdout':36},
       'model_selection_uses_holdout':False,'internal_developer_authored':True,
       'external_blind':False,'hardware_constant_per_run':True,
       'hard_budget_scope':'subprocess startup+imports+model fit+freeze+evidence on wall-clock',
       'time_not_counted':'source discovery, prior research, issuer preparation, grading, reporting',
       'independent_external_validation':'NOT_PERFORMED',
       'lottery_predictive_advantage':'NOT_ESTABLISHED'}
    (out/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    rows=[]
    for family in families:
      for seed in seeds:
        spec=task(family,seed)
        root=out/'tasks'/spec['task_id']
        root.mkdir(parents=True,exist_ok=False)
        (root/'challenge.json').write_text(json.dumps(spec,sort_keys=True,indent=2)+'\n')
        prepare(root/'challenge.json',root/'public',root/'private')
        for budget in budgets:
            experiment=root/f'budget_{budget}'
            order=ARMS if seed%2 else tuple(reversed(ARMS))
            result=solve(root/'public'/'public_challenge.json',experiment,budget,order=order)
            grades=grade(root/'public'/'public_challenge.json',
                root/'private'/'private_challenge.json',experiment)
            manifest=json.loads((experiment/'solver_manifest.json').read_text())
            for arm in ARMS+('frozen_portfolio',):
                event=grades[arm]
                ledger=(manifest['arms'][arm] if arm in ARMS else {})
                row={'family':family,'seed':seed,'task_id':spec['task_id'],
                    'budget_ms_per_model':budget,'arm':arm,
                    'wall_ms':ledger.get('wall_ms'),
                    'worker_status':ledger.get('status','PORTFOLIO_DERIVED'),
                    'score_status':event['status'],
                    'accepted':int(event['status']=='EVALUATED'),
                    'held_errors':event['holdout_errors'],
                    'held_cells':event['holdout_cells'],
                    'exact_success':int(event['status']=='EVALUATED' and event['holdout_errors']==0),
                    'task_category':'unstructured_control' if family in ('independent_random','opaque_power') else 'structured',
                    'external_blind':False}
                rows.append(row)
    path=out/'results.csv'
    with path.open('w',newline='',encoding='utf-8') as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary={'schema':SCHEMA+':internal_benchmark_summary','protocol_sha256':_sha(protocol),
      'developer_authored':True,'external_blind':False,
      'lottery_predictive_advantage':'NOT_ESTABLISHED','runs':len(families)*len(seeds),
      'unscored_timeouts_recorded':True,
      'models':{},
      'results_sha256_without_wall_time':_sha([{k:v for k,v in r.items() if k!='wall_ms'} for r in rows])}
    for budget in budgets:
      summary['models'][str(budget)]={}
      for arm in ARMS+('frozen_portfolio',):
        r=[x for x in rows if x['budget_ms_per_model']==budget and x['arm']==arm]
        summary['models'][str(budget)][arm]={
           'total_tasks':len(r),'accepted':sum(x['accepted'] for x in r),
           'exact_success':sum(x['exact_success'] for x in r),
           'holdout_errors_accepted':sum(x['held_errors'] or 0 for x in r),
           'holdout_cells_accepted':sum(x['held_cells'] for x in r),
           'worker_timeout':sum(x['worker_status']=='TIMED_OUT' for x in r),
           'worker_failure':sum(x['worker_status']=='FAILED' for x in r),
           'null_false_accepted':sum(x['accepted'] and x['task_category']=='unstructured_control' for x in r)}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(summary['models'],ensure_ascii=False,indent=2))
    return summary


if __name__=='__main__':run(Path(sys.argv[1] if len(sys.argv)>1 else '../runs/v3727/internal_hard_budget'))
