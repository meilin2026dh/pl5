"""Run offline equal-budget PL5 V3.7.3 ablations; refuses to overwrite outputs."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from pailie5.ablation_benchmark_v373 import ARMS,CASES,DEFAULT_SEEDS,run_suite


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--budget',type=int,default=2500)
    p.add_argument('--seeds',nargs='+',type=int,default=list(DEFAULT_SEEDS))
    p.add_argument('--cases',nargs='+',choices=list(CASES),default=list(CASES))
    p.add_argument('--arms',nargs='+',choices=list(ARMS),default=list(ARMS))
    a=p.parse_args(argv)
    try:
        result=run_suite(a.output,seeds=a.seeds,cases=a.cases,arms=a.arms,budget=a.budget)
        print(json.dumps({'output':str(a.output),'trials':len(result['trials']),
                          'protocol_sha256':result['protocol_sha256'],
                          'all_budgets_matched':result['summary']['all_budgets_matched']}))
        return 0
    except (ValueError,OSError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr); return 2

if __name__=='__main__':
    raise SystemExit(main())
