"""PL5 V2.4 nine-space exploratory research CLI. Does not fetch official history."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
from pailie5.nine_spaces_v24 import (Spaces,Rule,compose,walk_forward,
    capability_cards,predefined_exploratory_rules,FAMILIES,TemporalSpec,
    compose_temporal,walk_forward_temporal,describe_metric)


def read_history(path: Path) -> list[str]:
    if not path.is_file(): raise FileNotFoundError(path)
    with path.open('r',encoding='utf-8-sig',newline='') as fh:
        reader=csv.DictReader(fh)
        if not reader.fieldnames or 'number' not in reader.fieldnames:
            raise ValueError('必须包含number列；建议issue,date,number或period,number')
        rows=list(reader)
    if not rows: raise ValueError('空历史数据')
    if 'date' in reader.fieldnames:
        rows.sort(key=lambda r:(r['date'],r.get('issue','')))
    elif 'period' in reader.fieldnames:
        rows.sort(key=lambda r:r['period'])
    elif 'issue' in reader.fieldnames:
        rows.sort(key=lambda r:r['issue'])
    draws=[r['number'].strip() for r in rows]
    # validation shared with feature engine
    Spaces(draws)
    if 'issue' in reader.fieldnames and len({r['issue'] for r in rows})!=len(rows):
        raise ValueError('重复期号')
    if 'period' in reader.fieldnames and len({r['period'] for r in rows})!=len(rows):
        raise ValueError('重复期号')
    return draws


def main(argv=None):
    ap=argparse.ArgumentParser(description='PL5九空间探索研究；绝非中奖概率估计')
    ap.add_argument('command',choices=['cards','describe','demo','run','backtest'])
    ap.add_argument('--family',help='describe时指标所在空间')
    ap.add_argument('--metric',help='describe时的指标名')
    ap.add_argument('--history',type=Path,help='CSV，建议官方核验的期号及号码')
    ap.add_argument('--rule-json',type=Path,help='JSON规则列表；默认为五条演示过滤规则')
    ap.add_argument('--temporal-json',type=Path,help='时序规则配置JSON，按最近N期模式自动激活')
    ap.add_argument('--budget',type=int,default=100)
    ap.add_argument('--window',type=int,default=100)
    ap.add_argument('--backtest-periods',type=int,default=10)
    ap.add_argument('--min-train',type=int,default=30)
    ap.add_argument('--seed',type=int,default=42)
    ap.add_argument('--report',type=Path)
    ap.add_argument('--numbers',type=Path)
    args=ap.parse_args(argv)
    if args.command=='cards':
        result={'version':'v2.4','capabilities':capability_cards()}
    elif args.command=='describe':
        if not args.family or not args.metric:ap.error('describe需要--family和--metric')
        h=read_history(args.history) if args.history else []
        result=describe_metric(args.family,args.metric,history=h)
    else:
        if args.command!='demo' and args.history is None:
            ap.error('真实研究必须显式提供--history；不会把演示数据冒充官方')
        if args.command=='demo':
            history=[f'{(i*7919+i*i*17)%100000:05d}' for i in range(160)]
        else: history=read_history(args.history)
        history=history[-args.window:]
        rules=predefined_exploratory_rules() if not args.rule_json else [Rule(**r) for r in json.loads(args.rule_json.read_text(encoding='utf-8-sig'))]
        specs=[] if not args.temporal_json else [TemporalSpec(**r) for r in json.loads(args.temporal_json.read_text(encoding='utf-8-sig'))]
        if args.command=='backtest':
            if specs:
                result=walk_forward_temporal(history,rules,specs,min_train=args.min_train,last_n=args.backtest_periods,
                                            budget=args.budget,seed=args.seed)
            else:
                result=walk_forward(history,rules,min_train=args.min_train,last_n=args.backtest_periods,
                                    budget=args.budget,seed=args.seed)
        else:
            result=compose_temporal(history,rules,specs,budget=args.budget,seed=args.seed) if specs else compose(history,rules,budget=args.budget,seed=args.seed)
            result['source']='synthetic_demo' if args.command=='demo' else str(args.history)
            result['history_length']=len(history)
    data=json.dumps(result,ensure_ascii=False,indent=2,default=str)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(data+'\n',encoding='utf-8')
    else:
        print(data[:12000]+'\n...输出已截断，请使用 --report 保存完整结果' if len(data)>12000 else data)
    if args.numbers:
        if 'ranked_numbers' not in result: raise ValueError('仅run或demo可输出候选号码')
        args.numbers.parent.mkdir(parents=True,exist_ok=True)
        args.numbers.write_text('number\n'+'\n'.join(result['ranked_numbers'])+'\n',encoding='utf-8-sig')

if __name__=='__main__': main()
