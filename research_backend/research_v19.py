"""V1.9 one-shot research orchestration: V1.7 discovery then V1.9 capability research."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from research_v17 import main as legacy_main
from pailie5.ability_lab_v19 import Goal,GOALS,AbilityLab

def main(argv=None):
    p=argparse.ArgumentParser(description='PL5 V1.9自动科研联动执行')
    p.add_argument('--lab-db',required=True)
    p.add_argument('--goal',choices=GOALS,default='cross_position')
    p.add_argument('--limit',type=int,default=3)
    p.add_argument('--cycle-key',required=True)
    p.add_argument('--history',help='人工CSV历史只做探索性回测；来源需另行核验')
    p.add_argument('--verified-archive',action='store_true',help='仅通过V1.7官方归档验证后开展历史回放')
    args,forward=p.parse_known_args(argv)
    # First, preserve existing supervisor's archival, recovery, and research behavior.
    if not forward:raise ValueError('需要附带旧版科研任务参数（once --live 等）')
    status=legacy_main(forward)
    if status!=0:return status
    numbers=None
    if args.history and args.verified_archive:raise ValueError('不能混合人工CSV与官方归档')
    if args.verified_archive:
        from autoresearch.official_archive_v17 import OfficialArchive
        archive='data/official_archive_v17'
        if '--archive' in forward:
            i=forward.index('--archive')
            if i+1>=len(forward):raise ValueError('归档路径参数缺失')
            archive=forward[i+1]
        records,metadata=OfficialArchive(archive).load()
        numbers=[r['number'] for r in records] if records else None
    if args.history:
        import csv
        with open(args.history,encoding='utf-8-sig',newline='') as f:
            records=list(csv.DictReader(f))
        if not records or 'number' not in records[0]:raise ValueError('CSV缺少number列')
        numbers=[x['number'] for x in records]
    with AbilityLab(args.lab_db) as lab:
        result=lab.run(Goal(args.goal,args.limit),history=numbers,cycle_key=args.cycle_key)
    print(json.dumps({'v19_ability_lab':{**result,'verified_official_archive':bool(args.verified_archive and numbers),
        'archive_checked':bool(args.verified_archive),
        'history_count':len(numbers or [])}},ensure_ascii=False,indent=2))
    return 0
if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,RuntimeError,OSError,KeyError) as e:
        print('V1.9科研流程失败: '+str(e),file=sys.stderr);sys.exit(2)
