"""PL5 V1.0 command line: recoverable research workflow and sealed candidate packets."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from autoresearch.collectors import Paper, DEFAULT_TOPICS
from autoresearch.store import LabStore
from autoresearch.integrated_v10 import ResearchCoordinator, sha
from autoresearch.bundles_v10 import CandidateBundles
from pailie5.data import load_csv

ROOT=Path(__file__).resolve().parent


def fixture_read(path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data,list) or len(data)>100:
        raise ValueError('离线文献fixture必须是最多100条的数组')
    return [Paper(**x) for x in data]


def official_read(path, source):
    if not str(source).startswith(('official:', 'https://')):
        raise ValueError('指定了数据时必须声明人工核验的官方来源')
    content=Path(path).read_bytes()
    d=load_csv(content)
    if d.warnings:raise ValueError('历史CSV出现警告，需要先修复：'+str(d.warnings))
    return d.frame['number'].tolist()


def demo():
    papers=fixture_read(ROOT/'examples'/'v10_demo_papers.json')
    with LabStore(':memory:') as s:
        c=ResearchCoordinator(s)
        config={'mode':'offline','fixture':sha([p.to_dict() for p in papers]),
                'topics':['sequential multiple testing'],'providers':['openalex'],
                'max_documents':2,'max_formulas':1,'max_code_proposals':1}
        id=c.create(config,run_id='run_v10_synthetic_demo')
        first=c.run(id,fixture_papers=papers)
        second=c.run(id,fixture_papers=papers)
        return {'demo_only':True,'run_id':id,'status':second['status'],
                'steps_completed':len(first['steps']),'steps_idempotent':all(x['attempts']==1 for x in c.status(id)['steps']),
                'paid_calls':c.status(id)['budget']['paid_model_calls'],
                'official_data_used':False,'code_executed':False,'predictive_edge_proven':False}


def main(argv=None):
    ap=argparse.ArgumentParser(description='PL5 V1.0 研究中控台（无自动投注，无预测优势承诺）')
    ap.add_argument('--db',default='runtime/autoresearch.sqlite')
    sub=ap.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('run')
    mode=p.add_mutually_exclusive_group(required=False)
    mode.add_argument('--offline-fixture')
    mode.add_argument('--live',action='store_true')
    p.add_argument('--run-id',help='续跑时传入已有run_id，须同时提供原模式参数')
    p.add_argument('--resume-latest',action='store_true',help='恢复同配置最近失败/中断任务；适用于无人值守巡检')
    p.add_argument('--topics',default='sequential multiple testing,randomness testing')
    p.add_argument('--providers',default='openalex,arxiv')
    p.add_argument('--max-requests',type=int,default=12)
    p.add_argument('--max-documents',type=int,default=3)
    p.add_argument('--official-csv')
    p.add_argument('--official-source')
    p.add_argument('--audit',action='store_true',help='开发集实验；须传官方历史CSV，不能视作前向预测证据')
    p=sub.add_parser('status');p.add_argument('--run-id')
    p=sub.add_parser('seal');p.add_argument('--official-csv',required=True);p.add_argument('--official-source',required=True)
    p.add_argument('--period',required=True);p.add_argument('--k',type=int,default=100)
    p.add_argument('--model-name',default='shadow-rules');p.add_argument('--salt',default='pl5-v10')
    p.add_argument('--allow-empty-baseline',action='store_true')
    p.add_argument('--out-dir',default='research_reports/v10_commits')
    p=sub.add_parser('verify-seal');p.add_argument('--packet',required=True)
    p.add_argument('--official-csv',required=True);p.add_argument('--require-ledger',action='store_true')
    p=sub.add_parser('demo');p.add_argument('--out',default='examples/v10_demo_report.json')
    a=ap.parse_args(argv)
    if a.cmd=='demo':
        report=demo()
        dst=Path(a.out);dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 0
    with LabStore(a.db) as s:
        coord=ResearchCoordinator(s)
        if a.cmd=='run':
            if not a.live and not a.offline_fixture:
                raise ValueError('必须明确提供 --live 或 --offline-fixture，不能隐式联网')
            papers=fixture_read(a.offline_fixture) if a.offline_fixture else None
            history=official_read(a.official_csv,a.official_source) if a.audit else None
            cfg={'mode':'live' if a.live else 'offline',
                 'topics':[s.strip() for s in a.topics.split(',') if s.strip()],
                 'providers':[s.strip() for s in a.providers.split(',') if s.strip()],
                 'max_requests':a.max_requests,'max_documents':a.max_documents,
                 'enable_development_audit':a.audit,
                 'dataset_sha256':sha(history) if history else None,
                 'official_source':a.official_source if a.audit else None}
            if papers is not None:cfg['fixture']=sha([p.to_dict() for p in papers])
            if a.resume_latest and a.run_id:
                raise ValueError('--resume-latest 和 --run-id 不能同时提供')
            run_id=a.run_id
            if a.resume_latest:
                normalized=coord.normalize_config(cfg)
                old=s.db.execute("SELECT run_id FROM v10_runs WHERE config_sha256=? AND status != 'completed' ORDER BY started_at DESC LIMIT 1",(sha(normalized),)).fetchone()
                if old:run_id=old['run_id']
            run_id=coord.create(cfg,run_id=run_id)
            report=coord.run(run_id,fixture_papers=papers,history_numbers=history)
            out={'run_id':report['run_id'],'status':report['status'],
                 'steps':{k:({'total':len(v.get('formulas',v.get('python_candidates',[]))) } if k in ('invent','propose_python') else v) for k,v in report['steps'].items()},
                 'budget':coord.status(run_id)['budget']}
        elif a.cmd=='status':
            out=coord.status(a.run_id)
        elif a.cmd=='seal':
            out=CandidateBundles(s.db,ROOT).issue(csv_path=a.official_csv,official_source=a.official_source,
                 target_period=a.period,k=a.k,model_name=a.model_name,salt=a.salt,
                 output_dir=a.out_dir,allow_empty_baseline=a.allow_empty_baseline)
        elif a.cmd=='verify-seal':
            out=CandidateBundles(s.db,ROOT).verify(a.packet,a.official_csv,
                 require_model_in_ledger=a.require_ledger)
        else:raise ValueError('未知命令')
    print(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False))
    return 0


if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,KeyError,FileNotFoundError,RuntimeError,PermissionError,TypeError) as e:
        print('V1.0操作失败：'+str(e),file=sys.stderr)
        sys.exit(2)
