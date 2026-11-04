"""Local read/experimentation CLI for V1.8 AAN (does not approve algorithms)."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
from pailie5.capability_network import CapabilityRegistry, bootstrap, grow, run_pipeline


def main() -> int:
    p=argparse.ArgumentParser(description='PL5 V1.8算法能力网络')
    p.add_argument('--db',default='runtime/algorithm_abilities_v18.sqlite')
    s=p.add_subparsers(dest='cmd',required=True)
    s.add_parser('bootstrap')
    new=s.add_parser('grow');new.add_argument('--limit',type=int,default=10)
    s.add_parser('graph')
    gap=s.add_parser('gaps');gap.add_argument('--kind',choices=['metric','pattern','anti_filter','merge_masks'],default='anti_filter')
    run=s.add_parser('run');run.add_argument('--target',required=True);run.add_argument('--history',required=True)
    args=p.parse_args()
    db=CapabilityRegistry(args.db)
    try:
        if args.cmd=='bootstrap':data={'created':bootstrap(db),'total':len(db.all())}
        elif args.cmd=='grow':data={'created':grow(db,limit=args.limit),'total':len(db.all())}
        elif args.cmd=='graph':data=db.graph()
        elif args.cmd=='gaps':data=db.gaps(args.kind)
        else:
            with open(args.history,encoding='utf-8-sig',newline='') as f:
                rows=list(csv.DictReader(f))
            if not rows or not all('number' in r for r in rows):
                raise ValueError('CSV至少包含number列')
            data=run_pipeline(db,args.target,[r['number'] for r in rows])
        print(json.dumps(data,ensure_ascii=False,indent=2))
        return 0
    finally:db.close()

if __name__=='__main__': raise SystemExit(main())
