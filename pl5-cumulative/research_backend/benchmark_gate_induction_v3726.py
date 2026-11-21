"""PL5 V3.7.26 paired CPU-budget curves, on INTERNAL developer-authored tasks.

The 10x10 task generator is public in this repo. This is not an external blind
benchmark. Same task splits and machine, balanced rotating arm order. CPU-time
cutoffs are post-hoc *eligibility gates*, not deterministic runtime interrupts.
"""
from __future__ import annotations
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from pailie5.structure_search_v372 import CellDataset
from pailie5.language_evolution_v3722 import _sha
from pailie5.grammar_discovery_v3724 import fit as f24, freeze as fr24,evaluate as e24,commit_holdout as c24
from pailie5.open_grammar_v3725 import fit as f25,freeze as fr25,evaluate as e25,commit_holdout as c25
from pailie5.gate_induction_v3726 import fit as f26,freeze as fr26,evaluate as e26,commit_holdout as c26,program_table as table26,VERSION
from pailie5.open_grammar_v3725 import program_table as table25

FAMILIES=('diagonal_gate','mod3_difference_gate','sum_threshold_gate','less_gate',
          'linear_control','cubic_control','parity_control','random_null',
          'training_corruption','opaque_power')
SEEDS=(372603,372604,372605,372606,372607)
ARMS=('v3724_expanded','v3725_ring','v3726_gate')
REPORTED_ARMS=ARMS+('frozen_portfolio',)


def portfolio_choice(frozen25:dict,frozen26:dict)->str|None:
    """Choose only from pre-holdout frozen outputs; fail closed on conflict."""
    a=frozen25['status']=='FROZEN'
    b=frozen26['status']=='FROZEN'
    if a and not b:return 'v3725_ring'
    if b and not a:return 'v3726_gate'
    if not a and not b:return None
    if np.array_equal(table25(frozen25['selected']['spec']),
                      table26(frozen26['selected']['spec'])):
        return 'v3725_ring'
    return None
BUDGETS_MS=(25,50,100,250,500,1000)


def setter(family:str,seed:int)->np.ndarray:
    if family not in FAMILIES or seed not in SEEDS:raise ValueError('unsupported developer fixture')
    a,b=np.indices((10,10),dtype=np.int64)
    s=seed%10
    xor=np.bitwise_xor(a,b)
    p=a*b
    if family=='diagonal_gate': y=np.where(a==b,p+s,xor+s)
    elif family=='mod3_difference_gate':y=np.where((a-b)%3==1,p+s,xor+s)
    elif family=='sum_threshold_gate':y=np.where(a+b>=10,a+s,xor+s)
    elif family=='less_gate':y=np.where(a<b,p+s,xor+s)
    elif family=='linear_control':y=a+b+s
    elif family=='cubic_control':y=a*a*b+b*b+s
    elif family=='parity_control':y=np.where((a%2)==(b%2),p+s,xor+s)
    elif family=='random_null':y=np.random.default_rng(seed+712).integers(0,10,(10,10))
    elif family=='training_corruption':y=np.where(a==b,p+s,xor+s)
    elif family=='opaque_power':y=np.fromfunction(lambda a,b:((a+1)**(b%4+1)+b**3+s)%10,(10,10),dtype=int)
    else:raise ValueError('unknown task')
    return np.asarray(y,dtype=np.int64).reshape(100)%10


