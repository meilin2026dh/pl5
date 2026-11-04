"""PL5 V2.8 bounded autonomous lift creation, sparse Bayesian constraint research."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from pailie5.autolift_v28 import invent, study, validated_history, fit_lift, pmf, Lift
from research_v24 import read_history


def main(argv=None):
    p=argparse.ArgumentParser(description='PL5 v2.8 自主升维算子创造/稀疏关系蒸馏；仅科研')
    p.add_argument('action',choices=('discover','demo','biased-demo','study'))
    p.add_argument('--history',type=Path)
    p.add_argument('--seed',type=int,default=20261102)
    p.add_argument('--maximum',type=int,default=12)
    p.add_argument('--budget',type=int,default=100)
    p.add_argument('--validation-periods',type=int,default=35)
    p.add_argument('--test-periods',type=int,default=30)
    p.add_argument('--report',type=Path,default=Path('reports/v28_report.json'))
    p.add_argument('--registry',type=Path,default=Path('runtime/v28_research.sqlite'))
    p.add_argument('--top100',type=Path)
    p.add_argument('--full-ranking',type=Path)
    a=p.parse_args(argv)
    if a.action=='discover':
        result={'status':'research_only','cards':[s.card() for s in invent(a.seed,a.maximum)]}
    else:
        if a.action=='study':
            if not a.history:p.error('study需要--history（不得将演示数据冒充官方）')
            history=read_history(a.history)
            source=f'用户CSV：{a.history}，来源待核验'
        else:
            rng=np.random.default_rng(a.seed)
            values=rng.integers(0,10,size=(440 if a.action=='biased-demo' else 190,5))
            if a.action=='biased-demo':values[:,1]=values[:,0]
            history=[''.join(str(d) for d in row) for row in values]
            source=('人为制造位置关联的合成数据' if a.action=='biased-demo' else '独立均匀合成数据')
        result=study(history,seed=a.seed,maximum=a.maximum,budget=a.budget,
                     validation_periods=a.validation_periods,test_periods=a.test_periods,
                     register_path=a.registry)
        result['source']=source
        if a.top100:
            a.top100.parent.mkdir(parents=True,exist_ok=True)
            with a.top100.open('w',encoding='utf-8-sig',newline='') as fh:
                out=csv.writer(fh);out.writerow(['number','group'])
                out.writerows((n,'experimental_top_k') for n in result['experimental_top_k'])
                out.writerows((n,'equal_budget_random') for n in result['equal_budget_random_control'])
        if a.full_ranking:
            from pailie5.autolift_v28 import unique_lifts
            ids=validated_history(history)
            t=len(ids)-a.validation_periods-a.test_periods
            specs,_=unique_lifts(invent(a.seed,a.maximum),ids[:t])
            selected=result['selected_operator']
            if selected:
                spec=next(s for s in specs if s.id==selected)
                fit=fit_lift(spec,ids,t)
                probs=pmf(spec,fit,ids,result['selected_eta'])
                bins=spec.codes(ids)
                weights=fit['sparse_logratio'][bins]
            else:
                probs=np.full(100000,1/100000,dtype=np.float64)
                bins=np.zeros(100000,dtype=np.int16)
                weights=np.zeros(100000,dtype=np.float64)
            # Deterministic tie breaking is for display; a tie conveys no prediction edge.
            ties=np.random.default_rng(a.seed).random(100000)
            order=np.lexsort((ties,-probs))
            a.full_ranking.parent.mkdir(parents=True,exist_ok=True)
            with a.full_ranking.open('w',encoding='utf-8-sig',newline='') as fh:
                writer=csv.writer(fh)
                writer.writerow(['rank','number','model_assigned_probability','uniform_baseline','lift_bin','signed_soft_penalty','research_only'])
                for rank,num in enumerate(order,1):
                    writer.writerow([rank,f'{num:05d}',f'{probs[num]:.14g}',.00001,int(bins[num]),
                                     f'{-result["selected_eta"]*weights[num]:.7g}' if selected else 0,'yes'])
    payload=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(payload+'\n',encoding='utf-8')
    print(f'完成：{a.action}；报告：{a.report}；候选数：{len(result.get("experimental_top_k",[]))}；证据门槛：{result.get("gate",{}).get("passed","n/a")}')

if __name__=='__main__':main()
