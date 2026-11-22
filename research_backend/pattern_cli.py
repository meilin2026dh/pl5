"""示例：python pattern_cli.py --csv data/synthetic_demo.csv --backtest 30"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
from pailie5.data import load_csv
from pailie5.pattern_rules import Configuration, filter_next, historical_indicators, rolling_backtest
from pailie5.basic_filters import BasicConstraint, combine_basic_and_pattern


def main() -> None:
    p = argparse.ArgumentParser(description='PL5 通用指标时序过滤实验引擎')
    p.add_argument('--csv', required=True, type=Path, help='期号period,开奖号码number，必须从旧到新；数字期号会自动排序')
    p.add_argument('--mode', choices=('continuation', 'recurrence'), default='continuation')
    p.add_argument('--windows', default='3,4,6')
    p.add_argument('--indicators', default='sum,span,odd_count,unique_count,adjacent_equal,digit_5')
    p.add_argument('--transforms', default='raw,mod2,mod3')
    p.add_argument('--lookback', type=int, default=12)
    p.add_argument('--backtest', type=int, default=0)
    p.add_argument('--min-keep', type=int, default=1000)
    p.add_argument('--max-total-remove', type=float, default=0.8)
    p.add_argument('--sum-min', type=int)
    p.add_argument('--sum-max', type=int)
    p.add_argument('--export', type=Path, default=Path('pattern_candidates.csv'))
    p.add_argument('--report', type=Path, default=Path('pattern_report.json'))
    args = p.parse_args()
    data = load_csv(args.csv.read_bytes())
    history = data.frame['number'].tolist()
    config = Configuration(indicators=tuple(args.indicators.split(',')),
                           transforms=tuple(args.transforms.split(',')),
                           windows=tuple(int(w) for w in args.windows.split(',')),
                           mode=args.mode, lookback=args.lookback,
                           min_keep=args.min_keep, max_total_remove=args.max_total_remove)
    result = filter_next(history, config)
    basic = []
    if args.sum_min is not None or args.sum_max is not None:
        basic.append(BasicConstraint('sum', minimum=args.sum_min, maximum=args.sum_max))
    kept = combine_basic_and_pattern(basic, result.kept)
    args.export.parent.mkdir(parents=True, exist_ok=True)
    with args.export.open('w', newline='', encoding='utf-8-sig') as fh:
        writer = csv.writer(fh)
        writer.writerow(['number'])
        writer.writerows([[f'{int(n):05d}'] for n in kept])
    report = {
        'source': str(args.csv), 'warnings': list(data.warnings), 'latest_period': str(data.frame.iloc[-1]['period']),
        'samples': len(history), 'rules': [r.as_dict() for r in result.rules],
        'pattern_summary': result.summary(),
        'basic_count': len(basic), 'final_kept': int(len(kept)),
        'final_fair_random_coverage': len(kept) / 100_000,
        'recent_metrics': historical_indicators(history, config.indicators)[-12:],
        'research_only': '独立公平开奖时，任意保留K注的精确命中概率均为K/100000。'
    }
    if args.backtest:
        report['backtest_pattern_only'] = rolling_backtest(history, config,
                                                           warmup=max(30, max(config.windows)),
                                                           max_periods=args.backtest)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'summary': result.summary(), 'final_kept': len(kept),
                      'report': str(args.report), 'candidates': str(args.export)},ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
