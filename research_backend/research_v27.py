"""PL5 V2.7 Bayesian soft constraint research CLI. All numbers are illustrative scores."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from pailie5.bcse_v27 import study,capabilities,full_ranking,full_diagnostics
from research_v24 import read_history


def main(argv=None):
    p=argparse.ArgumentParser(description='BCSE贝叶斯软约束科研；不提供中奖保证')
    p.add_argument('command',choices=['capabilities','study','demo'])
    p.add_argument('--history',type=Path,help='官方CSV，包含number列，建议附issue和date')
    p.add_argument('--constraints',type=Path,help='自定义约束JSON列表；1—8条')
    p.add_argument('--budget',type=int,default=100)
    p.add_argument('--validation-periods',type=int,default=35)
    p.add_argument('--test-periods',type=int,default=30)
    p.add_argument('--dirichlet-alpha',type=float,default=30.)
    p.add_argument('--null-trials',type=int,default=0)
    p.add_argument('--seed',type=int,default=20261102)
    p.add_argument('--report',type=Path)
    p.add_argument('--candidates',type=Path)
    p.add_argument('--full-ranking',type=Path)
    a=p.parse_args(argv)
    if a.command=='capabilities':
        r={'version':'bcse-v27','capabilities':capabilities()}
    else:
        if a.command=='study':
            if a.history is None:p.error('study必须指定--history；禁止将合成数据冒充官方历史')
            h=read_history(a.history)
            source=f'user-supplied CSV: {a.history} (source requires verification)'
        else:
            h=[f'{int(v):05d}' for v in np.random.default_rng(a.seed).integers(100000,size=190)]
            source='IID synthetic demo; NOT official history'
        custom=json.loads(a.constraints.read_text('utf-8')) if a.constraints else None
        r=study(h,constraints=custom,seed=a.seed,test_periods=a.test_periods,
                validation_periods=a.validation_periods,budget=a.budget,
                dirichlet_alpha=a.dirichlet_alpha,null_trials=a.null_trials)
        r['source']=source
        if a.candidates:
            a.candidates.parent.mkdir(parents=True,exist_ok=True)
            content='number,group\n' + '\n'.join(f'{n},research_top_k' for n in r['experimental_top_k'])+'\n'+ '\n'.join(f'{n},equal_budget_random' for n in r['equal_budget_random_control'])+'\n'
            a.candidates.write_text(content,encoding='utf-8-sig')
        if a.full_ranking:
            order,fields=full_diagnostics(h,r,custom)
            a.full_ranking.parent.mkdir(parents=True,exist_ok=True)
            with a.full_ranking.open('w',encoding='utf-8-sig') as f:
                f.write('rank,number,model_posterior_mean,model_posterior_ci_low,model_posterior_ci_high,mean_signed_penalty,penalty_ci_low,penalty_ci_high,posterior_suppression_mass,violation_signature,uniform_baseline\n')
                for i,n in enumerate(order,1):
                    f.write(f"{i},{n:05d},{fields['model_probability_mean'][n]:.14g},{fields['model_probability_ci_low'][n]:.14g},{fields['model_probability_ci_high'][n]:.14g},{fields['penalty_mean'][n]:.12g},{fields['penalty_ci_low'][n]:.12g},{fields['penalty_ci_high'][n]:.12g},{fields['posterior_mass_below_uniform'][n]:.12g},{int(fields['signature'][n])},0.00001\n")
    blob=json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)
    if a.report:
        a.report.parent.mkdir(parents=True,exist_ok=True)
        a.report.write_text(blob+'\n',encoding='utf-8')
        print('报告保存：',a.report)
    else:print(blob[:16000]+ ('\n...请通过--report导出完整报告' if len(blob)>16000 else ''))

if __name__=='__main__':main()
