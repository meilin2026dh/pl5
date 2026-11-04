"""PL5 V2.6 HDSE: bounded research CLI. Does not fetch/buy lottery tickets."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from pailie5.highdim_v26 import study,capabilities,proposals,full_ranking
from pailie5.hdse_registry_v26 import grow as registry_grow, status as registry_status
from research_v24 import read_history


def main(argv=None):
    ap=argparse.ArgumentParser(description='高维张量·时空状态·有限群谱科研实验')
    ap.add_argument('command',choices=['capabilities','propose','study','demo','cycle','status'])
    ap.add_argument('--history',type=Path,help='需要已核验来源的历史开奖CSV（number列）')
    ap.add_argument('--db',type=Path,default=Path('runtime/hdse_v26.sqlite'))
    ap.add_argument('--seed',type=int,default=20261102)
    ap.add_argument('--maximum',type=int,default=7)
    ap.add_argument('--test-periods',type=int,default=30)
    ap.add_argument('--budget',type=int,default=100)
    ap.add_argument('--null-trials',type=int,default=0)
    ap.add_argument('--report',type=Path)
    ap.add_argument('--numbers',type=Path)
    ap.add_argument('--full-ranking',type=Path,help='导出全部100000注研究评分CSV')
    a=ap.parse_args(argv)
    if a.command=='capabilities': result={'version':'hdse-v26','capabilities':capabilities()}
    elif a.command=='cycle':result=registry_grow(a.db,base_seed=a.seed,maximum=a.maximum)
    elif a.command=='status':result=registry_status(a.db)
    elif a.command=='propose':result={'version':'hdse-v26','proposals':[s.capability() for s in proposals(a.seed,a.maximum)]}
    else:
        if a.command=='study':
            if not a.history:ap.error('study需要--history，不能用合成数据冒充官方开奖')
            h=read_history(a.history)
        else:
            # IID random synthetic control, not actual lottery data.
            import numpy as np
            h=[f'{x:05d}' for x in np.random.default_rng(a.seed).integers(0,100000,size=320)]
        result=study(h,seed=a.seed,maximum=a.maximum,test_periods=a.test_periods,
                     budget=a.budget,null_trials=a.null_trials)
        result['source']='IID synthetic demonstration' if a.command=='demo' else str(a.history)
    txt=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)
    if a.report:
        a.report.parent.mkdir(parents=True,exist_ok=True)
        a.report.write_text(txt+'\n',encoding='utf-8')
        print('报告：',a.report)
    else:print(txt[:16000]+'\n...(请指定--report保存全部)' if len(txt)>16000 else txt)
    if a.full_ranking:
        if a.command not in ('demo','study'):ap.error('只允许demo/study导出完整排名')
        order,p=full_ranking(h,result)
        a.full_ranking.parent.mkdir(parents=True,exist_ok=True)
        with a.full_ranking.open('w',encoding='utf-8-sig') as out:
            out.write('rank,number,research_model_probability,uniform_baseline_probability\n')
            for rank,n in enumerate(order,1):out.write(f'{rank},{n:05d},{p[n]:.14g},0.00001\n')
        print('全10万注研究排名：',a.full_ranking)
    if a.numbers:
        if 'experimental_top_k' not in result:ap.error('只有study/demo可导出候选')
        a.numbers.parent.mkdir(parents=True,exist_ok=True)
        pairs=[(n,'experimental') for n in result['experimental_top_k']]+[(n,'random_control') for n in result['equal_budget_random_control']]
        a.numbers.write_text('number,group\n'+'\n'.join(f'{n},{kind}' for n,kind in pairs)+'\n',encoding='utf-8-sig')
        print('号码：',a.numbers)

if __name__=='__main__':main()
