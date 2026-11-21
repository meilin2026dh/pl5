"""CLI for source-certified program transfer. Holdout is exposed only to evaluate."""
import argparse
import json
from pathlib import Path
from pailie5.math_discovery_v3720 import read_cells
from pailie5.transfer_language_v3723 import certify_source_bank,fit_target,freeze_target,evaluate_target,public_holdout_digest


def main(argv=None):
    parser=argparse.ArgumentParser(description='V3.7.23 research-only transfer; no lottery predictor')
    cmd=parser.add_subparsers(dest='command',required=True)
    source=cmd.add_parser('certify-bank');source.add_argument('--source-study',action='append',required=True,type=Path)
    source.add_argument('--out',required=True,type=Path)
    fit=cmd.add_parser('fit-target');fit.add_argument('--train',required=True,type=Path)
    fit.add_argument('--bank',required=True,type=Path);fit.add_argument('--study',required=True,type=Path)
    fit.add_argument('--commitment',default=None,help='Public digest of holdout made BEFORE fitting')
    check=cmd.add_parser('freeze-target');check.add_argument('--validation',required=True,type=Path)
    check.add_argument('--bank',required=True,type=Path);check.add_argument('--study',required=True,type=Path)
    ev=cmd.add_parser('evaluate-target');ev.add_argument('--holdout',required=True,type=Path)
    ev.add_argument('--bank',required=True,type=Path);ev.add_argument('--study',required=True,type=Path)
    ev.add_argument('--reveal-nonce',default=None,help='Nonce revealed only for final scoring')
    commit=cmd.add_parser('commit-holdout');commit.add_argument('--holdout',required=True,type=Path)
    commit.add_argument('--nonce',required=True)
    args=parser.parse_args(argv)
    if args.command=='certify-bank':r=certify_source_bank(args.source_study,args.out)
    elif args.command=='commit-holdout':r={'commitment':public_holdout_digest(read_cells(args.holdout),args.nonce)}
    elif args.command=='fit-target':r=fit_target(read_cells(args.train),args.bank,args.study,holdout_commitment=args.commitment)
    elif args.command=='freeze-target':r=freeze_target(args.study,args.bank,read_cells(args.validation))
    else:r=evaluate_target(args.study,args.bank,read_cells(args.holdout),reveal_nonce=args.reveal_nonce)
    print(json.dumps({k:v for k,v in r.items() if k not in ('candidates','templates')},ensure_ascii=False))


if __name__=='__main__':main()
