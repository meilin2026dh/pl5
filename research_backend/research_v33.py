"""V3.3 operator meta-learning command line: demo/table/study/schema/registry."""
from __future__ import annotations
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from pailie5.operator_metalearning_v33 import (learn,fixtures,MetaRegistry,VERSION,FAMILIES,PROPERTIES)
from pailie5.primitive_invention_v29 import history_array,discover
from research_v24 import read_history

def run(argv=None):
    parser=argparse.ArgumentParser(description='PL5 V3.3 算子三层元学习（仅科研）')
    parser.add_argument('action',choices=['demo','table','study','schema','registry'])
    parser.add_argument('--table-json',type=Path)
    parser.add_argument('--history',type=Path)
    parser.add_argument('--maximum',type=int,default=5)
    parser.add_argument('--seed',type=int,default=20261102)
    parser.add_argument('--required-property',action='append',default=[])
    parser.add_argument('--registry',type=Path,default=Path('runtime/v33_metalearning.sqlite'))
    parser.add_argument('--report',type=Path,default=Path('reports/v33_meta_demo.json'))
    args=parser.parse_args(argv)
    if args.action=='schema':
        out={'version':VERSION,'families':list(FAMILIES),'verifiable_properties':list(PROPERTIES),
             'math_input_domain':'digit 0..9 × digit 0..9','outputs':[3,4],
             'limitations':'仅五种有限模型家族；不证明彩票预测优势'}
    else:
        db=MetaRegistry(args.registry)
        if args.action=='registry':
            out={'version':VERSION,'cards':db.summary(),'count':len(db.summary())}
        else:
            if args.action=='table':
                if args.table_json is None:parser.error('table需要--table-json')
                if args.table_json.stat().st_size>1_000_000:raise ValueError('输入文件超过1MB')
                tables={'user_table':np.asarray(json.loads(args.table_json.read_text(encoding='utf-8-sig')))}
                source='用户提供数学表；来源未独立核验'
            elif args.action=='study':
                if args.history is None:parser.error('study需要--history')
                numbers=read_history(args.history)
                array=history_array(numbers)
                cutoff=len(array)-110
                if cutoff<120:raise ValueError('至少230期；末110期不参与算子诱导')
                discovered,_=discover(array[:cutoff],maximum=args.maximum)
                tables={op.identity:op.table_array for op in discovered}
                source='用户指定CSV的训练前缀（末110期未参与诱导；未经预测性能验证）'
            else:
                tables=fixtures();source='合成数学真值表（非真实彩票数据）'
            items=[]
            for name,table in tables.items():
                result=learn(table,source_id=name,seed=args.seed,maximum=args.maximum,
                             required_properties=args.required_property)
                cards=[]
                for ability in result.pop('abilities'):
                    cards.append({'card':ability.card(),'inserted':db.register(ability)})
                items.append({**result,'name':name,'abilities':cards})
            out={'version':VERSION,'status':'research_only','action':args.action,
                 'source':source,'items':items,
                 'registered_new':sum(sum(z['inserted'] for z in item['abilities']) for item in items),
                 'official_prediction_validation':'not_performed',
                 'registry':str(args.registry)}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(f'PL5 V3.3 {args.action}: report={args.report}; status=research_only')
    return out

if __name__=='__main__':run()