def _dataset(family:str,seed:int):
    y=setter(family,seed).copy()
    idx=np.random.default_rng(seed+61000).permutation(100)
    if family=='training_corruption':y[idx[0]]=(y[idx[0]]+1)%10
    return tuple(CellDataset(tuple((int(k//10),int(k%10),int(y[k])) for k in coords))
                 for coords in (idx[:48],idx[48:64],idx[64:]))


def run(out:Path)->dict:
    out.mkdir(parents=True,exist_ok=False)
    protocol={'schema':VERSION+':internal_paired_cpu_protocol',
      'families':FAMILIES,'seeds':SEEDS,'arms':REPORTED_ARMS,
      'splits':{'train':48,'validation':16,'holdout':36},
      'cpu_time_budgets_ms':BUDGETS_MS,
      'comparison_policy':'report all untruncated fits; within each CPU cutoff success only if fit+freeze CPU <= budget and exact holdout score; unbudgeted acceptance shown separately',
      'execution_order':'rotate independent arm order by seed to reduce fixed warm-cache ordering',
      'portfolio':'pre-holdout frozen-choice only: choose sole frozen arm, or identical full input-table predictions; abstain on disagreement. CPU charge equals ring+gate costs',
      'developer_authored':True,'external_blind_verified':False,
      'same_machine_paired':True,'total_search_cost_equalized':False,
      'cpu_time_comparable_metric':'process_time_ns for fit+freeze; excludes task generation, evidence serialization after freeze, source discovery, energy and external setup',
      'source_discovery_cost_included':False,
      'lottery_predictive_advantage':'NOT_ESTABLISHED'}
    (out/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    protocol_hash=_sha(protocol)
    funcs={'v3724_expanded':(f24,fr24,e24,c24),'v3725_ring':(f25,fr25,e25,c25),
           'v3726_gate':(f26,fr26,e26,c26)}
    rows=[]
    for family in FAMILIES:
      for seed in SEEDS:
        train,val,hold=_dataset(family,seed)
        nonce=hashlib.sha256(f'{VERSION}|{seed}|{family}|INTERNAL-DEMO-ONLY'.encode()).hexdigest()
        order=ARMS[seed%3:]+ARMS[:seed%3]
        artifacts={}
        # BOTH models are fitted and frozen BEFORE the first holdout is scored.
        for arm in order:
            f,fr,ev,com=funcs[arm]
            folder=out/'studies'/family/str(seed)/arm
            kw={'holdout_digest':com(hold,nonce),'protocol_sha256':protocol_hash}
            if arm=='v3724_expanded':kw['arm']='expanded'
            start=time.process_time_ns()
            trained=f(train,folder,**kw)
            frozen=fr(folder,val)
            cpu_ns=time.process_time_ns()-start
            artifacts[arm]=(folder,trained,frozen,cpu_ns)
        selection=portfolio_choice(artifacts['v3725_ring'][2],artifacts['v3726_gate'][2])
        task_rows={}
        for arm in ARMS:
            _,_,ev,_=funcs[arm]
            folder,trained,frozen,cpu_ns=artifacts[arm]
            result=ev(folder,hold,nonce=nonce)
            result_row={'family':family,'seed':seed,'arm':arm,
              'status':frozen['status'],'test_errors':result['test_errors'],
              'test_cells':result['test_count'],
              'cpu_fit_freeze_ms':round(cpu_ns/1e6,4),
              'candidate_evaluations':trained['candidate_evaluations'],
              'holdout_digest_verified':result['commitment_verified'],
              'task_class':'null' if family in ('random_null','training_corruption','opaque_power') else 'structured',
              'selected_source':arm}
            rows.append(result_row)
            task_rows[arm]=result_row
        if selection:
            source=task_rows[selection]
            errors=source['test_errors'];status=source['status']
        else:errors=None;status='ABSTAIN'
        rows.append({'family':family,'seed':seed,'arm':'frozen_portfolio',
          'status':status,'test_errors':errors,'test_cells':len(hold.rows),
          'cpu_fit_freeze_ms':round(sum(artifacts[a][3] for a in ('v3725_ring','v3726_gate'))/1e6,4),
          'candidate_evaluations':task_rows['v3725_ring']['candidate_evaluations']+task_rows['v3726_gate']['candidate_evaluations'],
          'holdout_digest_verified':True,
          'task_class':'null' if family in ('random_null','training_corruption','opaque_power') else 'structured',
          'selected_source':selection or 'ABSTAIN'})
    with (out/'results.csv').open('w',newline='',encoding='utf-8') as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary={'schema':VERSION+':summary','protocol_sha256':protocol_hash,
       'external_blind_verified':False,'independent_issuer':False,'source_discovery_cost_included':False,
       'lottery_predictive_advantage':'NOT_ESTABLISHED','results_sha256_excluding_timing':_sha([
        {k:v for k,v in r.items() if k!='cpu_fit_freeze_ms'} for r in rows]),'arms':{},'families':{}}
    for arm in REPORTED_ARMS:
        rr=[r for r in rows if r['arm']==arm]
        summary['arms'][arm]={'tasks':len(rr),
          'accepted':sum(r['status']=='FROZEN' for r in rr),
          'abstained':sum(r['status']=='ABSTAIN' for r in rr),
          'accepted_heldout_errors':sum(r['test_errors'] or 0 for r in rr),
          'accepted_heldout_cells':sum(r['test_cells'] for r in rr if r['test_errors'] is not None),
          'exact_success_all_tasks':sum(r['status']=='FROZEN' and r['test_errors']==0 for r in rr),
          'null_false_acceptances':sum(r['task_class']=='null' and r['status']=='FROZEN' for r in rr),
          'cpu_fit_freeze_total_ms':round(sum(r['cpu_fit_freeze_ms'] for r in rr),2),
          'cpu_fit_freeze_median_ms':float(round(np.median([r['cpu_fit_freeze_ms'] for r in rr]),3)),
          'success_by_cpu_cutoff_ms':{str(b):sum(r['cpu_fit_freeze_ms']<=b and
              r['status']=='FROZEN' and r['test_errors']==0 for r in rr) for b in BUDGETS_MS}}
    for family in FAMILIES:
        summary['families'][family]={arm:{'accepted':sum(r['status']=='FROZEN' for r in rows if r['arm']==arm and r['family']==family),
            'exact_success':sum(r['status']=='FROZEN' and r['test_errors']==0 for r in rows if r['arm']==arm and r['family']==family)} for arm in REPORTED_ARMS}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary['arms'],indent=2,ensure_ascii=False))
    return summary

if __name__=='__main__':run(Path(sys.argv[1] if len(sys.argv)>1 else '../runs/v3726/internal_paired'))
