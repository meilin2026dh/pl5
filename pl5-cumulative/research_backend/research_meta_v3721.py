"""PL5 V3.7.21 counterexample-driven derived meta-operator research CLI."""
import argparse
import json
from pathlib import Path
from pailie5.math_discovery_v3720 import read_cells
from pailie5.meta_operator_v3721 import make_synthetic, propose, freeze, evaluate


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    sp=p.add_subparsers(dest='command',required=True)
    demo=sp.add_parser('demo-split');demo.add_argument('--case',required=True,
        choices=['square_sum','quadratic_difference','linear_sum','cubic_sum','iid_null']);demo.add_argument('--seed',type=int,default=3721)
    demo.add_argument('--out',required=True,type=Path)
    pr=sp.add_parser('propose');pr.add_argument('--train',required=True,type=Path)
    pr.add_argument('--study',required=True,type=Path);pr.add_argument('--top-n',type=int,default=12)
    fr=sp.add_parser('freeze');fr.add_argument('--study',required=True,type=Path)
    fr.add_argument('--validation',required=True,type=Path)
    ev=sp.add_parser('evaluate');ev.add_argument('--study',required=True,type=Path)
    ev.add_argument('--holdout',required=True,type=Path)
    args=p.parse_args(argv)
    if args.command=='demo-split':out=make_synthetic(args.out,case=args.case,seed=args.seed)
    elif args.command=='propose':out=propose(read_cells(args.train),args.study,top_n=args.top_n)
    elif args.command=='freeze':out=freeze(args.study,read_cells(args.validation))
    else:out=evaluate(args.study,read_cells(args.holdout))
    print(json.dumps({'command':args.command,'status':out.get('status'),
        'schema':out['schema'],'holdout_errors':out.get('holdout_errors'),
        'predictive_advantage':'NOT_ESTABLISHED'},ensure_ascii=False))

if __name__=='__main__':main()
