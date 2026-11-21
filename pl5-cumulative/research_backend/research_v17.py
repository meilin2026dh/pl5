"""V1.7 supervised research CLI. No scheduler is enabled by launching this CLI."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from autoresearch.collectors import Paper
from autoresearch.supervisor_v17 import Supervisor,cycle_now,single_instance
from autoresearch.official_archive_v17 import OfficialArchive
from pailie5.capability_network import CapabilityRegistry, grow


def main(argv=None):
    p=argparse.ArgumentParser(description='PL5 V1.7 长期自动科研（仅研究，不自动投注/审批）')
    p.add_argument('--db',default='runtime/research_supervisor_v17.sqlite')
    p.add_argument('--papers-db',default='runtime/autoresearch.sqlite')
    p.add_argument('--archive',default='data/official_archive_v17')
    sub=p.add_subparsers(dest='command',required=True)
    run=sub.add_parser('once')
    mode=run.add_mutually_exclusive_group(required=True)
    mode.add_argument('--live',action='store_true',help='显式授权本轮联网检索')
    mode.add_argument('--offline-fixture',help='离线文献JSON，用于测试')
    run.add_argument('--cycle-key',default=None)
    run.add_argument('--recover-incomplete',action='store_true',help='优先尝试续跑同配置的上一个未完成周期')
    run.add_argument('--sync-official',action='store_true',help='仅从中国体彩固定官方接口获取开奖')
    run.add_argument('--pages',type=int,default=2)
    run.add_argument('--audit',action='store_true',help='仅开发集回测；须有官方历史归档')
    run.add_argument('--topics',default='sequential multiple testing,randomness testing')
    run.add_argument('--providers',default='openalex,arxiv')
    run.add_argument('--aan-db',default=None,help='V1.8可选算法能力库（研究目录）')
    run.add_argument('--aan-grow',type=int,default=0,help='每轮新提案上限0—100，默认关闭')
    sub.add_parser('status')
    sub.add_parser('verify-archive')
    args=p.parse_args(argv)
    if args.command=='verify-archive':
        report=OfficialArchive(args.archive).status()
    elif args.command=='status':
        with Supervisor(args.db,args.archive,args.papers_db) as sup:report=sup.status()
    else:
        if args.sync_official and not args.live:raise ValueError('必须明确 --live 才能联网')
        if type(args.aan_grow) is not int or not 0 <= args.aan_grow <= 100:
            raise ValueError('AAN每轮增长数量必须为0—100')
        if args.aan_grow and not args.aan_db:
            raise ValueError('启用AAN增长时必须显式指定持久化--aan-db')
        papers=None
        if args.offline_fixture:
            raw=Path(args.offline_fixture).read_bytes()
            if len(raw)>1_000_000:raise ValueError('fixture文件过大')
            values=json.loads(raw)
            if not isinstance(values,list) or len(values)>50:raise ValueError('fixture必须为不超过50篇论文的数组')
            papers=[Paper(**x) for x in values]
        topics=tuple(s.strip() for s in args.topics.split(',') if s.strip())
        providers=tuple(s.strip() for s in args.providers.split(',') if s.strip())
        mode_name='live' if args.live else 'offline'
        now_key=args.cycle_key or cycle_now()
        with single_instance(str(args.db)+'.lock'):
            with Supervisor(args.db,args.archive,args.papers_db) as sup:
                recovered=[]
                if args.recover_incomplete and not args.cycle_key:
                    past=sup.status(limit=50)['cycles']
                    for entry in reversed(past):
                        if entry['cycle_key']==now_key or entry['state']=='completed':continue
                        cfg=entry['config']
                        if (cfg.get('mode')!=mode_name or cfg.get('pages')!=args.pages or
                            cfg.get('sync_official')!=args.sync_official or cfg.get('audit')!=args.audit or
                            cfg.get('topics')!=list(topics) or cfg.get('providers')!=list(providers)):
                            continue
                        try:
                            sup.run(key=entry['cycle_key'],mode=mode_name,papers=papers,
                                sync_official=args.sync_official,pages=args.pages,
                                topics=topics,providers=providers,audit=args.audit)
                            recovered.append({'cycle_key':entry['cycle_key'],'state':'completed'})
                        except (RuntimeError,ValueError,OSError) as exc:
                            recovered.append({'cycle_key':entry['cycle_key'],'state':'still_failed',
                                              'error':(type(exc).__name__+': '+str(exc))[:200]})
                        # Bound unattended retries: one old cycle per invocation.
                        break
                report=sup.run(key=now_key,mode=mode_name,papers=papers,
                    sync_official=args.sync_official,pages=args.pages,
                    topics=topics,providers=providers,audit=args.audit)
                if args.aan_grow:
                    # Bounded, idempotent, non-executing capability proposals.
                    # Only runs after supervisor finishes this cycle successfully.
                    abilities=CapabilityRegistry(args.aan_db)
                    try:
                        additions=grow(abilities,limit=args.aan_grow)
                        growth={'created':additions,'catalog_size':len(abilities.all()),
                                'approval':'NOT_AUTOMATIC','predictive_advantage':'UNVERIFIED'}
                    finally: abilities.close()
                    if isinstance(report,dict):report={**report,'aan_growth':growth}
                if recovered:report={'current':report,'recovery':recovered}
    print(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,RuntimeError,PermissionError,FileNotFoundError,OSError,KeyError) as e:
        print('V1.7/V1.8运行失败：'+str(e),file=sys.stderr)
        sys.exit(2)
