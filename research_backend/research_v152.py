"""V1.5.2 offline ESSE seal, settlement, and verification. Never auto-approves rules."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from pailie5.forward_sculpt_v152 import SculptLedger, canon
from pailie5.algorithm_registry_v14 import Registry
from snapshot_v15 import extract

MAX_BYTES=1_500_000

def read_json(path):
    p=Path(path)
    if p.stat().st_size>MAX_BYTES:raise ValueError('输入超过1.5MB')
    return json.loads(p.read_text(encoding='utf-8'))


def main(argv=None):
    p=argparse.ArgumentParser(description='PL5 V1.5.2 开奖前雕塑封存与开奖后证据台账')
    p.add_argument('--db',default='runtime/sculpt_evidence_v152.sqlite')
    cmds=p.add_subparsers(dest='cmd',required=True)
    a=cmds.add_parser('seal');a.add_argument('--cache',required=True);a.add_argument('--request',required=True)
    a.add_argument('--target',required=True);a.add_argument('--source',required=True)
    a.add_argument('--registry-db');a.add_argument('--code-revision',default='local-uncommitted')
    b=cmds.add_parser('settle');b.add_argument('--cache',required=True);b.add_argument('--source',required=True)
    cmds.add_parser('report');cmds.add_parser('verify')
    args=p.parse_args(argv)
    with SculptLedger(args.db) as ledger:
        if args.cmd=='seal':
            reg=Registry(args.registry_db) if args.registry_db else None
            try:
                data=ledger.seal(target_issue=args.target, official_draws=extract(read_json(args.cache)),
                    source_label=args.source,bridge_request=read_json(args.request),registry=reg,
                    code_revision=args.code_revision)
            finally:
                if reg:reg.close()
        elif args.cmd=='settle':
            data=ledger.settle(official_draws=extract(read_json(args.cache)),source_label=args.source)
        elif args.cmd=='verify':data=ledger.verify()
        else:data=ledger.report()
    print(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False))
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,KeyError,PermissionError,FileNotFoundError) as ex:
        print('V1.5.2封存/核验失败：'+str(ex),file=sys.stderr);sys.exit(2)
