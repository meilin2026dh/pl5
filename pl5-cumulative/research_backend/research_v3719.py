"""PL5 V3.7.19 retrospective research verification CLI (no wager/bet actions)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pailie5.data import load_csv
from pailie5.research_validation_v3719 import (
    Draw, METHODS, Protocol, auxiliary_track_checks, run_walk_forward,
    synthetic_fair_draws,
)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument('--demo', action='store_true', help='independent synthetic fair draws')
    src.add_argument('--csv', type=Path, help='CSV with chronological period,number columns')
    parser.add_argument('--demo-n', type=int, default=60)
    parser.add_argument('--seed', type=int, default=3719)
    parser.add_argument('--warmup', type=int, default=40)
    parser.add_argument('--test-size', type=int, default=10)
    parser.add_argument('--top-k', type=int, default=100)
    parser.add_argument('--methods', nargs='+', choices=METHODS, default=list(METHODS))
    parser.add_argument('--skip-auxiliary', action='store_true')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    p = Protocol(warmup=args.warmup, test_size=args.test_size,
                 top_k=args.top_k, seed=args.seed, methods=tuple(args.methods))
    if args.demo:
        draws = synthetic_fair_draws(n=args.demo_n, seed=args.seed)
        typ = 'synthetic_fair_iid'
        csv_warnings = []
    else:
        data = load_csv(args.csv.read_bytes())
        draws = tuple(Draw(str(r.period), str(r.number)) for r in data.frame.itertuples())
        typ = 'unverified_historical_csv'
        csv_warnings = list(data.warnings)
    report = run_walk_forward(draws, p, input_type=typ)
    report['source_warnings'] = csv_warnings
    report['auxiliary_tracks'] = (None if args.skip_auxiliary
                                   else auxiliary_track_checks(seed=args.seed))
    # Exclusive create prevents erasure of past evidence.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'schema':report['schema'], 'evidence':str(args.output),
                      'test_count':report['test_count'], 'input_type':typ,
                      'models':[{k:v for k,v in model.items() if k in ('method','hits','test_periods')}
                                for model in report['models']]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
