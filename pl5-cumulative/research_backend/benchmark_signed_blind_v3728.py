"""INTERNAL only: exercise V3.7.28 signed role handoff on a frozen task panel.

Developer generates and knows all target functions and holds all test labels.
Signatures are functionally verified but signer independence is NOT verified.
Never report this as external-blind mathematical discovery.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
import platform
from pathlib import Path

from benchmark_hard_budget_v3727 import task, SEEDS
from research_open_grammar_v3725 import prepare
from research_signed_blind_v3728 import keygen, issue, freeze, settle, verify_settlement, _sha, _bytes

FAMILIES=('equal_gate','cubic_polynomial','independent_random','opaque_power')
SEED=SEEDS[0]
BUDGET=5000


def run(out:str | Path, secrets_dir:str | Path, backend_root: str | Path) -> dict:
    out=Path(out); secrets_dir=Path(secrets_dir)
    out.mkdir(parents=True,exist_ok=False)
    secrets_dir.mkdir(parents=True,exist_ok=False)
    keys={}
    for role in ('issuer','solver','grader'):
        keys[role]=(secrets_dir/f'{role}.key',out/f'{role}.pub')
        keygen(*keys[role])
    rows=[]
    timing_rows=[]
    for family in FAMILIES:
        start_total=time.perf_counter_ns()
        base=out/family;base.mkdir()
        data=task(family,SEED)
        (base/'developer_known.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
        prepare(base/'developer_known.json',base/'public',base/'private')
        public=base/'public/public_challenge.json'
        private=base/'private/private_challenge.json'
        att=base/'issuer_attestation.json'
        start_issue=time.perf_counter_ns()
        issue(public,backend_root,*keys['issuer'],att,BUDGET)
        after_issue=time.perf_counter_ns()
        freeze(public,backend_root,att,keys['issuer'][1],*keys['solver'],base/'solver')
        after_solver=time.perf_counter_ns()
        settle(public,private,backend_root,att,keys['issuer'][1],keys['solver'][1],*keys['grader'],base/'solver')
        after_grader=time.perf_counter_ns()
        v=verify_settlement(public,backend_root,att,keys['issuer'][1],keys['solver'][1],keys['grader'][1],base/'solver')
        after_verify=time.perf_counter_ns()
        timing_rows.append({'task_family':family,'challenge_prepare_wall_ms':round((start_issue-start_total)/1e6,3),
            'issuer_sign_wall_ms':round((after_issue-start_issue)/1e6,3),
            'solver_freeze_wall_ms':round((after_solver-after_issue)/1e6,3),
            'grader_settle_wall_ms':round((after_grader-after_solver)/1e6,3),
            'auditor_verify_wall_ms':round((after_verify-after_grader)/1e6,3),
            'measured_local_pipeline_wall_ms':round((after_verify-start_total)/1e6,3),
            'external_issuer_verified':False})
        assert v['signed_evidence_verified'] and not v['actual_external_blind_study_verified']
        score=json.loads((base/'solver/score.json').read_text())
        source=json.loads((base/'solver/solver_manifest.json').read_text())
        for arm in ('v3725_ring','v3726_gate','frozen_portfolio'):
            event=score['arms'][arm];worker=source['arms'].get(arm,{})
            rows.append({'task_family':family,'task_id':data['task_id'],'arm':arm,
                'worker_status':worker.get('status','DERIVED'),
                'score_status':event['status'],
                'holdout_errors':event['holdout_errors'],
                'holdout_cells':event['holdout_cells'],
                'wall_ms':worker.get('wall_ms'),
                'exact_accepted':int(event['status']=='EVALUATED' and event['holdout_errors']==0),
                'is_developer_authored':True,'external_blind_verified':False})
    with (out/'results.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (out/'pipeline_timings.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(timing_rows[0]));w.writeheader();w.writerows(timing_rows)
    summary={'schema':'pl5-v3728-internal-role-handoff-pilot-1',
        'families':list(FAMILIES),'seed':SEED,'budget_ms_per_arm':BUDGET,
        'total_mathematical_tasks':len(FAMILIES),'total_method_rows':len(rows),
        'source_code_independent_of_labels':False,
        'developer_knows_all_answers':True,'signer_identity_externally_verified':False,
        'external_blind_verified':False,'trusted_timestamp_verified':False,
        'public_keys_bundled':True,'private_keys_not_bundled':True,
        'environment':{'python':sys.version.split()[0],'platform':platform.system(),
          'machine':platform.machine()},
        'measured_pipeline_wall_ms_total':round(sum(x['measured_local_pipeline_wall_ms'] for x in timing_rows),3),
        'unmeasured_costs':['developer research','source algorithm search and design',
                             'environment provisioning','third-party recruitment and oversight',
                             'energy','trusted timestamp service'],
        'raw_records_digest_sha256':_sha(_bytes([{k:v for k,v in row.items() if k!='wall_ms'} for row in rows])),
        'methods':{},'lottery_predictive_advantage':'NOT_ESTABLISHED'}
    for arm in ('v3725_ring','v3726_gate','frozen_portfolio'):
        rs=[x for x in rows if x['arm']==arm]
        summary['methods'][arm]={'total_tasks':len(rs),
          'accepted_exact':sum(x['exact_accepted'] for x in rs),
          'accepted_with_errors':sum(x['score_status']=='EVALUATED' and x['holdout_errors']>0 for x in rs),
          'rejected_or_timeout':sum(x['score_status']!='EVALUATED' for x in rs),
          'holdout_cells_accepted':sum(x['holdout_cells'] for x in rs)}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    return summary


if __name__=='__main__':
    print(json.dumps(run(sys.argv[1],sys.argv[2],sys.argv[3]),ensure_ascii=False,indent=2))
