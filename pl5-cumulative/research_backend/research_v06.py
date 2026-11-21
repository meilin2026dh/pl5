"""PL5 V0.6 autonomous research CLI. Existing V0.5 research_cli.py stays available."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
from autoresearch.store import LabStore
from autoresearch.registry_v06 import ResearchRegistry
from autoresearch.fulltext import read_local_document,fetch_arxiv_pdf
from autoresearch.formulas import invent_from_text,emit_review_code
from autoresearch.verification import full_audit
from autoresearch.workflow_v06 import run_for_document
from pailie5.data import load_csv


def history_from_official(csv_path,source):
    if not source or not(source.startswith('official:') or source.startswith('https://')):
        raise ValueError('请声明核验的官方数据来源 --official-source')
    raw=Path(csv_path).read_bytes();data=load_csv(raw)
    if any('补零' in w for w in data.warnings):
        raise ValueError('CSV存在缺失前导零的疑点，需先核实')
    nums=data.frame['number'].tolist()
    if len(nums)<56:raise ValueError('实验要求至少56期有效历史数据')
    return nums,hashlib.sha256(raw).hexdigest()


def dump(obj):print(json.dumps(obj,ensure_ascii=False,indent=2))


def main(argv=None):
    a=argparse.ArgumentParser(description='PL5 V0.6自主研究引擎，所有实验为研究用途，绝不自动投注')
    a.add_argument('--db',default='runtime/autoresearch.sqlite')
    sub=a.add_subparsers(dest='command',required=True)
    p=sub.add_parser('import');p.add_argument('--file',required=True);p.add_argument('--key',required=True);p.add_argument('--title',required=True)
    p=sub.add_parser('fetch-arxiv');p.add_argument('--arxiv-id',required=True)
    p=sub.add_parser('ingest-leads');p.add_argument('--max-documents',type=int,default=5)
    p=sub.add_parser('invent');p.add_argument('--key',required=True);p.add_argument('--limit',type=int,default=6);p.add_argument('--paid-llm',action='store_true');p.add_argument('--model')
    p=sub.add_parser('experiment');p.add_argument('--fingerprint',required=True)
    p.add_argument('--csv',required=True);p.add_argument('--official-source',required=True)
    p.add_argument('--k',type=int,default=100);p.add_argument('--eval-size',type=int,default=80)
    p.add_argument('--null-sequences',type=int,default=4)
    p=sub.add_parser('cycle');p.add_argument('--max-documents',type=int,default=3)
    p.add_argument('--algorithms-per-document',type=int,default=2)
    p.add_argument('--csv');p.add_argument('--official-source')
    p.add_argument('--eval-size',type=int,default=60);p.add_argument('--null-sequences',type=int,default=2)
    p.add_argument('--k',type=int,default=100)
    p=sub.add_parser('rank-approved');p.add_argument('--csv',required=True);p.add_argument('--official-source',required=True)
    p.add_argument('--k',type=int,default=100);p.add_argument('--output',default='research_reports/v06_approved_top100.csv')
    p.add_argument('--target-period',help='可选：未开奖的期号，申请本地预注册')
    p=sub.add_parser('approve-research');p.add_argument('--fingerprint',required=True)
    p.add_argument('--audit-id',type=int,required=True);p.add_argument('--reviewer',required=True)
    p.add_argument('--consent',required=True)
    p=sub.add_parser('status');p.add_argument('--limit',type=int,default=15)
    p=sub.add_parser('review-code');p.add_argument('--fingerprint',required=True)
    args=a.parse_args(argv)
    with LabStore(args.db) as store:
        reg=ResearchRegistry(store.db)
        if args.command=='import':
            text,digest=read_local_document(args.file)
            out=reg.add_document(args.key,args.title,text,kind='local')
            out['original_file_sha256']=digest
        elif args.command=='fetch-arxiv':
            text,digest,url=fetch_arxiv_pdf(args.arxiv_id)
            out=reg.add_document('arxiv:'+args.arxiv_id,'arXiv '+args.arxiv_id,text,url=url,kind='arxiv_pdf')
            out['original_pdf_sha256']=digest
        elif args.command=='ingest-leads':
            if not 1<=args.max_documents<=25:raise ValueError('每轮最多25份文献')
            out={'ingested':[]}
            for r in store.papers(limit=args.max_documents,min_score=2):
                if len(r['abstract'].strip())<30:continue
                result=reg.add_document('lead:'+r['key'],r['title'] or r['key'],r['abstract'][:70000],
                                        url=r['url'],kind='abstract')
                out['ingested'].append(result)
        elif args.command=='invent':
            doc=reg.get_document(args.key)
            if args.paid_llm:
                from autoresearch.llm_v06 import propose_with_model
                algos=propose_with_model(doc['text_excerpt'],args.key,model=args.model)
            else:
                algos=invent_from_text(doc['text_excerpt'],args.key,limit=args.limit)
            out={'proposed':len(algos),'algorithms':[],'paid_model_used':args.paid_llm}
            for algo in algos:
                inserted=reg.add_algorithm(algo,args.key)
                out['algorithms'].append({**inserted,'specification':algo.to_dict()})
        elif args.command=='experiment':
            nums,digest=history_from_official(args.csv,args.official_source)
            algo=reg.get_algorithm(args.fingerprint)
            report=full_audit(algo,nums,k=args.k,eval_size=args.eval_size,
                              null_sequences=args.null_sequences,attempts=reg.audit_attempts())
            record=reg.add_audit(args.fingerprint,digest,report)
            out={'audit':record,'results':report,'source_declared':args.official_source}
        elif args.command=='cycle':
            if not 1<=args.max_documents<=12 or not 1<=args.algorithms_per_document<=12:
                raise ValueError('每轮研究工作量超出限额')
            if args.csv and not args.official_source:raise ValueError('请提供官方数据核验来源')
            nums,digest=history_from_official(args.csv,args.official_source) if args.csv else (None,None)
            result=[]
            docs=reg.documents(limit=args.max_documents)
            if not docs:
                for p in store.papers(limit=args.max_documents,min_score=2):
                    if len(p['abstract'].strip())>=30:
                        reg.add_document('lead:'+p['key'],p['title'] or p['key'],p['abstract'],
                                         url=p['url'],kind='abstract')
                docs=reg.documents(limit=args.max_documents)
            for doc in docs:
                result.append(run_for_document(reg,doc['doc_key'],nums,data_sha256=digest,
                              limit=args.algorithms_per_document,eval_size=args.eval_size,
                              null_sequences=args.null_sequences,k=args.k))
            out={'documents_processed':len(result),'cycles':result,
                 'note':'自动完成有限公式文法研发与开发集证伪；尚不具备通用论文方法完全复现，不自动激活选号算法。'}
        elif args.command=='rank-approved':
            from autoresearch.verification import rank_research_approved
            rows=[x for x in reg.algorithms(limit=300) if x['state']=='research_approved']
            active=[reg.get_algorithm(x['fingerprint']) for x in rows]
            nums,digest=history_from_official(args.csv,args.official_source)
            if len(active)>24:raise ValueError('获批研究公式超过24条，应先选择明确的规则子集')
            candidates,evidence=rank_research_approved(active,nums,k=args.k)
            path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('w',newline='',encoding='utf-8-sig') as fp:
                writer=csv.writer(fp);writer.writerow(('rank','number','model_status'))
                for pos,num in enumerate(candidates,1):writer.writerow((pos,num,'uncalibrated_research_only'))
            out={'output':str(path),'count':len(candidates),'evidence':evidence,
                 'note':'研究库独立排名，与原正式过滤引擎隔离，绝非实际中奖概率'}
            if args.target_period:
                from autoresearch.prospective import precommit
                record=load_csv(Path(args.csv).read_bytes())
                previous=str(record.frame['period'].iloc[-1])
                algo_digest=hashlib.sha256(json.dumps([a.fingerprint() for a in active],sort_keys=True).encode()).hexdigest()
                out['frozen']=precommit(store.db,target_period=args.target_period,previous_period=previous,
                    candidates=candidates,history_sha256=digest,algorithm_sha256=algo_digest,
                    source_description=args.official_source)
        elif args.command=='approve-research':
            out=reg.approve_research_only(args.fingerprint,args.audit_id,args.reviewer,args.consent)
        elif args.command=='review-code':
            algo=reg.get_algorithm(args.fingerprint);print(emit_review_code(algo.formula));return 0
        elif args.command=='status':
            out={'documents':reg.documents(args.limit),'algorithms':reg.algorithms(args.limit),
                 'audits':reg.audits(args.limit)}
        else:raise ValueError('不支持的命令')
    dump(out)
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,FileNotFoundError,PermissionError,KeyError,RuntimeError) as e:
        print('科研任务未完成：'+str(e),file=sys.stderr);sys.exit(2)
