"""PL5 V3.2 hypothesis-class invention CLI (research only)."""
import argparse
import json
from pathlib import Path
import numpy as np

from pailie5.category_hypotheses_v32 import (
    VERSION, infer_new_categories, HypothesisRegistry, synthetic_fixtures,
    study_historical_operators,
)
from pailie5.primitive_categories_v31 import run_operator_on_100k, compose_abilities
from research_v24 import read_history


def run(argv=None):
    p=argparse.ArgumentParser(description='PL5 V3.2 数学类别假设生成与逐格证伪（不用于自动下注）')
    p.add_argument('action',choices=['demo','table','study'])
    p.add_argument('--table-json',type=Path)
    p.add_argument('--history',type=Path)
    p.add_argument('--maximum',type=int,default=8)
    p.add_argument('--max-exceptions',type=int,default=5)
    p.add_argument('--min-saved-bits',type=int,default=1)
    p.add_argument('--registry',type=Path,default=Path('runtime/v32_category_hypotheses.sqlite'))
    p.add_argument('--report',type=Path,default=Path('reports/v32_hypothesis_study.json'))
    args=p.parse_args(argv)
    db=HypothesisRegistry(args.registry)
    if args.action=='study':
        if args.history is None:p.error('study需指定--history')
        history=read_history(args.history)
        report=study_historical_operators(history,maximum=args.maximum,registry=args.registry)
        report['dataset_source']='用户指定CSV；未自行证明其官方来源'
    else:
        if args.action=='table':
            if args.table_json is None:p.error('table需指定--table-json')
            if args.table_json.stat().st_size>1024*1024:raise ValueError('数学表文件超过1MiB')
            data=json.loads(args.table_json.read_text(encoding='utf-8-sig'))
            tables={'provided_mathematical_table':np.asarray(data)}
            source='用户自定义的10×10数学算子表'
        else:
            tables=synthetic_fixtures()
            source='合成数学运算表（不包含彩票官方历史）'
        entries=[]; first=None
        for label,t in tables.items():
            result=infer_new_categories(t,source_id=label,min_saved_bits=args.min_saved_bits,
                                        max_exceptions=args.max_exceptions)
            operators=[]
            for ability in result.pop('abilities'):
                if first is None:first=ability
                operators.append({'card':ability.card(),'registered':db.register(ability)})
            entries.append({**result,'name':label,'abilities':operators})
        report={'version':VERSION,'action':args.action,'dataset_source':source,
                'entries':entries,'registry':str(args.registry),
                'created_abilities':sum(len(x['abilities']) for x in entries),
                'status':'research_only','predictive_advantage':'NOT_ESTABLISHED'}
        if first is not None:
            mask=run_operator_on_100k(first,(0,4),(0,))
            report['esse_research_mask']={k:v for k,v in mask.items() if k!='mask'}
            chain=compose_abilities({'apply':first.id,'args':[{'digit':0},{'digit':4}]},
                                    {first.id:first})
            report['aan_composition']={k:v for k,v in chain.items() if k!='outputs'}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(f'PL5 V3.2 {args.action} | status=research_only | report={args.report}')
    return report

if __name__=='__main__':
    run()
