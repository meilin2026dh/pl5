"""Run PL5 V3.7.5 bounded scientific-question research (no background worker)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from pailie5.scientific_runtime_v375 import run_scientific_cycles


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description='PL5 V3.7.5 scientific questions (offline synthetic research)')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cycles',type=int,default=3)
    parser.add_argument('--budget',type=int,default=400)
    parser.add_argument('--seed',type=int,default=37401)
    parser.add_argument('--control-every',type=int,default=4)
    args=parser.parse_args(argv)
    try:
        state=run_scientific_cycles(args.output,cycles=args.cycles,budget=args.budget,
                                    seed=args.seed,control_every=args.control_every)
        registry=json.loads((args.output/'science'/'registry.json').read_text('utf8'))
    except (ValueError, RuntimeError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f'SCIENTIFIC_RESEARCH_PAUSED {type(exc).__name__}: {exc}',file=sys.stderr)
        return 2
    print(json.dumps({'output':str(args.output.resolve()),
                      'completed_cycles':state['completed_cycles'],
                      'scientific_questions':len(registry['questions']),
                      'observed_issue_tags':len(state['issues']),
                      'research_only':True,'production_enabled':False,
                      'background_running':False,'status':'BOUNDED_SCIENCE_COMPLETE'},
                     ensure_ascii=False))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
