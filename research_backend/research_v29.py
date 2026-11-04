"""PL5 V2.9 — Invent learned finite binary mathematical operations from data."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from pailie5.primitive_invention_v29 import history_array, discover, study, fit_primitive, pmf, DIGITS, N, register_aan_primitives
from research_v24 import read_history


def main(argv=None):
    p=argparse.ArgumentParser(description='V2.9自主基础算子发明；默认科研隔离、无正式预测准入')
    p.add_argument('action',choices=('discover','demo','biased-demo','study'))
    p.add_argument('--history',type=Path)
    p.add_argument('--seed',type=int,default=20261102)
    p.add_argument('--maximum',type=int,default=40)
    p.add_argument('--budget',type=int,default=100)
    p.add_argument('--validation-periods',type=int,default=60)
    p.add_argument('--holdout-periods',type=int,default=50)
    p.add_argument('--report',type=Path,default=Path('reports/v29_research.json'))
    p.add_argument('--registry',type=Path,default=Path('runtime/v29_primitive_registry.sqlite'))
    p.add_argument('--aan-registry',type=Path,help='显式将工程研究算子登记到AAN；绝不赋予正式过滤权限')
    p.add_argument('--full-ranking',type=Path)
    a=p.parse_args(argv)
    if a.action=='study':
        if a.history is None:p.error('study需要--history；不会把演示数据冒充官方')
        history=read_history(a.history)
        source=f'用户提供CSV（来源尚未独立核验）：{a.history}'
    else:
        rng=np.random.default_rng(a.seed)
        digits=rng.integers(0,10,(500 if a.action!='biased-demo' else 800,5))
        if a.action=='biased-demo':digits[:,1]=digits[:,0]
        history=[''.join(str(v) for v in d) for d in digits]
        source='合成独立均匀数据' if a.action!='biased-demo' else '合成人工位置耦合数据'
    if a.action=='discover':
        arr=history_array(history)
        train_end=len(arr)-a.validation_periods-a.holdout_periods
        ops,duplicates=discover(arr[:train_end],maximum=a.maximum)
        result={'status':'research_only','cards':[op.card() for op in ops],
                'splits':{'train_periods':train_end},
                'duplicate_rejections':duplicates,'source':source}
    else:
        result=study(history,seed=a.seed,maximum=a.maximum,budget=a.budget,
                     validation_periods=a.validation_periods,holdout_periods=a.holdout_periods,
                     registry=a.registry)
        result['source']=source
        if a.full_ranking:
            a.full_ranking.parent.mkdir(parents=True,exist_ok=True)
            selected=result['selected_operator']
            if selected:
                data=history_array(history)
                train_end=len(data)-a.validation_periods-a.holdout_periods
                ops,_=discover(data[:train_end],maximum=a.maximum)
                op=next(op for op in ops if op.identity==selected['operator_id'])
                probs=pmf(op,fit_primitive(op,data[:train_end]),selected['mixture'])
                labels=op.vector()
            else:
                probs=np.full(N,1./N);labels=np.full(N,-1)
            # deterministic display order; tied weights are not real probability differences
            order=np.lexsort((np.random.default_rng(a.seed).random(N),-probs))
            with a.full_ranking.open('w',encoding='utf-8-sig',newline='') as file:
                writer=csv.writer(file);writer.writerow(['rank','number','model_assigned_probability','uniform_baseline','new_primitive_output','research_only'])
                for rank,n in enumerate(order,1):writer.writerow([rank,f'{n:05d}',f'{probs[n]:.14g}',1/N,int(labels[n]),'yes'])
    if a.aan_registry is not None:
        result['aan_research_primitives_inserted']=register_aan_primitives(result,a.aan_registry)
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    print(f'V2.9执行完成：{a.action}，新算子 {len(result.get("cards",[]))}，证据门槛 {result.get("validation_gate",{}).get("passed","n/a")}，结果 {a.report}')

if __name__=='__main__':main()
