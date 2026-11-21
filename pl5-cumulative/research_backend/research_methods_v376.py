"""Run a bounded PL5 V3.7.6 method-design study (synthetic, no daemon)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from pailie5.scientific_runtime_v376 import run_method_studies


def main(argv=None):
    parser=argparse.ArgumentParser(description='PL5 V3.7.6 adaptive scientific method research')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--historical',type=Path,required=True)
    parser.add_argument('--studies',type=int,default=4)
    parser.add_argument('--budget',type=int,default=160)
    parser.add_argument('--seed',type=int,default=37601)
    parser.add_argument('--control-every',type=int,default=4)
    args=parser.parse_args(argv)
    try:
        state=run_method_studies(args.output,args.historical,studies=args.studies,
                                 budget=args.budget,seed=args.seed,control_every=args.control_every)
    except (ValueError,RuntimeError,FileNotFoundError,KeyError,json.JSONDecodeError) as exc:
        print(f'SCIENTIFIC_METHOD_RESEARCH_PAUSED {type(exc).__name__}: {exc}',file=sys.stderr)
        return 2
    print(json.dumps({
        'status':'BOUNDED_METHOD_RESEARCH_COMPLETE',
        'output':str(args.output.resolve()),
        'historical_completed_cycles':state['historical_completed_cycles'],
        'total_method_studies':state['completed_studies'],
        'method_history':[{k:v for k,v in x.items() if k in ('study_number','method','case','holdout_delta','issues')}
                          for x in state['history']],
        'production_enabled':False,'background_running':False,
        'scientific_conclusion':'UNRESOLVED',
    },ensure_ascii=False))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
