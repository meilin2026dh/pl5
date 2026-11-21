"""Task-blocked, exploratory summaries. Never treat reused cells as new tasks."""
from __future__ import annotations
from collections import defaultdict
import itertools
import math
import numpy as np
from scipy.stats import binomtest


def exact_sign_flip(differences) -> float:
    x=np.asarray(differences,dtype=float)
    if x.ndim!=1 or not 1<=len(x)<=20 or not np.isfinite(x).all():
        raise ValueError('expected 1..20 finite task differences')
    observed=abs(float(x.sum()))
    extreme=sum(abs(sum(a*b for a,b in zip(signs,x)))>=observed-1e-12
                for signs in itertools.product((-1,1),repeat=len(x)))
    return extreme/(2**len(x))


def holm_adjust(pvalues: dict[str,float]) -> dict[str,float]:
    if any(not math.isfinite(v) or not 0<=v<=1 for v in pvalues.values()):
        raise ValueError('p values must be finite and between 0 and 1')
    ordered=sorted(pvalues,key=lambda k:pvalues[k])
    result={}; previous=0.0
    for i,name in enumerate(ordered):
        previous=max(previous,min(1.0,(len(ordered)-i)*pvalues[name]))
        result[name]=previous
    return result


def summarize(trials: list[dict]) -> dict:
    if not trials: raise ValueError('no completed trials')
    keys=[(r['case'],r['seed'],r['arm']) for r in trials]
    if len(set(keys))!=len(keys): raise ValueError('duplicate trials')
    arms=sorted({r['arm'] for r in trials})
    arm_summary={}
    for arm in arms:
        chosen=[r for r in trials if r['arm']==arm]
        structured=[r for r in chosen if r['task_group']!='iid_control']
        controls=[r for r in chosen if r['task_group']=='iid_control']
        def rate(rows,key,count):
            return sum(r[key] for r in rows)/sum(r[count] for r in rows) if rows else None
        item={
            'trials':len(chosen),'structured_trials':len(structured),'iid_trials':len(controls),
            'holdout_accuracy':rate(structured,'holdout_correct','holdout_n'),
            'training_accuracy':rate(structured,'training_correct','training_n'),
            'exact_reconstructions':sum(r['exact_reconstruction'] for r in structured),
            'mean_nodes':float(np.mean([r['nodes'] for r in structured])) if structured else None,
            'mean_fit_seconds':float(np.mean([r['fit_seconds'] for r in chosen])),
            'all_budgets_matched':all(r['budget_matched'] for r in chosen),
            'min_evaluations':min(r['evaluations'] for r in chosen),
            'max_evaluations':max(r['evaluations'] for r in chosen),
            'mean_proposals':float(np.mean([r['proposals'] for r in chosen])),
        }
        if controls:
            k=sum(r['holdout_correct'] for r in controls); n=sum(r['holdout_n'] for r in controls)
            test=binomtest(k,n,.1,alternative='two-sided')
            ci=test.proportion_ci(confidence_level=.95,method='exact')
            item['iid_control']={'correct':k,'cells':n,'accuracy':k/n,
                                 'exact_reconstructions':sum(r['exact_reconstruction'] for r in controls),
                                 'p_two_sided':float(test.pvalue),
                                 'exact_95pct_interval':[float(ci.low),float(ci.high)]}
        arm_summary[arm]=item
    groups=defaultdict(list)
    for r in trials:
        if r['task_group']!='iid_control': groups[(r['case'],r['arm'])].append(r)
    task_means={}
    for (case,arm),rows in groups.items():
        task_means.setdefault(case,{})[arm]={
            'accuracy':float(np.mean([r['holdout_correct']/r['holdout_n'] for r in rows])),
            'exact':sum(r['exact_reconstruction'] for r in rows),'trials':len(rows),
            'mean_nodes':float(np.mean([r['nodes'] for r in rows]))}
    contrasts={}
    for arm in ('no_mutation','no_crossover','no_complexity','no_warm_start'):
        available=sorted(case for case in task_means if 'full' in task_means[case] and arm in task_means[case])
        if not available: continue
        for case in available:
            lhs={r['seed'] for r in groups[case,'full']}; rhs={r['seed'] for r in groups[case,arm]}
            if lhs!=rhs: raise ValueError('paired comparison requires identical seeds')
        d=[task_means[c]['full']['accuracy']-task_means[c][arm]['accuracy'] for c in available]
        contrasts[arm]={'task_count':len(available),'tasks':available,'full_minus_ablation_by_task':d,
                        'mean_difference':float(np.mean(d)),
                        'p_two_sided_sign_flip':exact_sign_flip(d),
                        'assumption':'task-level sign symmetry/exchangeability under null; conditional developmental diagnostic',
                        'unit':'one task mean over seeds, never one input cell or repeated split'}
    adjusted=holm_adjust({k:v['p_two_sided_sign_flip'] for k,v in contrasts.items()})
    for k,value in adjusted.items(): contrasts[k]['holm_p']=value
    controls_adjusted=holm_adjust({k:v['iid_control']['p_two_sided'] for k,v in arm_summary.items() if 'iid_control' in v})
    for k,value in controls_adjusted.items(): arm_summary[k]['iid_control']['holm_p_across_arms']=value
    return {'arms':arm_summary,'task_means':task_means,'prespecified_contrasts':contrasts,
            'all_budgets_matched':all(r['budget_matched'] for r in trials),
            'interpretation':'developmental synthetic benchmark, not a random sample of all mathematical tasks; no lottery evidence',
            'production_enabled':False}
