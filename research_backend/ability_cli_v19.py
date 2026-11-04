"""V1.9 goal-directed research CLI. No code downloads or automatic approval."""
from __future__ import annotations
import argparse
import csv
import json
from pailie5.ability_lab_v19 import GOALS,AbilityLab,Goal,plan_goal

def main(argv=None):
    p=argparse.ArgumentParser(description='PL5 V1.9 自主算法能力实验室')
    p.add_argument('--db',default='runtime/algorithm_abilities_v19.sqlite')
    s=p.add_subparsers(dest='command',required=True)
    plan=s.add_parser('plan'); plan.add_argument('--goal',choices=GOALS,required=True)
    run=s.add_parser('research');run.add_argument('--goal',choices=GOALS,required=True)
    run.add_argument('--limit',type=int,default=3)
    run.add_argument('--history',help='包含number列的官方历史CSV（可不填）')
    run.add_argument('--cycle-key',help='同配置同周期幂等')
    run.add_argument('--source',default='PL5自主科研推导（非论文复现）')
    status=s.add_parser('status');status.add_argument('--limit',type=int,default=20)
    args=p.parse_args(argv)
    if args.command=='plan':result=plan_goal(args.db,Goal(args.goal))
    elif args.command=='status':
        with AbilityLab(args.db) as lab:result=lab.latest(limit=args.limit)
    else:
        numbers=None
        if args.history:
            with open(args.history,encoding='utf-8-sig',newline='') as f:
                records=list(csv.DictReader(f))
            if not records or 'number' not in records[0]:raise ValueError('CSV需要number列')
            numbers=[r['number'] for r in records]
        with AbilityLab(args.db) as lab:
            result=lab.run(Goal(args.goal,args.limit,args.source),history=numbers,cycle_key=args.cycle_key)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0
if __name__=='__main__':raise SystemExit(main())
