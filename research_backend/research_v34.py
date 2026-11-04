"""PL5 V3.4 parameter hub, learned threshold/moduli, exact transfer experiments."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
from pailie5.parameter_hub_v34 import (VERSION,inventory,fit_step_constraint,fit_lift_moduli,ParameterAudit)
from pailie5.operator_metalearning_v33 import learn,fixtures,MetaRegistry
from pailie5.transfer_evolution_v34 import transfer,public_result
from research_v24 import read_history

def to_ids(file):
    if file is None:raise ValueError('需提供--history历史CSV')
    return [int(x) for x in read_history(file)]

def demo(seed=20261102):
    rng=np.random.default_rng(seed)
    uniform=rng.integers(0,100000,size=360).tolist()
    # Unequal synthetic last digit distribution, for test of detectability (not lottery evidence).
    biased=rng.integers(0,100000,size=400)
    biased=(biased//10)*10+rng.choice(10,size=len(biased),p=[.35]+[.65/9]*9)
    math_table=fixtures()['affine_modular']
    origin=learn(math_table,source_id='v34_math_source')['abilities'][0]
    changed=origin.table().copy();changed[1,7]=(int(changed[1,7])+1)%origin.levels
    migrated=transfer(origin,changed)
    return {'version':VERSION,'research_only':True,'source':'synthetic','uniform_constraint':fit_step_constraint(uniform),
            'synthetic_biased_lift':fit_lift_moduli(biased.tolist(),{'op':'digit','pos':4},{'op':'digit','pos':0}),
            'exact_transfer':public_result(migrated),'capabilities':inventory(),
            'prediction_advantage':'NOT_ESTABLISHED'}

def main(argv=None):
    parser=argparse.ArgumentParser(description='PL5 V3.4参数统一登记与迁移研究，无自动启用')
    parser.add_argument('action',choices=['catalog','demo','fit-step','fit-lift','transfer','audit'])
    parser.add_argument('--history',type=Path)
    parser.add_argument('--first-pos',type=int,default=0)
    parser.add_argument('--second-pos',type=int,default=1)
    parser.add_argument('--source-id',type=str)
    parser.add_argument('--target-table',type=Path)
    parser.add_argument('--seed',type=int,default=20261102)
    parser.add_argument('--audit-db',type=Path,default=Path('runtime/v34_parameter_audit.sqlite'))
    parser.add_argument('--source-db',type=Path,default=Path('runtime/v33_metalearning.sqlite'))
    parser.add_argument('--report',type=Path,default=Path('reports/v34_research.json'))
    args=parser.parse_args(argv)
    if args.action=='catalog':out=inventory()
    elif args.action=='audit':out={'version':VERSION,'records':ParameterAudit(args.audit_db).summary()}
    elif args.action=='demo':out=demo(args.seed)
    elif args.action=='fit-step':out=fit_step_constraint(to_ids(args.history))
    elif args.action=='fit-lift':
        if not (0<=args.first_pos<=4 and 0<=args.second_pos<=4):raise ValueError('digit position 0..4')
        out=fit_lift_moduli(to_ids(args.history),{'op':'digit','pos':args.first_pos},{'op':'digit','pos':args.second_pos})
    else:
        if args.source_id is None or args.target_table is None:raise ValueError('transfer需要--source-id和--target-table')
        if args.target_table.stat().st_size>1_000_000:raise ValueError('table too large')
        source=MetaRegistry(args.source_db).get(args.source_id)
        table=json.loads(args.target_table.read_text(encoding='utf-8-sig'))
        if not isinstance(table,list) or len(table)!=10 or any(not isinstance(row,list) or len(row)!=10 for row in table):
            raise ValueError('需要10x10 JSON数组')
        raw=transfer(source,np.asarray(table),source_id=str(args.target_table))
        out=public_result(raw)
    if args.action not in ('catalog','audit'):
        run_id,inserted=ParameterAudit(args.audit_db).register(args.action if args.action!='demo' else 'inventory',out) if args.action!='fit-step' and args.action!='fit-lift' else ParameterAudit(args.audit_db).register('fit_step' if args.action=='fit-step' else 'fit_lift',out)
        out={'run_id':run_id,'new_record':inserted,**out}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(f'V3.4 {args.action}: {args.report}  [research_only]')
    return out

if __name__=='__main__':main()
