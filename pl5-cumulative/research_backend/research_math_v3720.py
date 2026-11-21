"""PL5 V3.7.20: separate propose, freeze and test gates for mathematical operators."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from pailie5.math_discovery_v3720 import (
    split_synthetic, read_cells, propose, freeze, evaluate,
)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    commands=p.add_subparsers(dest='command',required=True)
    demo=commands.add_parser('demo-split')
    demo.add_argument('--case',choices=('composite_absproduct','shifted_square','iid_null'),default='composite_absproduct')
    demo.add_argument('--seed',type=int,default=3720)
    demo.add_argument('--out',required=True,type=Path)
    pr=commands.add_parser('propose')
    pr.add_argument('--train',required=True,type=Path)
    pr.add_argument('--study',required=True,type=Path)
    pr.add_argument('--seed',type=int,default=3720)
    pr.add_argument('--budget',type=int,default=1200)
    pr.add_argument('--top-n',type=int,default=16)
    sel=commands.add_parser('freeze')
    sel.add_argument('--study',required=True,type=Path)
    sel.add_argument('--validation',required=True,type=Path)
    te=commands.add_parser('evaluate')
    te.add_argument('--study',required=True,type=Path)
    te.add_argument('--holdout',required=True,type=Path)
    a=p.parse_args(argv)
    if a.command=='demo-split':
        out=split_synthetic(a.out,case=a.case,seed=a.seed)
    elif a.command=='propose':
        out=propose(read_cells(a.train),a.study,seed=a.seed,eval_budget=a.budget,top_n=a.top_n)
    elif a.command=='freeze':
        out=freeze(a.study,read_cells(a.validation))
    else:
        out=evaluate(a.study,read_cells(a.holdout))
    print(json.dumps({'command':a.command,'schema':out['schema'],
        'holdout_errors':out.get('holdout_errors'), 'study':str(getattr(a,'study',getattr(a,'out',''))),
        'predictive_advantage':'NOT_ESTABLISHED'},ensure_ascii=False))


if __name__=='__main__':
    main()
