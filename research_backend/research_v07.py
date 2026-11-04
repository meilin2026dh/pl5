"""PL5 V0.7 methods, novelty competition and prospective evidence CLI."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
from autoresearch.store import LabStore
from autoresearch.registry_v06 import ResearchRegistry
from autoresearch.novelty_v07 import invent_diverse,assess_novelty
from autoresearch.paper_protocol_v07 import build_research_protocol
from autoresearch.verification import full_audit,rank_research_approved
from autoresearch.forward_v07 import freeze_checked,forward_report
from autoresearch.prospective import settle_from_history
from pailie5.data import load_csv


def jprint(x):print(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False))


def load_history(path,source):
    if not source or not(source.startswith('official:') or source.startswith('https://')):
        raise ValueError('请填写官方公告核验来源；本程序只能记录来源声明，无法自动证明真伪')
    raw=Path(path).read_bytes();draws=load_csv(raw)
    if any('补零' in w for w in draws.warnings):raise ValueError('缺少前导零的号码必须人工核实后再导入')
    if not draws.frame['period'].str.fullmatch('[0-9]{4,16}').all():
        raise ValueError('前向试验要求全为4至16位数字期号')
    return draws,hashlib.sha256(raw).hexdigest()


def main(argv=None):
    p=argparse.ArgumentParser(description='PL5 V0.7自主科研验证，研究用途，不保证中奖')
    p.add_argument('--db',default='runtime/autoresearch.sqlite')
    sp=p.add_subparsers(dest='command',required=True)
    sub=sp.add_parser('paper-plan');sub.add_argument('--key',required=True)
    sub=sp.add_parser('discover');sub.add_argument('--key',required=True)
    sub.add_argument('--limit',type=int,default=4)
    sub=sp.add_parser('discover-all');sub.add_argument('--max-documents',type=int,default=2)
    sub.add_argument('--per-document',type=int,default=2)
    sub=sp.add_parser('audit');sub.add_argument('--fingerprint',required=True)
    sub.add_argument('--csv',required=True);sub.add_argument('--official-source',required=True)
    sub.add_argument('--eval-size',type=int,default=80);sub.add_argument('--null-sequences',type=int,default=2)
    sub.add_argument('--k',type=int,default=100)
    sub=sp.add_parser('freeze');sub.add_argument('--csv',required=True)
    sub.add_argument('--official-source',required=True)
    sub.add_argument('--target-period',required=True);sub.add_argument('--k',type=int,default=100)
    sub=sp.add_parser('settle');sub.add_argument('--csv',required=True)
    sub.add_argument('--official-source',required=True)
    sub=sp.add_parser('forward-report')
    args=p.parse_args(argv)
    with LabStore(args.db) as store:
        reg=ResearchRegistry(store.db)
        if args.command=='paper-plan':
            out=build_research_protocol(reg.get_document(args.key))
        elif args.command=='discover':
            existing=[reg.get_algorithm(x['fingerprint']) for x in reg.algorithms(80)]
            new,report=invent_diverse(reg.get_document(args.key)['text_excerpt'],args.key,
                                      limit=args.limit,already=existing)
            accepted=[reg.add_algorithm(x,args.key) for x in new]
            out={'new_algorithms':accepted,'novelty_report':report,'auto_activated':False}
        elif args.command=='discover-all':
            if not 1<=args.max_documents<=5 or not 1<=args.per_document<=4:
                raise ValueError('定时科研每次最多5篇、每篇最多4条')
            out={'documents':[],'auto_activated':False}
            for doc in reg.documents(args.max_documents):
                existing=[reg.get_algorithm(x['fingerprint']) for x in reg.algorithms(80)]
                new,report=invent_diverse(reg.get_document(doc['doc_key'])['text_excerpt'],doc['doc_key'],
                             limit=args.per_document,already=existing,search_budget=24)
                out['documents'].append({'key':doc['doc_key'],
                   'new':[reg.add_algorithm(x,doc['doc_key']) for x in new],
                   'screened':report['evaluated'],'rejected':report['rejected']})
        elif args.command=='audit':
            draws,digest=load_history(args.csv,args.official_source)
            algorithm=reg.get_algorithm(args.fingerprint)
            previous=[reg.get_algorithm(x['fingerprint']) for x in reg.algorithms(80)
                      if x['fingerprint']!=args.fingerprint]
            novelty=assess_novelty(algorithm,previous)
            report=full_audit(algorithm,draws.frame['number'].tolist(),k=args.k,
                              eval_size=args.eval_size,null_sequences=args.null_sequences,
                              attempts=reg.audit_attempts())
            out={'research_heuristic':novelty,'verification':report,
                 'audit_record':reg.add_audit(args.fingerprint,digest,report),
                 'predictive_edge_proven':False}
        elif args.command=='freeze':
            draws,digest=load_history(args.csv,args.official_source)
            entries=[x for x in reg.algorithms(300) if x['state']=='research_approved']
            if not entries:raise ValueError('尚无人工审批通过的研究算法，不能用未审核模型生成前向候选')
            if len(entries)>24:raise ValueError('已审批研究公式超过24个，请先缩减本轮算法集')
            algorithms=[reg.get_algorithm(x['fingerprint']) for x in entries]
            chosen,evidence=rank_research_approved(algorithms,draws.frame['number'].tolist(),k=args.k)
            algo_hash=hashlib.sha256(json.dumps(sorted(a.fingerprint() for a in algorithms)).encode()).hexdigest()
            out={'freeze':freeze_checked(store.db,draws_frame=draws.frame,
                 target_period=args.target_period,candidates=chosen,history_sha256=digest,
                 algorithm_sha256=algo_hash,official_source=args.official_source),
                 'ranking_evidence':evidence,'note':'不可在开奖号码公布后注册未来期号；本地时间戳无法独立证明时序'}
        elif args.command=='settle':
            draws,digest=load_history(args.csv,args.official_source)
            outcomes=dict(zip(draws.frame['period'].astype(str),draws.frame['number']))
            out=settle_from_history(store.db,period_to_number=outcomes,
                                    data_sha256=digest,source_description=args.official_source)
            out['forward_summary']=forward_report(store.db)
        elif args.command=='forward-report':out=forward_report(store.db)
        else:raise ValueError('未知命令')
    jprint(out)
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,KeyError,RuntimeError,PermissionError,FileNotFoundError) as exc:
        print('V0.7科研任务失败：'+str(exc),file=sys.stderr);sys.exit(2)
