"""PL5 V3.7.27: fail-closed, wall-clock hard-budget blind challenge runner.

ISSUER (on independent machine): create a challenge using
research_open_grammar_v3725.py prepare; retain PRIVATE and publish only PUBLIC.
SOLVER: python research_hard_budget_v3727.py solve --public ... --out ... --budget-ms 2000
GRADER (after solver freeze): python research_hard_budget_v3727.py grade --public ... --private ... --out ...

This is a protocol implementation, NOT independent test provenance or a secure
sandbox. The caller must supply physical/process access separation and signed,
externally timestamped challenge/solver receipts for an external-blind claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from research_open_grammar_v3725 import _public, _read, _ds
from pailie5.language_evolution_v3722 import _sha, _signed, _read_checked, _write_new, _coordinate_overlap
from pailie5.open_grammar_v3725 import (
    VERSION as V25, fit as fit25, freeze as freeze25,
    evaluate as evaluate25, commit_holdout as commitment25,
)
from pailie5.gate_induction_v3726 import (
    VERSION as V26, fit as fit26, freeze as freeze26,
    evaluate as evaluate26,
)
from benchmark_gate_induction_v3726 import portfolio_choice

SCHEMA='pl5-v3727-hard-wall-budget-1'
ARMS=('v3725_ring','v3726_gate')
WORKER_RECEIPT=SCHEMA+':worker_receipt'
RUN_MANIFEST=SCHEMA+':run_manifest'
GRADE_MANIFEST=SCHEMA+':grade_manifest'
MIN_MS=100
MAX_MS=60_000


def _validated_budget(ms:int):
    if type(ms) is not int or not MIN_MS <= ms <= MAX_MS:
        raise ValueError(f'hard wall budget must be integer {MIN_MS}..{MAX_MS} ms')
    return ms


def _worker(public_file: str|Path, out: str|Path, arm: str):
    if arm not in ARMS: raise ValueError('unknown algorithm arm')
    pub=_public(public_file)
    train,val=_ds(pub['train']),_ds(pub['validation'])
    if _coordinate_overlap(train.pairs,val.pairs):raise ValueError('overlapping train and validation coordinates')
    root=Path(out)
    if root.exists():raise FileExistsError('immutable study output already exists')
    if arm=='v3725_ring':
        fit=fit25(train,root,holdout_digest=pub['holdout_commitment'],protocol_sha256=pub['protocol_sha256'])
        freeze=freeze25(root,val)
    else:
        # V26 uses a different commitment namespace. The grader must first
        # independently verify the V25 issuer commitment before scoring either.
        fit=fit26(train,root,protocol_sha256=pub['protocol_sha256'])
        freeze=freeze26(root,val)
    rec=_signed({'schema':WORKER_RECEIPT, 'arm':arm,
        'public_sha256':_sha(pub), 'fit_sha256':_sha({k:v for k,v in fit.items() if k!='integrity_sha256'}),
        'freeze_sha256':_sha({k:v for k,v in freeze.items() if k!='integrity_sha256'}),
        'status':freeze['status'], 'candidate_evaluations':fit['candidate_evaluations'],
        'holdout_labels_seen':False, 'evidence_grade':'INTERNAL_OR_UNVERIFIED_ISSUER',
        'lottery_predictive_advantage':'NOT_ESTABLISHED'})
    _write_new(root/'worker_receipt.json',rec)
    return {'arm':arm,'status':freeze['status']}


def _summarize_arm(root:Path,arm:str,public_hash:str)->dict:
    version=V25 if arm=='v3725_ring' else V26
    receipt=_read_checked(root/'worker_receipt.json',WORKER_RECEIPT)
    fit=_read_checked(root/'fit.json',version+':fit')
    freeze=_read_checked(root/'freeze.json',version+':freeze')
    if (receipt['arm']!=arm or receipt['public_sha256']!=public_hash or
          receipt['fit_sha256']!=_sha(fit) or receipt['freeze_sha256']!=_sha(freeze) or
          receipt['status']!=freeze['status'] or fit['protocol_sha256'] is None):
        raise ValueError('worker evidence changed or mismatched')
    return {'status':'COMPLETED','frozen_status':freeze['status'],
            'receipt_sha256':_sha(receipt),'candidate_evaluations':fit['candidate_evaluations']}


def solve(public_file: str|Path,out:str|Path,budget_ms:int,*,order:tuple[str,...]=ARMS)->dict:
    """One *fresh* OS process per arm, enforced by subprocess wall deadline.

    Startup, imports, fit, validation freeze and writing evidence all count.
    Timeout kills worker, and no prediction from partial evidence can be scored.
    """
    _validated_budget(budget_ms)
    if set(order)!=set(ARMS) or len(order)!=len(ARMS):raise ValueError('exactly two known arms')
    public_file=Path(public_file).resolve()
    pub=_public(public_file)
    if _coordinate_overlap(_ds(pub['train']).pairs,_ds(pub['validation']).pairs):
        raise ValueError('public train/validation overlap')
    root=Path(out)
    root.mkdir(parents=True,exist_ok=False)
    protocol=_signed({'schema':SCHEMA+':protocol','budget_ms_per_arm':budget_ms,
        'arms':list(order),'public_sha256':_sha(pub),'task_id':pub['task_id'],
        'clock':'time.perf_counter_ns; subprocess.run(timeout=budget_s)',
        'budget_scope':'worker process startup+imports+fit+freeze+evidence serialization',
        'budget_excludes':'challenge issuer generation, benchmark development, offline discovery, grader',
        'timeout_policy':'kill worker, mark TIMED_OUT, never grade partial evidence',
        'ensemble_budget_multiplier':2,
        'integrity_not_authenticity':True,'independent_external_issuer_verified':False,
        'lottery_predictive_advantage':'NOT_ESTABLISHED'})
    _write_new(root/'protocol.json',protocol)
    rows={}
    for arm in order:
        start=time.perf_counter_ns()
        cmd=[sys.executable,str(Path(__file__).resolve()),'worker',
             '--public',str(public_file),'--arm',arm,'--out',str((root/arm).resolve())]
        try:
            completed=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                     timeout=budget_ms/1000,check=False,env={**os.environ,'PYTHONNOUSERSITE':'1'})
            elapsed_ms=(time.perf_counter_ns()-start)/1e6
            if completed.returncode!=0:
                row={'status':'FAILED','reason':'nonzero_worker_exit',
                     'exit_code':completed.returncode,'stderr_tail':completed.stderr[-1000:]}
            elif elapsed_ms>budget_ms:
                row={'status':'TIMED_OUT','reason':'wall_budget_exceeded'}
            else:
                try: row=_summarize_arm(root/arm,_arm(arm),_sha(pub))
                except (OSError,ValueError,KeyError,TypeError) as exc:
                    row={'status':'FAILED','reason':'invalid_worker_receipt','error':type(exc).__name__}
        except subprocess.TimeoutExpired:
            elapsed_ms=(time.perf_counter_ns()-start)/1e6
            row={'status':'TIMED_OUT','reason':'subprocess_hard_timeout'}
        row['wall_ms']=round(elapsed_ms,3)
        row['allowed_budget_ms']=budget_ms
        rows[arm]=row
    manifest=_signed({'schema':RUN_MANIFEST,'protocol_sha256':_sha({k:v for k,v in protocol.items() if k!='integrity_sha256'}),
        'public_sha256':_sha(pub),'task_id':pub['task_id'],'arms':rows,
        'all_completed_models_frozen_before_holdout_grading':True,
        'private_labels_received_by_solver':False,
        'independent_external_blind_verified':False,
        'lottery_predictive_advantage':'NOT_ESTABLISHED'})
    _write_new(root/'solver_manifest.json',manifest)
    return {'task_id':pub['task_id'],'budget_ms_per_arm':budget_ms,
            'arms':{x:{'status':rows[x]['status'],'frozen_status':rows[x].get('frozen_status')} for x in ARMS},
            'external_blind_verified':False}


def _arm(arm):
    if arm not in ARMS:raise ValueError('unsupported arm')
    return arm


def grade(public_file:str|Path,private_file:str|Path,out:str|Path)->dict:
    """Issue the holdout only after verifying both arms were already frozen.

    The score file uses O_EXCL, so resubmitting changed results fails closed.
    """
    root=Path(out)
    if (root/'score.json').exists():raise FileExistsError('already graded')
    pub=_public(public_file)
    priv=_read(private_file)
    if (set(priv)!={'schema','task_id','holdout','nonce','public_sha256'} or
          priv['schema']!=V25+':private' or priv['task_id']!=pub['task_id'] or
          priv['public_sha256']!=_sha(pub)):
        raise ValueError('issuer public/private mismatch')
    holdout=_ds(priv['holdout'])
    if _coordinate_overlap(_ds(pub['train']).pairs,_ds(pub['validation']).pairs,holdout.pairs):
        raise ValueError('holdout overlaps model-visible labels')
    if commitment25(holdout,priv['nonce'])!=pub['holdout_commitment']:
        raise ValueError('issuer commitment differs from holdout')
    protocol=_read_checked(root/'protocol.json',SCHEMA+':protocol')
    manifest=_read_checked(root/'solver_manifest.json',RUN_MANIFEST)
    if (manifest['task_id']!=pub['task_id'] or manifest['public_sha256']!=_sha(pub)
        or protocol['public_sha256']!=_sha(pub) or
        manifest['protocol_sha256']!=_sha(protocol) or
        set(manifest['arms'])!=set(ARMS)):
        raise ValueError('solver receipt and issuer mismatch')
    graded={}
    # Preflight ALL runnable arms before revealing any labels to evaluation.
    for arm,row in manifest['arms'].items():
        if row['status']=='COMPLETED':
            ref=_summarize_arm(root/arm,arm,_sha(pub))
            for key in ('status','receipt_sha256','frozen_status','candidate_evaluations'):
                if ref[key]!=row[key]:raise ValueError('frozen solver state modified')
            fit=_read_checked(root/arm/'fit.json',(V25 if arm=='v3725_ring' else V26)+':fit')
            if fit['protocol_sha256']!=pub['protocol_sha256']:
                raise ValueError('solver trained against different protocol')
        elif row['status'] not in ('TIMED_OUT','FAILED'):
            raise ValueError('invalid solver arm state')
    frozen={}
    for arm,row in manifest['arms'].items():
        if row['status']!='COMPLETED':
            graded[arm]={'status':row['status'],'holdout_errors':None,'holdout_cells':0}
            continue
        if arm=='v3725_ring':res=evaluate25(root/arm,holdout,nonce=priv['nonce'])
        else:res=evaluate26(root/arm,holdout)
        frozen[arm]=_read_checked(root/arm/'freeze.json',(V25 if arm=='v3725_ring' else V26)+':freeze')
        graded[arm]={'status':res['status'],'holdout_errors':res['test_errors'],
                     'holdout_cells':res['test_count'] if res['status']=='EVALUATED' else 0}
    # Portfolio requires BOTH component arms on time; charge sum of wall budgets.
    selection=None
    if len(frozen)==len(ARMS):selection=portfolio_choice(frozen['v3725_ring'],frozen['v3726_gate'])
    graded['frozen_portfolio']={'status':'EVALUATED' if selection else 'ABSTAIN',
       'selected_source':selection,
       'holdout_errors':graded[selection]['holdout_errors'] if selection else None,
       'holdout_cells':graded[selection]['holdout_cells'] if selection else 0,
       'budget_ms_total':2*protocol['budget_ms_per_arm']}
    output=_signed({'schema':GRADE_MANIFEST,'public_sha256':_sha(pub),
      'solver_manifest_sha256':_sha(manifest),'holdout_commitment_verified':True,
      'task_id':pub['task_id'],'arms':graded,'external_issuer_verified':False,
      'external_blind_verified':False,'lottery_predictive_advantage':'NOT_ESTABLISHED'})
    _write_new(root/'score.json',output)
    return graded


def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    sub=ap.add_subparsers(dest='action',required=True)
    a=sub.add_parser('worker');a.add_argument('--public',required=True);a.add_argument('--out',required=True);a.add_argument('--arm',choices=ARMS,required=True)
    a=sub.add_parser('solve');a.add_argument('--public',required=True);a.add_argument('--out',required=True);a.add_argument('--budget-ms',required=True,type=int)
    a=sub.add_parser('grade');a.add_argument('--public',required=True);a.add_argument('--private',required=True);a.add_argument('--out',required=True)
    args=ap.parse_args()
    if args.action=='worker':ret=_worker(args.public,args.out,args.arm)
    elif args.action=='solve':ret=solve(args.public,args.out,args.budget_ms)
    else:ret=grade(args.public,args.private,args.out)
    print(json.dumps(ret,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
