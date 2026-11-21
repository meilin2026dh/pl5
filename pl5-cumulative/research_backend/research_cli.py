"""PL5 V0.5 autonomous research CLI. Metadata scan can run unattended on Windows."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

from autoresearch.collectors import collect_all, DEFAULT_TOPICS
from autoresearch.store import LabStore
from autoresearch.lab import Hypothesis, propose, relevance_score, walk_forward, rank_100
from pailie5.data import load_csv
from autoresearch.prospective import precommit,settle_from_history,outcome_report


def official_history(path, source: str):
    if not source or not (source.startswith('https://') or source.startswith('official:')):
        raise ValueError('使用历史数据时必须传入 --official-source https://官方公告URL 或 official:来源说明')
    content=Path(path).read_bytes()
    data=load_csv(content)
    if any('补零' in w for w in data.warnings):
        raise ValueError('官方数据存在前导零丢失，须手工核验并修复后才能进行研究')
    return data.frame['number'].tolist(),hashlib.sha256(content).hexdigest(),list(data.warnings)


def scan(store, args):
    config = Path(args.config)
    topics=DEFAULT_TOPICS
    if config.exists():
        settings=json.loads(config.read_text(encoding='utf-8'))
        topics=settings.get('topics',DEFAULT_TOPICS)
        if not isinstance(topics,list) or not topics or any(not isinstance(t,str) or len(t)>100 for t in topics):
            raise ValueError('检索主题配置无效')
    papers,errors=collect_all(topics,days=args.days,limit=args.limit,
                             providers=tuple(args.providers.split(',')))
    inserted=store.upsert_papers(papers,relevance_score)
    store.record_cycle(len(papers),inserted,errors)
    return {'fetched':len(papers),'new_papers':inserted,'errors':errors}


def synthesize(store,*, threshold=2, max_papers=40):
    candidates=store.papers(limit=max_papers,min_score=threshold)
    new=0
    for p in candidates:
        # Reuse only known, locally validated algorithm operators.
        from autoresearch.collectors import Paper
        paper=Paper(p['key'],p['source'],p['title'],p['abstract'],p['url'],p['published'],p['topic'],p['authors'])
        for spec in propose(paper):
            new+=int(store.add_hypothesis(spec,p['key']))
    return {'reviewed_papers':len(candidates),'new_hypotheses':new,
            'total_hypotheses':len(store.hypotheses(limit=10000))}


def evaluate(store,numbers,digest,*,limit=8,k=100,eval_size=60):
    results=[]
    specs=store.hypotheses(limit=limit,status='candidate')
    for row in specs:
        spec=Hypothesis(**row['specification'])
        report=walk_forward(numbers,spec,k=k,eval_size=eval_size)
        store.record_trial(spec.fingerprint(),'development',digest,report)
        results.append({'hypothesis':spec.fingerprint(), 'indicator':spec.indicator,
                        'pattern':spec.pattern, **report})
    return {'evaluated':len(results),'results':results,
            'note':'开发集探索，不是独立验证；多算法反复搜索会产生选择偏差。'}


def _write_json(report,path):
    if path:
        target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')


def _write_candidates(candidates,path):
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.writer(f);writer.writerow(['rank','number','status'])
        for i,num in enumerate(candidates,1):writer.writerow([i,num,'research_only_unvalidated'])


def main(argv=None):
    parser=argparse.ArgumentParser(description='PL5 论文研究与算法候选库（不自动投注，不承诺命中）')
    parser.add_argument('--db',default='runtime/autoresearch.sqlite')
    parser.add_argument('--config',default='config/research_topics.json')
    commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('scan');p.add_argument('--days',type=int,default=21);p.add_argument('--limit',type=int,default=5)
    p.add_argument('--providers',default='openalex,arxiv,github')
    p=commands.add_parser('propose');p.add_argument('--threshold',type=float,default=2)
    p=commands.add_parser('analyze');p.add_argument('--limit',type=int,default=3)
    p.add_argument('--min-score',type=float,default=3)
    p.add_argument('--model',default=None)
    p=commands.add_parser('evaluate');p.add_argument('--csv',required=True);p.add_argument('--official-source',required=True)
    p.add_argument('--k',type=int,default=100);p.add_argument('--limit',type=int,default=8)
    p.add_argument('--eval-size',type=int,default=60);p.add_argument('--output',default='research_reports/evaluation.json')
    p=commands.add_parser('cycle');p.add_argument('--days',type=int,default=21);p.add_argument('--limit',type=int,default=5)
    p.add_argument('--providers',default='openalex,arxiv,github')
    p.add_argument('--csv');p.add_argument('--official-source')
    p.add_argument('--output',default='research_reports/latest_cycle.json')
    p=commands.add_parser('rank');p.add_argument('--csv',required=True);p.add_argument('--official-source',required=True)
    p.add_argument('--k',type=int,default=100);p.add_argument('--output',default='research_reports/top100_research_only.csv')
    p=commands.add_parser('status');p.add_argument('--limit',type=int,default=20)
    p=commands.add_parser('freeze');p.add_argument('--csv',required=True);p.add_argument('--official-source',required=True)
    p.add_argument('--target-period',required=True);p.add_argument('--k',type=int,default=100)
    p.add_argument('--output',default='research_reports/frozen_prediction.json')
    p=commands.add_parser('settle');p.add_argument('--csv',required=True);p.add_argument('--official-source',required=True)
    p.add_argument('--output',default='research_reports/prospective_results.json')
    commands.add_parser('prospective')
    p=commands.add_parser('shadow');p.add_argument('--fingerprint',required=True)
    args=parser.parse_args(argv)
    if getattr(args,'k',100)>100 or getattr(args,'k',100)<1:parser.error('--k 必须在1..100之间')
    with LabStore(args.db) as store:
        if args.command=='scan':out=scan(store,args)
        elif args.command=='propose':out=synthesize(store,threshold=args.threshold)
        elif args.command=='analyze':
            from autoresearch.collectors import Paper
            from autoresearch.llm import analyze_abstract
            out={'papers_analyzed':0,'cards':[],'errors':[],
                 'note':'需显式执行此命令才使用付费大模型API；不能自动将算法发布到正式库'}
            if not 1<=args.limit<=10: parser.error('analyze --limit 必须1到10')
            for r in store.papers_needing_analysis(limit=args.limit,min_score=args.min_score,model=args.model):
                paper=Paper(r['key'],r['source'],r['title'],r['abstract'],r['url'],r['published'],r['topic'],r['authors'])
                try:
                    card,spec=analyze_abstract(paper,model=args.model)
                    store.add_literature_card(paper.key,card,spec)
                    out['papers_analyzed']+=1
                    out['cards'].append({'key':paper.key,'card':card,
                           'hypothesis':spec.fingerprint() if spec else None})
                except (ValueError,RuntimeError) as exc:
                    out['errors'].append({'paper_key':paper.key,'error':str(exc)[:200]})
        elif args.command=='status':
            out={'papers':store.papers(limit=args.limit),'hypotheses':store.hypotheses(limit=args.limit),
                 'trials':store.trials(limit=args.limit),
                 'literature_cards':store.literature_cards(limit=args.limit)}
        elif args.command=='shadow':
            store.set_status(args.fingerprint,'shadow')
            out={'status':'shadow','fingerprint':args.fingerprint,
                 'warning':'仅为影子实验登记，不代表预测有效或正式发布'}
        elif args.command=='evaluate':
            numbers,digest,warnings=official_history(args.csv,args.official_source)
            out=evaluate(store,numbers,digest,limit=args.limit,k=args.k,eval_size=args.eval_size)
            out['data']={'sha256':digest,'rows':len(numbers),'source_declared':args.official_source,'warnings':warnings}
            _write_json(out,args.output)
        elif args.command=='freeze':
            numbers,digest,warnings=official_history(args.csv,args.official_source)
            data=load_csv(Path(args.csv).read_bytes())
            previous=str(data.frame['period'].iloc[-1])
            active=[Hypothesis(**r['specification']) for r in store.hypotheses(limit=500,status='shadow')]
            candidates,evidence=rank_100(numbers,active,k=args.k)
            algorithm_hash=hashlib.sha256(json.dumps([x.fingerprint() for x in active],sort_keys=True).encode()).hexdigest()
            commit=precommit(store.db,target_period=args.target_period,previous_period=previous,
                             candidates=candidates,history_sha256=digest,algorithm_sha256=algorithm_hash,
                             source_description=args.official_source)
            out={'commit':commit,'candidates':candidates,'rule_evidence':evidence,
                 'data_warnings':warnings,'warning':'预注册只是研究封存，不能证明彩票命中优势或保证10期内中奖'}
            _write_json(out,args.output)
        elif args.command=='settle':
            numbers,digest,warnings=official_history(args.csv,args.official_source)
            data=load_csv(Path(args.csv).read_bytes())
            lookup=dict(zip(data.frame['period'],numbers))
            settled=settle_from_history(store.db,period_to_number=lookup,
                                        data_sha256=digest,source_description=args.official_source)
            out={'new_outcomes':settled,'report':outcome_report(store.db),'data_warnings':warnings}
            _write_json(out,args.output)
        elif args.command=='prospective':
            out=outcome_report(store.db)
        elif args.command=='rank':
            numbers,digest,warnings=official_history(args.csv,args.official_source)
            active=[Hypothesis(**r['specification']) for r in store.hypotheses(limit=500,status='shadow')]
            candidates,evidence=rank_100(numbers,active,k=args.k)
            _write_candidates(candidates,args.output)
            out={'count':len(candidates),'output':args.output,'active_shadow_hypotheses':len(active),
                 'evidence':evidence,'source_sha256':digest,
                 'warning':'实验性启发排序，不是实际中奖概率；即使没有激活规则，也会按可复现随机顺序输出K注。'}
        elif args.command=='cycle':
            out={'scan':scan(store,args),'propose':synthesize(store)}
            if args.csv:
                if not args.official_source:parser.error('提供CSV必须同时提供--official-source')
                numbers,digest,warnings=official_history(args.csv,args.official_source)
                out['evaluation']=evaluate(store,numbers,digest)
                out['data']={'rows':len(numbers),'sha256':digest,'source_declared':args.official_source,
                             'warnings':warnings}
            else:
                out['note']='本次未提供官方历史CSV，仅完成联网论文检索与研究假设登记。'
            _write_json(out,args.output)
        else:raise RuntimeError('unreachable')
    print(json.dumps(out,ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,FileNotFoundError,KeyError) as err:
        print('操作未完成：'+str(err),file=sys.stderr)
        sys.exit(2)
