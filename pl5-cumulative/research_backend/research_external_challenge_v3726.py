"""PL5 V3.7.26 issuer/solver/grader INTERFACE (not an external audit itself).

Issuer on independent infrastructure:
  python research_external_challenge_v3726.py prepare --challenge task.json --public PUBLIC --private PRIVATE
Solver receives ONLY PUBLIC/public_challenge.json (no private directory):
  python research_external_challenge_v3726.py solve --public PUBLIC/public_challenge.json --out SOLVER
Issuer/grader AFTER algorithm freeze:
  python research_external_challenge_v3726.py grade --public PUBLIC/public_challenge.json --private PRIVATE/private_challenge.json --out SOLVER

True blind evidence requires independent challenge provenance, separated access,
prior signed/timestamped registration and third-party custody. No result here is
claimed externally verified merely because this interface was executed locally.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from research_open_grammar_v3725 import prepare, _public, _read, _ds, _write_new
from pailie5.language_evolution_v3722 import _sha, _signed, _read_checked, _coordinate_overlap
from pailie5.open_grammar_v3725 import (
    VERSION as V25, fit as f25, freeze as fr25, evaluate as e25,
    commit_holdout as c25)
from pailie5.gate_induction_v3726 import (
    VERSION, fit as f26, freeze as fr26, evaluate as e26)

MANIFEST_SCHEMA=VERSION+':solver_manifest'


def solve(public_file:str|Path,out:str|Path)->dict:
    doc=_public(public_file)
    train,validation=_ds(doc['train']),_ds(doc['validation'])
    if _coordinate_overlap(train.pairs,validation.pairs):raise ValueError('train/validation overlap')
    root=Path(out)
    if root.exists():raise FileExistsError('solver output exists; results cannot be overwritten')
    folders={'v3725_ring':root/'v3725_ring','v3726_gate':root/'v3726_gate'}
    record={}
    for arm in folders:
        folder=folders[arm]
        if arm=='v3725_ring':
            fitted=f25(train,folder,holdout_digest=doc['holdout_commitment'],protocol_sha256=doc['protocol_sha256'])
            frozen=fr25(folder,validation)
        else:
            # V3726 commitment version differs. The issuer's existing V3725
            # public/private digest is verified by the independent GRADER below.
            fitted=f26(train,folder,protocol_sha256=doc['protocol_sha256'])
            frozen=fr26(folder,validation)
        record[arm]={'fit_sha256':_sha({k:v for k,v in fitted.items() if k!='integrity_sha256'}),
                      'freeze_sha256':_sha({k:v for k,v in frozen.items() if k!='integrity_sha256'}),
                      'status':frozen['status'],
                      'candidate_evaluations':fitted['candidate_evaluations']}
    manifest=_signed({'schema':MANIFEST_SCHEMA,'issuer_public_sha256':_sha(doc),
                      'task_id':doc['task_id'],'arms':record,'private_answers_seen':False,
                      'lottery_predictive_advantage':'NOT_ESTABLISHED',
                      'issuer_external_identity_verified':False})
    _write_new(root/'solver_manifest.json',manifest)
    return {'task_id':doc['task_id'],'methods':{k:r['status'] for k,r in record.items()},
            'manifest_sha256':_sha(manifest),'independent_external_blind':False}


def grade(public_file:str|Path,private_file:str|Path,out:str|Path)->dict:
    pub=_public(public_file)
    priv=_read(private_file)
    if set(priv)!={'schema','task_id','holdout','nonce','public_sha256'} or priv['schema']!=V25+':private':
        raise ValueError('unregistered issuer private data')
    if priv['public_sha256']!=_sha(pub) or priv['task_id']!=pub['task_id']:
        raise ValueError('public/private linkage mismatch')
    holdout=_ds(priv['holdout'])
    if _coordinate_overlap(_ds(pub['train']).pairs,_ds(pub['validation']).pairs,holdout.pairs):
        raise ValueError('holdout coordinate overlap')
    if c25(holdout,priv['nonce'])!=pub['holdout_commitment']:
        raise ValueError('issuer holdout commitment mismatch')
    root=Path(out)
    manifest=_read_checked(root/'solver_manifest.json',MANIFEST_SCHEMA)
    if manifest['issuer_public_sha256']!=_sha(pub) or manifest['task_id']!=pub['task_id']:
        raise ValueError('solver/issuer mismatch')
    for arm,version in [('v3725_ring',V25),('v3726_gate',VERSION)]:
        info=manifest['arms'][arm]
        fit=_read_checked(root/arm/'fit.json',version+':fit')
        freeze=_read_checked(root/arm/'freeze.json',version+':freeze')
        if info['fit_sha256']!=_sha(fit) or info['freeze_sha256']!=_sha(freeze):
            raise ValueError('solver state altered after freeze')
        if fit['protocol_sha256']!=pub['protocol_sha256']:
            raise ValueError('solver protocol changed')
    # Do not start grading if either existing result would block a second run.
    if any((root/arm/'evaluation.json').exists() for arm in ('v3725_ring','v3726_gate')):
        raise FileExistsError('already graded; no rescoring')
    old=e25(root/'v3725_ring',holdout,nonce=priv['nonce'])
    new=e26(root/'v3726_gate',holdout)
    return {'task_id':pub['task_id'],
            'issuer_holdout_commitment_verified':True,
            'methods':{
                'v3725_ring':{'status':old['status'],'errors':old['test_errors'],'cells':old['test_count']},
                'v3726_gate':{'status':new['status'],'errors':new['test_errors'],'cells':new['test_count']}},
            'private_holdout_previously_withheld_requires_external_attestation':True,
            'independent_external_blind_verified':False,
            'lottery_predictive_advantage':'NOT_ESTABLISHED'}


def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    cmd=parser.add_subparsers(dest='action',required=True)
    a=cmd.add_parser('prepare');a.add_argument('--challenge',required=True);a.add_argument('--public',required=True);a.add_argument('--private',required=True)
    a=cmd.add_parser('solve');a.add_argument('--public',required=True);a.add_argument('--out',required=True)
    a=cmd.add_parser('grade');a.add_argument('--public',required=True);a.add_argument('--private',required=True);a.add_argument('--out',required=True)
    args=parser.parse_args()
    if args.action=='prepare':ret=prepare(args.challenge,args.public,args.private)
    elif args.action=='solve':ret=solve(args.public,args.out)
    else:ret=grade(args.public,args.private,args.out)
    print(json.dumps(ret,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
