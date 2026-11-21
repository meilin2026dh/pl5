"""Resume interrupted V3727 internal fixture (keeps failed/incomplete evidence).

Usage: python resume_benchmark_v3727.py [output] [max_studies]
Repeated calls perform at most max_studies. Do not release partial summary as a
pre-registered completed benchmark.
"""
from __future__ import annotations
import csv,json,sys
from pathlib import Path
from benchmark_hard_budget_v3727 import FAMILIES,SEEDS,BUDGETS_MS,task
from research_open_grammar_v3725 import prepare
from research_hard_budget_v3727 import solve,grade,ARMS,SCHEMA
from pailie5.language_evolution_v3722 import _sha


def resume(out:Path,max_studies:int=5):
    assert (out/'protocol.json').is_file(), 'benchmark protocol not initialized'
    protocol=json.loads((out/'protocol.json').read_text())
    assert protocol['families']==list(FAMILIES) and protocol['seeds']==list(SEEDS) and protocol['budgets_ms']==list(BUDGETS_MS)
    created=0
    for family in FAMILIES:
      for seed in SEEDS:
        spec=task(family,seed)
        root=out/'tasks'/spec['task_id']
        if not root.exists():
            root.mkdir(parents=True,exist_ok=False)
            (root/'challenge.json').write_text(json.dumps(spec,sort_keys=True,indent=2)+'\n')
            prepare(root/'challenge.json',root/'public',root/'private')
        for budget in BUDGETS_MS:
            experiment=root/f'budget_{budget}'
            if (experiment/'score.json').exists():continue
            if created>=max_studies:return {'new_studies':created,'complete':False}
            if experiment.exists():
                backup=root/f'budget_{budget}.interrupted'
                if backup.exists():raise FileExistsError(f'duplicate incomplete record {backup}')
                experiment.rename(backup)
            order=ARMS if seed%2 else tuple(reversed(ARMS))
            solve(root/'public'/'public_challenge.json',experiment,budget,order=order)
            grade(root/'public'/'public_challenge.json',root/'private'/'private_challenge.json',experiment)
            created+=1
    return {'new_studies':created,'complete':True}


def collect(out:Path):
    protocol=json.loads((out/'protocol.json').read_text())
    rows=[]
    for family in FAMILIES:
      for seed in SEEDS:
        spec=task(family,seed)
        root=out/'tasks'/spec['task_id']
        for budget in BUDGETS_MS:
            experiment=root/f'budget_{budget}'
            if not (experiment/'score.json').exists():
                raise RuntimeError(f'incomplete study: {experiment}')
            scores=json.loads((experiment/'score.json').read_text())['arms']
            manifest=json.loads((experiment/'solver_manifest.json').read_text())
            for arm in ARMS+('frozen_portfolio',):
                event=scores[arm]
                ledger=manifest['arms'][arm] if arm in ARMS else {}
                rows.append({'family':family,'seed':seed,'task_id':spec['task_id'],
                    'budget_ms_per_model':budget,'arm':arm,
                    'wall_ms':ledger.get('wall_ms'),
                    'worker_status':ledger.get('status','PORTFOLIO_DERIVED'),
                    'score_status':event['status'],
                    'accepted':int(event['status']=='EVALUATED'),
                    'held_errors':event['holdout_errors'],
                    'held_cells':event['holdout_cells'],
                    'exact_success':int(event['status']=='EVALUATED' and event['holdout_errors']==0),
                    'task_category':'unstructured_control' if family in ('independent_random','opaque_power') else 'structured',
                    'external_blind':False})
    with (out/'results.csv').open('w',newline='',encoding='utf-8') as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary={'schema':SCHEMA+':internal_benchmark_summary','protocol_sha256':_sha(protocol),
      'developer_authored':True,'external_blind':False,
      'lottery_predictive_advantage':'NOT_ESTABLISHED','runs':len(FAMILIES)*len(SEEDS),
      'unscored_timeouts_recorded':True,
      'models':{},
      'results_sha256_without_wall_time':_sha([{k:v for k,v in r.items() if k!='wall_ms'} for r in rows])}
    for budget in BUDGETS_MS:
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
    return summary


if __name__=='__main__':
    out=Path(sys.argv[1] if len(sys.argv)>1 else '../runs/v3727/internal_hard_budget')
    max_studies=int(sys.argv[2]) if len(sys.argv)>2 else 5
    r=resume(out,max_studies)
    print(json.dumps(r))
    if r['complete']:print(json.dumps(collect(out)['models'],ensure_ascii=False,indent=2))
