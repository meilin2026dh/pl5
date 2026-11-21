"""V3.7.19 III: cautious two-province historical verification and RFC3161 entry."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from pailie5.official_dataset_v3719 import inspect_sources, audited_walk_forward
from pailie5.prospective_validation_v3719 import save_new
from pailie5.research_validation_v3719 import Protocol, METHODS
from pailie5.timestamp_evidence_v3719 import make_request, verify_response


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    for action in ('inspect','backtest'):
        p=sub.add_parser(action)
        p.add_argument('--primary',type=Path,required=True)
        p.add_argument('--witness',type=Path,required=True)
        p.add_argument('--primary-url',required=True)
        p.add_argument('--witness-url',required=True)
        p.add_argument('--min-overlap',type=int,default=1)
        p.add_argument('--consecutive',action='store_true')
        p.add_argument('--out',type=Path,required=True)
        if action=='backtest':
            p.add_argument('--warmup',type=int,default=40)
            p.add_argument('--test-size',type=int,default=10)
            p.add_argument('--top-k',type=int,default=100)
            p.add_argument('--seed',type=int,default=3719)
            p.add_argument('--methods',nargs='+',choices=METHODS,default=list(METHODS))
            p.add_argument('--allow-unverified-test-issues',action='store_true')
    req=sub.add_parser('timestamp-request')
    req.add_argument('--packet',type=Path,required=True)
    req.add_argument('--out',type=Path,required=True)
    verify=sub.add_parser('timestamp-verify')
    verify.add_argument('--packet',type=Path,required=True)
    verify.add_argument('--response',type=Path,required=True)
    verify.add_argument('--trusted-ca',type=Path,required=True)
    verify.add_argument('--out',type=Path,required=True)
    a=parser.parse_args(argv)
    if a.command=='timestamp-request':
        out=make_request(a.packet,a.out)
    elif a.command=='timestamp-verify':
        out=verify_response(a.packet,a.response,a.trusted_ca)
        save_new(a.out,out)
    else:
        opts=dict(primary=a.primary,witness=a.witness,primary_url=a.primary_url,
                  witness_url=a.witness_url,min_overlap=a.min_overlap,
                  require_consecutive=a.consecutive)
        if a.command=='backtest':
            out=audited_walk_forward(**opts,
                                    protocol=Protocol(warmup=a.warmup,test_size=a.test_size,
                                                      top_k=a.top_k,seed=a.seed,methods=tuple(a.methods)),
                                    strict_test_crosscheck=not a.allow_unverified_test_issues)
        else:
            out=inspect_sources(**opts)
        save_new(a.out,out)
    print(json.dumps({'command':a.command,'output':str(a.out),'result':(
        out.get('evidence_level') or out.get('evidence_grade') or out.get('predraw_status') or out.get('timestamp_request'))},ensure_ascii=False))


if __name__=='__main__':
    main()
