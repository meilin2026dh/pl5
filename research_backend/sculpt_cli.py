"""V1.1 CLI for reversible sculpting, completely local (no network or betting)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from pailie5.data import load_csv
from pailie5.pattern_rules import Configuration
from pailie5.basic_filters import BasicConstraint
from pailie5.sculpting import SculptSession, knives_from_history, rolling_sculpt_backtest
from pailie5.space_mapping import register_space_indicators


def main(argv=None):
    parser=argparse.ArgumentParser(description='PL5 V1.1 ESSE 可逆解空间雕塑实验')
    parser.add_argument('--csv',type=Path,help='官方核验CSV（period,number）；缺省使用合成演示数据')
    parser.add_argument('--indicators',default='sum,span,odd_count,digit_1,digit_5')
    parser.add_argument('--windows',default='3,4')
    parser.add_argument('--patterns',default='constant,strict_up,arithmetic')
    parser.add_argument('--k',type=int,default=100)
    parser.add_argument('--sum-max',type=int,default=None)
    parser.add_argument('--backtest',type=int,default=0,help='探索性滚动回测最近N期（0=不回测）')
    parser.add_argument('--out',type=Path,default=Path('runtime/esse_v11'))
    args=parser.parse_args(argv)
    register_space_indicators()
    demo=args.csv is None
    source=args.csv or Path(__file__).parent/'data'/'synthetic_demo.csv'
    content=source.read_bytes()
    dataset=load_csv(content,is_demo=demo)
    cfg=Configuration(indicators=tuple(x.strip() for x in args.indicators.split(',')),
       windows=tuple(int(x) for x in args.windows.split(',')),
       patterns=tuple(x.strip() for x in args.patterns.split(',')),
       transforms=('raw',),max_rules=35,max_total_remove=.99,min_keep=100)
    basics=[BasicConstraint('sum',maximum=args.sum_max)] if args.sum_max is not None else []
    history=dataset.frame['number'].tolist()
    knives,defaults=knives_from_history(history,cfg,basics)
    session=SculptSession(knives,enabled=defaults)
    ranking,summary=session.rank(k=args.k)
    root=args.out.expanduser()
    root.mkdir(parents=True,exist_ok=True)
    top=root/'top_k.csv'; full=root/'all_100000.csv'; report=root/'report.json'
    ranking.head(args.k).to_csv(top,index=False,encoding='utf-8-sig')
    ranking.to_csv(full,index=False,encoding='utf-8-sig')
    evidence={'summary':summary,'demo_data':demo,
              'source_sha256':hashlib.sha256(content).hexdigest(),
              'rule_trace':[x.as_dict() for x in session.sculpt().stages],
              'counterfactual':session.counterfactual(),
              'warnings':list(dataset.warnings)}
    if args.backtest:
        evidence['exploratory_backtest']=rolling_sculpt_backtest(history,cfg,
                           k=args.k,warmup=max(40,max(cfg.windows)),max_periods=args.backtest,basic=basics)
    report.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'summary':summary,'demo_data':demo,
                      'files':[str(top),str(full),str(report)]},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
