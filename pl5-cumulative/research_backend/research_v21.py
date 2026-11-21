"""PL5 V2.1 cooperating research-role orchestration; no autonomous paid calls."""
from __future__ import annotations
import argparse,csv,json,sqlite3,sys
from pathlib import Path
from autoresearch.council_v21 import ResearchCouncil


def main(argv=None):
    p=argparse.ArgumentParser(description='PL5 V2.1多角色科研委员会（研究用途）')
    p.add_argument('--db',default='runtime/autoresearch.sqlite')
    sub=p.add_subparsers(dest='command',required=True)
    x=sub.add_parser('create'); x.add_argument('--blueprint',required=True); x.add_argument('--goal',required=True)
    x.add_argument('--budget',type=int,default=100);x.add_argument('--periods',type=int,default=8)
    x=sub.add_parser('plan');x.add_argument('--project',required=True)
    x=sub.add_parser('auto-plan');x.add_argument('--limit',type=int,default=3)
    x=sub.add_parser('submit-code'); x.add_argument('--project',required=True)
    x.add_argument('--role',choices=['primary','reference'],required=True);x.add_argument('--file',required=True)
    x=sub.add_parser('red-team'); x.add_argument('--project',required=True)
    x=sub.add_parser('audit');x.add_argument('--project',required=True);x.add_argument('--csv',required=True)
    x.add_argument('--allow-docker',action='store_true')
    x=sub.add_parser('decision');x.add_argument('--project',required=True)
    x=sub.add_parser('state');x.add_argument('--project',required=True)
    x=sub.add_parser('status'); x.add_argument('--limit',type=int,default=20)
    a=p.parse_args(argv)
    path=Path(a.db);path.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(path) as db:
        council=ResearchCouncil(db)
        if a.command=='create':
            result=council.create(a.blueprint,goal=a.goal,budget=a.budget,periods=a.periods)
        elif a.command=='plan':result=council.plan(a.project)
        elif a.command=='auto-plan':result=council.auto_plan(maximum=a.limit)
        elif a.command=='submit-code':
            result=council.submit_code(a.project,role=a.role,source=Path(a.file).read_text(encoding='utf8'))
        elif a.command=='red-team':result=council.red_team(a.project)
        elif a.command=='audit':
            if not a.allow_docker:raise PermissionError('必须显式授权--allow-docker')
            with open(a.csv,encoding='utf-8-sig',newline='') as f:
                records=list(csv.DictReader(f))
            if (not records or any(not r.get('issue') or not r.get('date') or not r.get('number') for r in records)
                or len({r['issue'] for r in records})!=len(records)
                or len({r['date'] for r in records})!=len(records)):
                raise ValueError('开奖CSV缺少issue/date/number或期号日期冲突')
            records.sort(key=lambda r:r['date'])
            result=council.audit(a.project,[r['number'] for r in records],allow_docker=True)
        elif a.command=='decision':result=council.decision(a.project)
        elif a.command=='state':result=council.state(a.project)
        else:result=council.status(limit=a.limit)
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (PermissionError,ValueError,KeyError,RuntimeError,OSError,sqlite3.DatabaseError) as e:
        print('V2.1科研委员会：'+str(e),file=sys.stderr);sys.exit(2)
