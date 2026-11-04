"""PL5 V3.0 symbolic regression for invented finite-algebra operations."""
import argparse
import json
from pathlib import Path
import numpy as np
from pailie5.symbolic_operators_v30 import analyze_primitives, search_formula, certify_formula
from research_v24 import read_history


def main(argv=None):
    p=argparse.ArgumentParser(description='PL5 V3.0 研究性符号回归与算子压缩，不提供预测优势保证')
    p.add_argument('action',choices=['demo','study','formula-demo'])
    p.add_argument('--history',type=Path)
    p.add_argument('--seed',type=int,default=20261102)
    p.add_argument('--maximum',type=int,default=8)
    p.add_argument('--beam-width',type=int,default=24)
    p.add_argument('--max-nodes',type=int,choices=(3,5,7),default=5)
    p.add_argument('--report',type=Path,default=Path('reports/v30_symbolic.json'))
    p.add_argument('--registry',type=Path,default=Path('runtime/v30_symbolic.sqlite'))
    a=p.parse_args(argv)
    if a.action=='formula-demo':
        aa,bb=np.indices((10,10))
        table=(aa+bb)%3
        cert=search_formula(table,seed=a.seed,beam_width=a.beam_width,max_nodes=a.max_nodes)
        result={'version':'v30','synthetic_known_operator':'(a+b)%3',
                'symbolic':cert.as_card(),'certified':certify_formula(cert,table)}
    else:
        if a.action=='study':
            if not a.history:p.error('study需要--history CSV（来源需事先核验）')
            numbers=read_history(a.history)
            source='用户提供CSV，未由本程序独立核验官方来源'
        else:
            rng=np.random.default_rng(a.seed)
            d=rng.integers(0,10,(300,5))
            numbers=[''.join(map(str,row)) for row in d]
            source='合成独立均匀数据'
        result=analyze_primitives(numbers,seed=a.seed,maximum=a.maximum,beam_width=a.beam_width,
                                  max_nodes=a.max_nodes,registry=a.registry)
        result['source']=source
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(f'V3.0运行完成：{a.action}；报告 {a.report}')
    return result

if __name__=='__main__':main()
