"""PL5 V2.0 paper-to-capability command line, research-only and opt-in for code execution."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import sqlite3
import sys
from autoresearch.fulltext import read_local_document
from autoresearch.paper_factory_v20 import PaperFactory,offline_blueprint,llm_blueprint
from autoresearch.proposals_v08 import llm_python_proposal


def main(argv=None):
    p=argparse.ArgumentParser(description='PL5 V2.0论文方法→独立代码→研究能力说明书')
    p.add_argument('--db',default='runtime/autoresearch.sqlite')
    sub=p.add_subparsers(dest='command',required=True)
    x=sub.add_parser('ingest'); x.add_argument('--file',required=True);x.add_argument('--key',required=True);x.add_argument('--title',required=True)
    x.add_argument('--url',default='')
    x=sub.add_parser('auto-extract'); x.add_argument('--limit',type=int,default=3)
    x=sub.add_parser('extract');x.add_argument('--document',required=True)
    x.add_argument('--blueprint-json',help='提供人工核验的JSON方法卡（不传则离线生成未复核卡）')
    x.add_argument('--paid-llm',action='store_true');x.add_argument('--confirm-paid',action='store_true');x.add_argument('--model')
    x=sub.add_parser('propose-code');x.add_argument('--blueprint',required=True)
    x.add_argument('--role',choices=['primary','reference'],required=True)
    x.add_argument('--source',help='用户审核过的Python源文件')
    x.add_argument('--paid-llm',action='store_true');x.add_argument('--confirm-paid',action='store_true');x.add_argument('--model')
    x=sub.add_parser('audit');x.add_argument('--blueprint',required=True);x.add_argument('--csv',required=True)
    x.add_argument('--budget',type=int,default=100);x.add_argument('--periods',type=int,default=8)
    x.add_argument('--allow-docker',action='store_true')
    x=sub.add_parser('card');x.add_argument('--blueprint',required=True)
    x=sub.add_parser('status')
    a=p.parse_args(argv)
    path=Path(a.db);path.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(path) as db:
        with_obj=PaperFactory(db)
        if a.command=='ingest':
            body,raw_sha=read_local_document(a.file)
            result=with_obj.documents.add_document(a.key,a.title,body,url=a.url,kind='local')
            result['file_sha256']=raw_sha
        elif a.command=='auto-extract':result=with_obj.auto_extract(maximum=a.limit)
        elif a.command=='extract':
            doc=with_obj.documents.get_document(a.document)
            if a.paid_llm:
                spec=llm_blueprint(doc,confirm_paid=a.confirm_paid,model=a.model);mode='llm_opt_in'
            elif a.blueprint_json:
                spec=json.loads(Path(a.blueprint_json).read_text(encoding='utf8'));mode='manual'
            else:spec=offline_blueprint(doc);mode='offline_unreviewed'
            result=with_obj.register_blueprint(a.document,spec,mode=mode)
        elif a.command=='propose-code':
            blueprint=with_obj.get_blueprint(a.blueprint)
            if a.paid_llm and a.source:raise ValueError('不能同时指定源码文件和大模型')
            if a.paid_llm:
                if not a.confirm_paid:raise PermissionError('付费模型调用需要--confirm-paid')
                doc=with_obj.documents.get_document(blueprint['document_key'])
                # Existing proven research-only code generator is reused; its method adaptation
                # is a hypothesis, not a faithful paper reproduction.
                snippet=blueprint['blueprint']['excerpt']
                payload=llm_python_proposal({**doc,'text_excerpt':snippet+'\n'+doc['text_excerpt'][:12000]},model=a.model)
                src=payload['source'];origin='llm_opt_in';claim=payload['method_claim']
            elif a.source:
                src=Path(a.source).read_text(encoding='utf8');origin='human';claim='人工提交的候选评分器，隔离执行前仅开展静态检查；非论文忠实复现认证。'
            else:raise ValueError('必须提供--source，或显式批准--paid-llm --confirm-paid')
            result=with_obj.link_code(a.blueprint,src,role=a.role,origin=origin,claim=claim)
        elif a.command=='audit':
            if not a.allow_docker:raise PermissionError('必须显式提供--allow-docker')
            with open(a.csv,encoding='utf-8-sig',newline='') as fp:
                rows=list(csv.DictReader(fp))
            if not rows or any(not all(k in r for k in ('issue','date','number')) for r in rows):
                raise ValueError('CSV必须有issue,date,number且非空')
            if len(set(r['issue'] for r in rows))!=len(rows):raise ValueError('开奖期号重复')
            rows.sort(key=lambda r:r['date'])
            draws=[r['number'] for r in rows]
            result=with_obj.study(a.blueprint,draws,budget=a.budget,periods=a.periods,allow_docker=True)
        elif a.command=='card':result=with_obj.capability_card(a.blueprint)
        else:result=with_obj.status()
    print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False))
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,KeyError,PermissionError,RuntimeError,OSError,json.JSONDecodeError) as ex:
        print('V2.0研究任务失败：'+str(ex),file=sys.stderr)
        sys.exit(2)
