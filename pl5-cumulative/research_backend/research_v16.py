"""PL5 V1.6 read-only value center CLI. Never places bets or updates rules."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from pailie5.value_center_v16 import analyze


def main(argv=None):
    parser = argparse.ArgumentParser(description='PL5 V1.6 逐刀价值与动态研究权重审计（只读）')
    parser.add_argument('--db', default='runtime/sculpt_evidence_v152.sqlite')
    parser.add_argument('--min-periods', type=int, default=100)
    parser.add_argument('--alpha', type=float, default=0.01)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    report = analyze(args.db, minimum_periods=args.min_periods, alpha=args.alpha)
    result = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result+'\n', encoding='utf-8')
    print(result)
    return 0 if report['state']=='ready' else 2

if __name__=='__main__':
    raise SystemExit(main())
