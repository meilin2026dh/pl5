"""Two-party file protocol for PL5 V3.7.25 research trials.

USAGE (run preparation on the *challenge provider's* computer):
  python research_open_grammar_v3725.py prepare --challenge challenge.json --public PUBLIC --private PRIVATE
The solver only receives PUBLIC/public_challenge.json:
  python research_open_grammar_v3725.py solve --public PUBLIC/public_challenge.json --out SOLVER
The grader alone receives PRIVATE/private_challenge.json:
  python research_open_grammar_v3725.py grade --public PUBLIC/public_challenge.json --private PRIVATE/private_challenge.json --out SOLVER

An internal single-machine rehearsal is NOT an independent external blind test.
"""
from __future__ import annotations
import argparse
import json
import os
import secrets
from pathlib import Path

from pailie5.structure_search_v372 import CellDataset
from pailie5.language_evolution_v3722 import _sha, _coordinate_overlap
from pailie5.open_grammar_v3725 import VERSION, fit,freeze,evaluate,commit_holdout
from pailie5.grammar_discovery_v3724 import fit as baseline_fit, freeze as baseline_freeze, evaluate as baseline_evaluate, commit_holdout as baseline_commit


def _read(path:str|Path)->dict:
    obj=json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(obj,dict):raise ValueError('JSON object required')
    return obj


def _ds(rows)->CellDataset:
    if not isinstance(rows,list):raise ValueError('observations must be an array')
    return CellDataset(tuple(tuple(r) if isinstance(r,list) else r for r in rows))


def _write_new(path:Path,body:dict,secret:bool=False):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600 if secret else 0o644)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(body,f,ensure_ascii=False,sort_keys=True,indent=2)
            f.write('\n')
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def prepare(challenge:str|Path,public_dir:str|Path,private_dir:str|Path)->dict:
    doc=_read(challenge)
    if set(doc)!={'task_id','train','validation','holdout','source_description'}:
        raise ValueError('unsupported challenge file: explicit task_id/source_description/splits required')
    identifier=doc['task_id']
    if not isinstance(identifier,str) or not 1<=len(identifier)<=128 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.' for c in identifier):
        raise ValueError('invalid task id')
    source=doc['source_description']
    if not isinstance(source,str) or len(source)>1024:raise ValueError('invalid provenance')
    ds={k:_ds(doc[k]) for k in ('train','validation','holdout')}
    if _coordinate_overlap(*(x.pairs for x in ds.values())):raise ValueError('partition coordinate overlap')
    nonce=secrets.token_hex(32)
    public={'schema':VERSION+':challenge','task_id':identifier,
            'train':[list(x) for x in ds['train'].rows],
            'validation':[list(x) for x in ds['validation'].rows],
            'holdout_commitment':commit_holdout(ds['holdout'],nonce),
            'source_description_self_reported':source,
            'issuer_identity_externally_verified':False,
            'evaluation_grade':'UNVERIFIED_ISSUER_UNTIL_EXTERNAL_AUDIT',
            'version':VERSION}
    public['protocol_sha256']=_sha({k:v for k,v in public.items() if k!='protocol_sha256'})
    private={'schema':VERSION+':private','task_id':identifier,
            'holdout':[list(x) for x in ds['holdout'].rows],
            'nonce':nonce,'public_sha256':_sha(public)}
    pub=Path(public_dir)/'public_challenge.json'
    priv=Path(private_dir)/'private_challenge.json'
    if pub.resolve()==priv.resolve():raise ValueError('public and private must be separate files')
    if pub.exists() or priv.exists():raise FileExistsError('challenge already exists')
    _write_new(pub,public)
    _write_new(priv,private,secret=True)
    return {'task_id':identifier,'public_file':str(pub),'private_file':str(priv),
            'holdout_sha256_commitment':public['holdout_commitment'],
            'external_blind_verified':False}


def _public(path:str|Path)->dict:
    doc=_read(path)
    if doc.get('schema')!=VERSION+':challenge':raise ValueError('unregistered challenge schema')
    if _sha({k:v for k,v in doc.items() if k!='protocol_sha256'})!=doc.get('protocol_sha256'):
        raise ValueError('public challenge modified')
    if not isinstance(doc.get('holdout_commitment'),str) or len(doc['holdout_commitment'])!=64:
        raise ValueError('missing holdout digest')
    return doc


def solve(public_file:str|Path,out:str|Path)->dict:
    doc=_public(public_file)
    train,validation=_ds(doc['train']),_ds(doc['validation'])
    if _coordinate_overlap(train.pairs,validation.pairs):raise ValueError('training/validation overlap')
    folder=Path(out)
    if folder.exists():raise FileExistsError('solver result directory already exists')
    # Each file uses O_EXCL; any interruption preserves partial evidence rather than overwriting.
    root=folder/'open_grammar'
    f=fit(train,root,holdout_digest=doc['holdout_commitment'],protocol_sha256=doc['protocol_sha256'])
    fr=freeze(root,validation)
    return {'task_id':doc['task_id'],'candidate_evaluations':f['candidate_evaluations'],
            'fit_wall_ms':round(f['fit_wall_ns']/1e6,3),'status':fr['status'],
            'selected':fr['selected'],'external_blind_verified':False}


def grade(public_file:str|Path,private_file:str|Path,out:str|Path)->dict:
    pub=_public(public_file)
    priv=_read(private_file)
    if set(priv)!={'schema','task_id','holdout','nonce','public_sha256'} or priv['schema']!=VERSION+':private':
        raise ValueError('invalid private challenge structure')
    if priv['public_sha256']!=_sha(pub) or pub['task_id']!=priv['task_id']:
        raise ValueError('private/public mismatch')
    holdout=_ds(priv['holdout'])
    if commit_holdout(holdout,priv['nonce'])!=pub['holdout_commitment']:
        raise ValueError('holdout bytes do not match public commitment')
    ev=evaluate(Path(out)/'open_grammar',holdout,nonce=priv['nonce'])
    return {'task_id':pub['task_id'],'status':ev['status'],'errors':ev['test_errors'],
            'test_cells':ev['test_count'],'digest_verified':ev['commitment_verified'],
            'issuer_externally_verified':False}


def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    sub=ap.add_subparsers(dest='action',required=True)
    a=sub.add_parser('prepare');a.add_argument('--challenge',required=True);a.add_argument('--public',required=True);a.add_argument('--private',required=True)
    a=sub.add_parser('solve');a.add_argument('--public',required=True);a.add_argument('--out',required=True)
    a=sub.add_parser('grade');a.add_argument('--public',required=True);a.add_argument('--private',required=True);a.add_argument('--out',required=True)
    v=ap.parse_args()
    if v.action=='prepare':ret=prepare(v.challenge,v.public,v.private)
    elif v.action=='solve':ret=solve(v.public,v.out)
    else:ret=grade(v.public,v.private,v.out)
    print(json.dumps(ret,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
