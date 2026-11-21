"""V3.7.19 Phase II: registration, local sealing, cross-check and settlement CLI.

Do not use this CLI as an assertion of an independently timestamped pre-draw seal.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from pailie5.prospective_validation_v3719 import (
    read_evidence, reconcile, register, save_new, seal, settle,
    verify_seal, verify_settlement,
)
from pailie5.research_validation_v3719 import METHODS, Protocol


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command', required=True)
    def sources(p):
        p.add_argument('--primary',type=Path,required=True)
        p.add_argument('--witness',type=Path,required=True)
    pc=sub.add_parser('crosscheck');sources(pc);pc.add_argument('--out',type=Path,required=True)
    pr=sub.add_parser('register');sources(pr)
    pr.add_argument('--primary-url',required=True);pr.add_argument('--witness-url',required=True)
    pr.add_argument('--study-id',required=True);pr.add_argument('--target',required=True)
    pr.add_argument('--warmup',type=int,default=40);pr.add_argument('--test-size',type=int,default=10)
    pr.add_argument('--top-k',type=int,default=100);pr.add_argument('--seed',type=int,default=3719)
    pr.add_argument('--alpha',type=float,default=0.01)
    pr.add_argument('--methods',nargs='+',choices=METHODS,default=list(METHODS))
    pr.add_argument('--out',type=Path,required=True)
    ps=sub.add_parser('seal');sources(ps)
    ps.add_argument('--registration',type=Path,required=True);ps.add_argument('--out',type=Path,required=True)
    pt=sub.add_parser('settle');sources(pt)
    pt.add_argument('--registration',type=Path,required=True)
    pt.add_argument('--packet',type=Path,required=True);pt.add_argument('--out',type=Path,required=True)
    pv=sub.add_parser('verify')
    pv.add_argument('--registration',type=Path,required=True)
    pv.add_argument('--packet',type=Path,required=True)
    pv.add_argument('--settlement',type=Path)
    a=parser.parse_args(argv)
    if a.command=='crosscheck':
        out=reconcile(a.primary,a.witness)
        save_new(a.out,out)
    elif a.command=='register':
        p=Protocol(warmup=a.warmup,test_size=a.test_size,top_k=a.top_k,seed=a.seed,
                   alpha=a.alpha,methods=tuple(a.methods))
        out=register(primary=a.primary,witness=a.witness,primary_url=a.primary_url,
                     witness_url=a.witness_url,study_id=a.study_id,target_issue=a.target,protocol=p)
        save_new(a.out,out)
    else:
        r=read_evidence(a.registration,'registration')
        if a.command=='seal':
            out=seal(r,a.primary,a.witness)
            save_new(a.out,out)
        else:
            packet=read_evidence(a.packet,'seal')
            if a.command=='settle':
                out=settle(r,packet,a.primary,a.witness)
                save_new(a.out,out)
            else:
                if a.settlement:
                    verify_settlement(r,packet,read_evidence(a.settlement,'settlement'))
                else:
                    verify_seal(r,packet)
                out={'verified':'LOCAL_HASH_INTEGRITY_ONLY',
                     'independent_predraw_timestamp_verified':False,
                     'seal_sha256':packet['document_sha256']}
    print(json.dumps(out if a.command=='verify' else {
        'command':a.command,'sha256':out.get('document_sha256'),
        'output':str(a.out)},ensure_ascii=False))

if __name__=='__main__':
    main()
