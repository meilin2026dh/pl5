"""Run finite, resumable, offline mathematics research cycles; never execute external generated code."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from pailie5.autonomous_v374 import run_cycles


def main(argv=None):
    p = argparse.ArgumentParser(description='PL5 V3.7.4 offline autonomous research (synthetic mathematics; no wagering)')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--cycles', type=int, default=3)
    p.add_argument('--budget', type=int, default=400)
    p.add_argument('--seed', type=int, default=37401)
    p.add_argument('--control-every', type=int, default=4)
    args = p.parse_args(argv)
    try:
        state = run_cycles(args.output, cycles=args.cycles, budget=args.budget,
                           seed=args.seed, control_every=args.control_every)
    except (ValueError, RuntimeError, OSError, KeyError, json.JSONDecodeError) as error:
        print(f'RESEARCH_PAUSED {type(error).__name__}: {error}', file=sys.stderr)
        return 2
    print(json.dumps({'output': str(args.output.resolve()),
                      'completed_cycles': state['completed_cycles'],
                      'issues': len(state['issues']),
                      'next_hypothesis': state['next_hypothesis'],
                      'production_enabled': False,
                      'status': 'BOUNDED_RUN_COMPLETE',
                      'continuous_background_run': False}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
