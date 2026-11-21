"""V3.7.22 staged scientific experiment CLI (research-only)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from pailie5.math_discovery_v3720 import read_cells
from pailie5.language_evolution_v3722 import (create_synthetic_task, invent, falsify,
                                               freeze, evaluate, propose_revision, TASK_FAMILIES)


def main(argv=None):
    p=argparse.ArgumentParser(description='V3.7.22 grammar extension research; no lottery predictions')
    sub=p.add_subparsers(dest='command', required=True)
    task=sub.add_parser('create-task');task.add_argument('--family',choices=TASK_FAMILIES,required=True)
    task.add_argument('--seed',type=int,required=True);task.add_argument('--out',type=Path,required=True)
    invent_p=sub.add_parser('invent');invent_p.add_argument('--train',type=Path,required=True)
    invent_p.add_argument('--study',type=Path,required=True)
    invent_p.add_argument('--max-candidates',type=int,default=24)
    challenge=sub.add_parser('falsify');challenge.add_argument('--study',type=Path,required=True)
    challenge.add_argument('--challenge',type=Path,required=True)
    rev=sub.add_parser('revise');rev.add_argument('--study',type=Path,required=True)
    rev.add_argument('--train',type=Path,required=True)
    rev.add_argument('--challenge',type=Path,required=True)
    rev.add_argument('--new-study',type=Path,required=True)
    f=sub.add_parser('freeze');f.add_argument('--study',type=Path,required=True)
    f.add_argument('--validation',type=Path,required=True)
    e=sub.add_parser('evaluate');e.add_argument('--study',type=Path,required=True)
    e.add_argument('--holdout',type=Path,required=True)
    args=p.parse_args(argv)
    if args.command=='create-task':
        result=create_synthetic_task(args.out,family=args.family,seed=args.seed)
    elif args.command=='invent':
        result=invent(read_cells(args.train),args.study,max_candidates=args.max_candidates)
    elif args.command=='falsify':
        result=falsify(args.study,read_cells(args.challenge))
    elif args.command=='revise':
        result=propose_revision(args.study,read_cells(args.train),
                                read_cells(args.challenge),args.new_study)['revision_provenance']
    elif args.command=='freeze':
        result=freeze(args.study,read_cells(args.validation))
    else:
        result=evaluate(args.study,read_cells(args.holdout))
    print(json.dumps({k:v for k,v in result.items() if k not in ('diagnostics','candidates','results')},ensure_ascii=False))


if __name__=='__main__':main()
