"""python rank_cli.py --csv data/synthetic_demo.csv --out runtime/all_rank.csv"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from pailie5.data import load_csv
from pailie5.pattern_rules import Configuration
from pailie5.probability_ranker import rank_all_numbers, rolling_rank_backtest


def main():
    p=argparse.ArgumentParser(description='PL5十万号码研究性相对评分/权重排序')
    p.add_argument('--csv',required=True,type=Path)
    p.add_argument('--indicators',default='sum,span,odd_count,digit_5,same_positions_prev')
    p.add_argument('--transforms',default='raw,mod2')
    p.add_argument('--patterns',default='constant,strict_up,strict_down,arithmetic,period2,zigzag')
    p.add_argument('--windows',default='3,4,6')
    p.add_argument('--mode',choices=['continuation','recurrence'],default='continuation')
    p.add_argument('--lookback',type=int,default=15)
    p.add_argument('--strength',type=float,default=1.0)
    p.add_argument('--all-detected',action='store_true',help='把被硬过滤护栏跳过的规则也用于软排名')
    p.add_argument('--top-k',type=int,default=1000)
    p.add_argument('--backtest',type=int,default=0)
    p.add_argument('--out',type=Path,default=Path('runtime/pl5_all_rank.csv'))
    p.add_argument('--report',type=Path,default=Path('runtime/pl5_rank_report.json'))
    args=p.parse_args()
    data=load_csv(args.csv.read_bytes())
    history=data.frame['number'].tolist()
    cfg=Configuration(indicators=tuple(args.indicators.split(',')),
                      transforms=tuple(args.transforms.split(',')),
                      patterns=tuple(args.patterns.split(',')),
                      windows=tuple(int(x) for x in args.windows.split(',')),
                      mode=args.mode,lookback=max(args.lookback,max(int(x) for x in args.windows.split(','))))
    if args.all_detected:
        from pailie5.pattern_rules import filter_next
        from pailie5.probability_ranker import rule_key
        all_rules=filter_next(history,cfg).rules
        selected=[rule_key(r) for r in all_rules]
    else:
        selected=None
    result=rank_all_numbers(history,cfg,strength=args.strength,selected_rule_keys=selected)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    result.table.to_csv(args.out,index=False,encoding='utf-8-sig')
    payload={'source':str(args.csv),'data_warning':list(data.warnings),
             'summary':result.summary(top_k=args.top_k),'rules':result.rule_details,
             'probability_disclaimer':'model_probability为未校准启发式相对权重；公平独立开奖时每注条件概率均为0.00001。'}
    if args.backtest:
        payload['rolling_rank_backtest']=rolling_rank_backtest(history,cfg,max_periods=args.backtest,
              warmup=max(30,max(cfg.windows)),top_k=args.top_k,strength=args.strength)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'csv':str(args.out),'report':str(args.report),
                     'summary':payload['summary']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
