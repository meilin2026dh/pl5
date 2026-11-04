"""V0.8 research-only open Python candidate CLI. No model can self-approve."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from autoresearch.store import LabStore
from autoresearch.registry_v06 import ResearchRegistry
from autoresearch.python_lab_v08 import PythonResearchStore, inspect_python_source, docker_available
from autoresearch.proposals_v08 import offline_proposals, llm_python_proposal
from pailie5.data import load_csv


def main(argv=None):
    p=argparse.ArgumentParser(description='PL5 V0.8开放Python算法自主研究（非预测保证）')
    p.add_argument('--db',default='runtime/autoresearch.sqlite')
    sub=p.add_subparsers(dest='cmd',required=True)
    s=sub.add_parser('status')
    s=sub.add_parser('list')
    s=sub.add_parser('propose-offline');s.add_argument('--document',required=True)
    s=sub.add_parser('auto-propose');s.add_argument('--max-documents',type=int,default=2)
    s.add_argument('--paid-llm',action='store_true');s.add_argument('--confirm-paid',action='store_true')
    s=sub.add_parser('propose-llm');s.add_argument('--document',required=True)
    s.add_argument('--confirm-paid',action='store_true');s.add_argument('--model')
    s=sub.add_parser('propose-file');s.add_argument('--document',required=True)
    s.add_argument('--source',required=True);s.add_argument('--claim',required=True)
    s=sub.add_parser('inspect');s.add_argument('--code-id',required=True)
    s=sub.add_parser('audit');s.add_argument('--code-id',required=True)
    s.add_argument('--csv',required=True);s.add_argument('--k',type=int,default=100)
    s.add_argument('--eval-size',type=int,default=8);s.add_argument('--allow-docker',action='store_true')
    s.add_argument('--official-source',required=True)
    a=p.parse_args(argv)
    with LabStore(a.db) as store:
        r=ResearchRegistry(store.db);lab=PythonResearchStore(store.db)
        if a.cmd=='status':out={'docker_ready':docker_available(),'registered':len(lab.list(100)),
            'code_execution_policy':'Docker only; explicit flag; no automatic production release'}
        elif a.cmd=='list':out={'candidates':lab.list()}
        elif a.cmd=='propose-offline':
            doc=r.get_document(a.document)
            out={'added':[lab.add(document_key=a.document,**spec) for spec in offline_proposals(doc)],
                 'warning':'离线模板是论文启发的研究迁移，不是论文原算法复现'}
        elif a.cmd=='auto-propose':
            if not 1<=a.max_documents<=3:raise ValueError('每次最多处理3篇文献')
            if a.paid_llm and not a.confirm_paid:raise PermissionError('付费生成Python必须明确批准')
            method='llm_opt_in' if a.paid_llm else 'offline_template'
            out={'documents':[],'paid':a.paid_llm,'code_executed':False,'auto_activated':False}
            for entry in r.documents(60):
                if lab.has_proposal_attempt(entry['doc_key'],method):continue
                doc=r.get_document(entry['doc_key'])
                specs=[llm_python_proposal(doc)] if a.paid_llm else offline_proposals(doc)
                proposals=[lab.add(document_key=entry['doc_key'],**spec) for spec in specs]
                lab.register_proposal_attempt(entry['doc_key'],method)
                out['documents'].append({'document_key':entry['doc_key'],'proposals':proposals})
                if len(out['documents'])>=a.max_documents:break
        elif a.cmd=='propose-llm':
            if not a.confirm_paid:raise PermissionError('必须显式提供--confirm-paid以允许付费模型调用')
            doc=r.get_document(a.document)
            spec=llm_python_proposal(doc,model=a.model)
            out=lab.add(document_key=a.document,**spec)
        elif a.cmd=='propose-file':
            r.get_document(a.document)
            src=Path(a.source).read_text(encoding='utf-8')
            out=lab.add(document_key=a.document,source=src,origin='human',method_claim=a.claim)
        elif a.cmd=='inspect':
            item=lab.get(a.code_id)
            out={'candidate':{k:v for k,v in item.items() if k!='source'},
                 'source':item['source'],'static':inspect_python_source(item['source'])}
        elif a.cmd=='audit':
            if not a.allow_docker:raise PermissionError('运行外部生成的Python代码必须显式提供--allow-docker')
            if not(a.official_source.startswith('official:') or a.official_source.startswith('https://')):
                raise ValueError('必须声明核验的官方开奖数据来源')
            data=Path(a.csv).read_bytes();draws=load_csv(data)
            if any('补零' in w for w in draws.warnings):raise ValueError('存在补零警告，请核实数据')
            out=lab.audit(a.code_id,draws.frame['number'].tolist(),data_digest=sha256(data).hexdigest(),
                          k=a.k,eval_size=a.eval_size,official_source=a.official_source)
        else:raise RuntimeError('未知命令')
    print(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False))
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,KeyError,RuntimeError,PermissionError,FileNotFoundError) as exc:
        print('V0.8研究流程失败：'+str(exc),file=sys.stderr);sys.exit(2)
