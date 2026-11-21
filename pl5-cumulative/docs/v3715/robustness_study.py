"""Exploratory stress test: frozen fixed settings on unseen optimizer seeds and target counts."""
from __future__ import annotations
import json, statistics, time, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "research_backend"))
from benchmark_ga_cs_v3715 import _build_problem, METHODS
from pailie5.ga_cs_optimizer_v3715 import SearchProblem, optimize


def run():
    cases,masks,min_remain,compile_secs,digest=_build_problem()
    targets=(32_000,36_000,40_000)
    seeds=tuple(range(100,112))
    out={'schema':'pl5-v3715-robustness-exploratory-1','methods':list(METHODS),'targets':list(targets),
         'seeds':list(seeds),'evaluations_per_run':300,'all_rules_min_count':min_remain,
         'no_real_draw_labels':True, 'results':[], 'summary':[]}
    for target in targets:
        p=SearchProblem(masks=masks,rule_names=tuple(n for n,_ in cases),universe_size=100_000,
                        target=target,min_survivors=28_000,max_survivors=42_000,min_active=2)
        for seed in seeds:
            for method in METHODS[seed%6:]+METHODS[:seed%6]:
                tic=time.perf_counter_ns()
                r=optimize(p,method=method,evaluations=300,seed=seed,switch_ratio=.30)
                out['results'].append({'target':target,'seed':seed,'method':method,'fitness':r.best.fitness,
                                       'survivors':r.best.survivors,'feasible':r.best.feasible,
                                       'selected_rules':list(r.selected_rules),
                                       'elapsed_s':(time.perf_counter_ns()-tic)/1e9})
        for method in METHODS:
            xs=[x for x in out['results'] if x['target']==target and x['method']==method]
            out['summary'].append({'target':target,'method':method,
                                   'median_fitness':statistics.median(x['fitness'] for x in xs),
                                   'feasible_trials':sum(x['feasible'] for x in xs),
                                   'median_elapsed_s':statistics.median(x['elapsed_s'] for x in xs)})
    return out

if __name__=='__main__':
    result=run()
    open('../docs/v3715/robustness_results.json','x',encoding='utf-8').write(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    for t in result['targets']:
        print('TARGET',t)
        for x in result['summary']:
            if x['target']==t: print('  ',x['method'],x['feasible_trials'],'median fitness',x['median_fitness'])
