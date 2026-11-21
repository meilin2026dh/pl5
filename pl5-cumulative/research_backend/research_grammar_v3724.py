"""V3.7.24 finite-field grammar expansion; research only.

CLI exposes fit, freeze and evaluate as separate actions. External task setters may
supply their own independent cells; the bundled benchmark is NOT external blind.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from pailie5.math_discovery_v3720 import read_cells
from pailie5.grammar_discovery_v3724 import fit,freeze,evaluate,commit_holdout


def main(argv=None):
    p=argparse.ArgumentParser(description='PL5 V3.7.24 restricted grammar scientific study (not lottery forecasting)')
    sub=p.add_subparsers(dest='cmd',required=True)
    c=sub.add_parser('commit-holdout');c.add_argument('--holdout',type=Path,required=True);c.add_argument('--nonce',required=True)
    f=sub.add_parser('fit');f.add_argument('--train',type=Path,required=True);f.add_argument('--study',type=Path,required=True)
    f.add_argument('--arm',choices=['baseline','expanded'],required=True);f.add_argument('--digest')
    z=sub.add_parser('freeze');z.add_argument('--validation',type=Path,required=True);z.add_argument('--study',type=Path,required=True)
    e=sub.add_parser('evaluate');e.add_argument('--holdout',type=Path,required=True);e.add_argument('--study',type=Path,required=True)
    e.add_argument('--nonce')
    args=p.parse_args(argv)
    if args.cmd=='commit-holdout':out={'digest':commit_holdout(read_cells(args.holdout),args.nonce)}
    elif args.cmd=='fit':out=fit(read_cells(args.train),args.study,arm=args.arm,holdout_digest=args.digest)
    elif args.cmd=='freeze':out=freeze(args.study,read_cells(args.validation))
    else:out=evaluate(args.study,read_cells(args.holdout),nonce=args.nonce)
    print(json.dumps({k:v for k,v in out.items() if k not in ('exact_fit_programs',)},ensure_ascii=False,sort_keys=True))

if __name__=='__main__':main()
