"""V2.2 autonomous bounded code authoring; sandbox evaluation is opt-in."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path
from autoresearch.collaboration_v22 import V22ResearchLab, FAMILIES


def main(argv=None):
    p=argparse.ArgumentParser(description='PL5 V2.2多智能体算法工程与自动反例实验')
    p.add_argument('--db',default='runtime/autoresearch.sqlite')
    sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('generate'); a.add_argument('--project',required=True);a.add_argument('--family',choices=FAMILIES)
    a=sub.add_parser('auto-generate');a.add_argument('--limit',type=int,default=3)
    a=sub.add_parser('evaluate');a.add_argument('--project',required=True)
    a.add_argument('--allow-docker',action='store_true');a.add_argument('--complete-domain',action='store_true')
    a=sub.add_parser('status');a.add_argument('--project',required=True)
    a=p.parse_args(argv)
    path=Path(a.db);path.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(path) as db:
        lab=V22ResearchLab(db)
        if a.command=='generate':result=lab.generate(a.project,family=a.family)
        elif a.command=='auto-generate':result=lab.auto_generate(maximum=a.limit)
        elif a.command=='evaluate':result=lab.evaluate(a.project,allow_docker=a.allow_docker,complete_domain=a.complete_domain)
        else:result=lab.status(a.project)
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,PermissionError,KeyError,RuntimeError,OSError,sqlite3.DatabaseError) as e:
        print('V2.2科研实验：'+str(e),file=sys.stderr);sys.exit(2)
