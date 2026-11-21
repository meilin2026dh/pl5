"""PL5 V0.9 CLI: paper provenance, independent built-in checks, multiple-model evidence.

No command can automatically add algorithms to production prediction ranking.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import random
import sys
from autoresearch.store import LabStore
from autoresearch.registry_v06 import ResearchRegistry
from autoresearch.python_lab_v08 import PythonResearchStore
from autoresearch.proposals_v08 import DIGIT_COUNT_SOURCE,TRANSITION_SOURCE
from autoresearch.replication_v09 import ReplicationRegistry,verify_independent_kernels,pure_python_reference
from autoresearch.evidence_v09 import EvidenceLedger
from autoresearch.pair_review_v09 import PairReview
from pailie5.data import load_csv


def load_candidates(path):
    text=Path(path).read_text(encoding='utf-8-sig')
    if path.lower().endswith('.json'):
        arr=json.loads(text)
        if not isinstance(arr,list):raise ValueError('候选JSON必须是号码字符串列表')
        return arr
    # one number per line; never parse as integer because of leading zeros.
    return [x.strip() for x in text.splitlines() if x.strip()]


def demo():
    """Synthetic arithmetic self-check. No historical or official claim."""
    with LabStore(':memory:') as store:
        db=store.db
        paper=ResearchRegistry(db)
        lab=PythonResearchStore(db)
        protocols=ReplicationRegistry(db)
        evidence=EvidenceLedger(db)
        paper.add_document('demo-09','演示材料：仅用于受控测试',
            'This is synthetic documentation for a methodological test of independent digit features. '*2)
        model_ids=[];checks=[]
        for method,source in [('digit_sum',DIGIT_COUNT_SOURCE),('odd_count',TRANSITION_SOURCE)]:
            cid=lab.add(document_key='demo-09',source=source,origin='offline_template',
              method_claim='该研究假设没有经过真实的彩票前向验证，也不是论文原始方法。')['code_id']
            examples=['00000','12345','99999','01234']
            protocol=protocols.create(document_key='demo-09',code_id=cid,method_name=method,
                  method_type='method_adaptation',paper_locator='demo://not-a-paper',
                  math_assumptions='数字是0至9、固定5位、不从未来开奖结果学习',
                  procedure='验证两份独立实现（纯Python及NumPy）的数学定义一致，不测试任意候选算法Python评分',
                  expected_fixture={'numbers':examples,'expected':pure_python_reference(method,examples)})
            verified=protocols.verify_builtin(protocol['protocol_id'],exhaustive=True)
            assert verified['engineering_reproduced']
            checks.append({'method':method,'crosscheck':verified['cross_check']})
            model_id='demo_'+method
            registered=evidence.register_model(model_id=model_id,code_sha256=cid,
                  protocol_id=protocol['protocol_id'],reviewer='demo-not-real')
            model_ids.append(registered['model_id'])
        rng=random.Random(20261101)
        for period in range(20261001,20261021):
            candidates_a=[f'{n:05d}' for n in rng.sample(range(100000),100)]
            candidates_b=[f'{n:05d}' for n in rng.sample(range(100000),100)]
            for model_id,cands in zip(model_ids,[candidates_a,candidates_b]):
                evidence.seal(model_id=model_id,target_period=str(period),
                     previous_period=str(period-1),candidates=cands,
                     history_sha256=sha256(f'synthetic-history-{period}'.encode()).hexdigest(),
                     source_description='synthetic:simulation-not-real')
            number=f'{rng.randrange(100000):05d}'
            evidence.settle(target_period=str(period),number=number,
                 source_description='synthetic:simulation-not-real',
                 data_sha256=sha256(f'synthetic-result-{period}'.encode()).hexdigest())
        return {'demo_only':True,'official_data_used':False,'codes_executed':False,
                'cross_checks':checks,'family':evidence.family_report(),
                'warning':'模拟实验不证明任何彩票预测优势；验证的内置指标与候选开放Python算法并非同一个实现'}


def main(argv=None):
    ap=argparse.ArgumentParser(description='PL5 V0.9 论文复现证据链与家族错误控制')
    ap.add_argument('--db',default='runtime/autoresearch.sqlite')
    subs=ap.add_subparsers(dest='cmd',required=True)
    subs.add_parser('demo').add_argument('--out',default='examples/v09_synthetic_evidence_demo.json')
    subs.add_parser('status')
    x=subs.add_parser('check-kernel');x.add_argument('--method',required=True,choices=['digit_sum','odd_count','transition_count'])
    x=subs.add_parser('protocol-create');x.add_argument('--json',required=True)
    x=subs.add_parser('protocol-list')
    x=subs.add_parser('protocol-check');x.add_argument('--protocol-id',required=True)
    x=subs.add_parser('pair-register');x.add_argument('--protocol-id',required=True);x.add_argument('--primary-id',required=True);x.add_argument('--reference-id',required=True);x.add_argument('--reviewer',required=True);x.add_argument('--independence-basis',required=True)
    subs.add_parser('pair-list')
    x=subs.add_parser('pair-audit');x.add_argument('--pair-id',required=True);x.add_argument('--csv',required=True);x.add_argument('--k',type=int,default=100);x.add_argument('--eval-size',type=int,default=8);x.add_argument('--allow-docker',action='store_true')
    x=subs.add_parser('register');x.add_argument('--model-id',required=True);x.add_argument('--code-id',required=True)
    x.add_argument('--protocol-id',required=True);x.add_argument('--reviewer',required=True)
    x=subs.add_parser('seal');x.add_argument('--model-id',required=True);x.add_argument('--period',required=True)
    x.add_argument('--previous',required=True);x.add_argument('--candidates',required=True)
    x.add_argument('--history-sha256',required=True);x.add_argument('--source',required=True)
    x=subs.add_parser('settle');x.add_argument('--period',required=True);x.add_argument('--number',required=True)
    x.add_argument('--data-sha256',required=True);x.add_argument('--source',required=True)
    x=subs.add_parser('report');x.add_argument('--model-id')
    args=ap.parse_args(argv)
    if args.cmd=='demo':
        output=demo()
        out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
        print(json.dumps({'saved':str(out),'models':output['family']['models_registered'],
              'tests':len(output['cross_checks']),'synthetic_only':True},ensure_ascii=False,indent=2))
        return 0
    with LabStore(args.db) as store:
        rep=ReplicationRegistry(store.db)
        ledger=EvidenceLedger(store.db)
        pairs=PairReview(store.db)
        if args.cmd=='status':
            result={'protocols':rep.list(),'models':ledger.family_report(),
                    'prediction_model_auto_promotion':False}
        elif args.cmd=='check-kernel':result=verify_independent_kernels(args.method,exhaustive=True)
        elif args.cmd=='protocol-create':
            payload=json.loads(Path(args.json).read_text(encoding='utf-8'))
            result=rep.create(**payload)
        elif args.cmd=='protocol-list':result=rep.list()
        elif args.cmd=='protocol-check':result=rep.verify_builtin(args.protocol_id)
        elif args.cmd=='pair-register':result=pairs.register(protocol_id=args.protocol_id,primary_sha256=args.primary_id,reference_sha256=args.reference_id,reviewer=args.reviewer,independence_basis=args.independence_basis)
        elif args.cmd=='pair-list':result=pairs.list()
        elif args.cmd=='pair-audit':
            if not args.allow_docker:raise PermissionError('必须人工同意Docker隔离运行')
            raw=Path(args.csv).read_bytes()
            draws=load_csv(raw)
            if any('补零' in w for w in draws.warnings):raise ValueError('开奖CSV存在补零风险')
            result=pairs.audit(args.pair_id,draws.frame['number'].tolist(),k=args.k,eval_size=args.eval_size)
        elif args.cmd=='register':result=ledger.register_model(model_id=args.model_id,code_sha256=args.code_id,
                protocol_id=args.protocol_id,reviewer=args.reviewer)
        elif args.cmd=='seal':result=ledger.seal(model_id=args.model_id,target_period=args.period,
                previous_period=args.previous,candidates=load_candidates(args.candidates),
                history_sha256=args.history_sha256,source_description=args.source)
        elif args.cmd=='settle':result=ledger.settle(target_period=args.period,number=args.number,
                source_description=args.source,data_sha256=args.data_sha256)
        elif args.cmd=='report':result=ledger.model_report(args.model_id) if args.model_id else ledger.family_report()
        else:raise RuntimeError('未知命令')
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,RuntimeError,PermissionError,KeyError,FileNotFoundError) as exc:
        print('V0.9操作失败：'+str(exc),file=sys.stderr)
        sys.exit(2)
