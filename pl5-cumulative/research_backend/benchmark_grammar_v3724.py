"""Preregistered internal synthetic pilot. Setters and solver exchange bounded JSON;
this is not an independent third-party blind study. Test data is accessed only
when BOTH model arms have frozen, but is included in the archive for audit.
"""
from __future__ import annotations
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
import numpy as np
from pailie5.grammar_discovery_v3724 import (
    VERSION, MAX_EVALS, FEATURES, COMBINERS, fit,freeze,evaluate,commit_holdout,
)
from pailie5.structure_search_v372 import CellDataset
from pailie5.language_evolution_v3722 import _sha

FAMILIES=('product_plus_a','xor_plus_b','gcd_plus_absdiff','xor_plus_absdiff',
          'unary_control','random_null','cubic_interaction_negative','piecewise_negative')
SEEDS=(372401,372402,372403,372404,372405,372406)
SPLITS=(('train',48),('validation',16),('holdout',36))


def family_table(family:str,seed:int)->np.ndarray:
    if family not in FAMILIES or seed not in SEEDS:raise ValueError('unregistered task')
    a,b=np.indices((10,10),dtype=np.int64)
    offset=seed%10
    if family=='product_plus_a':return (a*b+a+offset)%10
    if family=='xor_plus_b':return (np.bitwise_xor(a,b)+b+offset)%10
    if family=='gcd_plus_absdiff':return (np.gcd(a,b)+abs(a-b)+offset)%10
    if family=='xor_plus_absdiff':return (np.bitwise_xor(a,b)+abs(a-b)+offset)%10
    if family=='unary_control':return (a+b+offset)%10
    if family=='random_null':return np.random.default_rng(seed).integers(0,10,size=(10,10))
    if family=='cubic_interaction_negative':return (a*a*b+b*b+offset)%10
    return np.where(a<b,(a*b+offset)%10,(np.bitwise_xor(a,b)+offset)%10)


def setter(family:str,seed:int,folder:Path):
    folder.mkdir(parents=True,exist_ok=False)
    t=family_table(family,seed)
    permutation=np.random.default_rng(seed+90000).permutation(100)
    parts={}
    pos=0
    for name,n in SPLITS:
        indices=permutation[pos:pos+n];pos+=n
        ds=CellDataset(tuple((int(i//10),int(i%10),int(t.flat[i])) for i in indices))
        parts[name]=ds
        (folder/(name+'.json')).write_text(json.dumps(ds.rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return parts


def run(output:Path):
    output.mkdir(parents=True,exist_ok=False)
    protocol={'schema':VERSION+':protocol','cases':list(FAMILIES),'seeds':list(SEEDS),
      'splits':dict(SPLITS),'arms':['baseline','expanded'],
      'feature_order':list(FEATURES),'binary_operations':list(COMBINERS),
      'evaluations_per_arm':MAX_EVALS,'training_selected':True,
      'holdout_selection_prohibited':True,'abstention_allowed':True,
      'null_baselines_expected_to_abstain':True,'evaluation_grade':'INTERNAL_SYNTHETIC',
      'source_discovery_and_runtime_not_matched':True,
      'hypothesis':'two-feature extension improves coverage over unary polynomial grammar at equal table evaluations',
      'lottery_predictive_advantage':'NOT_ESTABLISHED'}
    # This protocol is frozen on disk before any study is initiated.
    (output/'protocol.json').write_text(json.dumps(protocol,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    protocol_sha=_sha(protocol)
    rows=[]
    for family in FAMILIES:
        for seed in SEEDS:
            task=output/'setter'/family/str(seed)
            parts=setter(family,seed,task)
            # Withheld nonce is needed only for final evaluation; hash is public.
            nonce=hashlib.sha256(f'{VERSION}|{family}|{seed}|not-a-third-party-secret'.encode()).hexdigest()
            digest=commit_holdout(parts['holdout'],nonce)
            frozen={}
            stages={}
            for arm in ('baseline','expanded'):
                study=output/'studies'/family/str(seed)/arm
                f=fit(parts['train'],study,arm=arm,holdout_digest=digest,protocol_sha256=protocol_sha)
                z=freeze(study,parts['validation'])
                frozen[arm]=z
                stages[arm]=f
            for arm in ('baseline','expanded'):
                study=output/'studies'/family/str(seed)/arm
                ev=evaluate(study,parts['holdout'],nonce=nonce)
                rows.append({'family':family,'seed':seed,'arm':arm,'train_error_best':stages[arm]['best_training_errors'],
                  'stage1_train_error':stages[arm]['base_stage_errors'],
                  'expansion_triggered':stages[arm]['grammar_expansion_triggered'],
                  'exact_fit_tables':len(stages[arm]['exact_fit_programs']),
                  'candidate_evaluations':stages[arm]['candidate_evaluations'],
                  'fit_wall_ms':round(stages[arm]['wall_ns_fit']/1e6,3),
                  'freeze_status':frozen[arm]['status'],'holdout_error':ev['test_errors'],
                  'holdout_count':ev['test_count'],'commitment_verified':ev['commitment_verified']})
    with (output/'results.csv').open('w',newline='',encoding='utf-8') as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    result={}
    for arm in ('baseline','expanded'):
        subset=[r for r in rows if r['arm']==arm]
        result[arm]={'tasks':len(subset),'accepted':sum(r['freeze_status']=='FROZEN' for r in subset),
          'abstained':sum(r['freeze_status']=='ABSTAIN' for r in subset),
          'accepted_test_errors':sum(r['holdout_error'] or 0 for r in subset),
          'accepted_test_cells':sum(r['holdout_count'] for r in subset if r['holdout_error'] is not None),
          'total_candidate_evaluations':sum(r['candidate_evaluations'] for r in subset),
          'measured_fit_wall_ms':round(sum(r['fit_wall_ms'] for r in subset),1)}
    for family in FAMILIES:
        result[family]={arm:{'accepts':sum(r['family']==family and r['arm']==arm and r['freeze_status']=='FROZEN' for r in rows),
          'test_errors':sum(r['holdout_error'] or 0 for r in rows if r['family']==family and r['arm']==arm)}
          for arm in ('baseline','expanded')}
    stable_rows=[{k:v for k,v in row.items() if k!='fit_wall_ms'} for row in rows]
    logical_digest=_sha(stable_rows)
    result.update({'schema':VERSION+':summary','logical_results_sha256':logical_digest,'protocol_sha256':protocol_sha,'external_blind':False,
       'source_discovery_cost_not_included':True,'whole_program_runtime_equalized':False,
       'results_sha256':hashlib.sha256((output/'results.csv').read_bytes()).hexdigest(),
       'lottery_predictive_advantage':'NOT_ESTABLISHED'})
    (output/'summary.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    run(Path(sys.argv[1] if len(sys.argv)>1 else 'runs/v3724/benchmark'))
