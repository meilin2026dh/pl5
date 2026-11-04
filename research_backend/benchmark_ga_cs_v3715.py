"""V3.7.15 cost-matched optimizer comparison on actual PL5 rule bitmaps.

All algorithms receive identical independent objective evaluations. This
compares optimizer mechanics, NOT predictive ability: no real draw history
is imported or used as the fitness target.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import time

import numpy as np

from benchmark_high_throughput_v3714 import _rules
from pailie5.basic_filters import apply_basic_filters
from pailie5.high_throughput_v3714 import ExactFilterEngine, BYTES_PER_MASK, mask_from_bitmap
from pailie5.ga_cs_optimizer_v3715 import SearchProblem, optimize

METHODS = ('random', 'greedy', 'anneal', 'ga', 'cs', 'ga_cs')


def _build_problem():
    cases = _rules()  # Existing 20 rules from PL5 V3.7.14, not a toy matrix.
    engine = ExactFilterEngine()
    for name, rule in cases:
        engine.add_basic(name, rule)
    start = time.perf_counter_ns()
    # Snapshot the exact masks before the experiment. These rule instances
    # and their 100000-bit results stay frozen for every optimizer.
    masks = tuple(engine._compile(name) for name, _ in cases)
    compile_seconds = (time.perf_counter_ns() - start) / 1e9
    full = (1 << 100000) - 1
    all_intersection = full
    h = hashlib.sha256()
    for (name, _), bits in zip(cases, masks):
        all_intersection &= bits
        h.update(name.encode('ascii'))
        h.update(b'\0')
        h.update(bits.to_bytes(BYTES_PER_MASK,'little'))
    return cases, masks, all_intersection.bit_count(), compile_seconds, h.hexdigest()


def _trial(method, p, cases, seed, evaluations):
    started = time.perf_counter_ns()
    answer = optimize(p, method=method, evaluations=evaluations, seed=seed,
                      switch_ratio=.30, population_size=12)
    elapsed = (time.perf_counter_ns() - started) / 1e9
    # Independently compare optimized combination against the PL5 legacy
    # vectorized oracle, not the same bitmap implementation.
    selected = [rule for j, (_, rule) in enumerate(cases) if answer.best.genome & (1 << j)]
    oracle = apply_basic_filters(selected)
    bits = (1 << p.universe_size) - 1 if p.hard_mask is None else p.hard_mask
    for j, mask in enumerate(p.masks):
        if answer.best.genome & (1 << j):
            bits &= mask
    expected = np.flatnonzero(mask_from_bitmap(bits))
    mismatch = int(not np.array_equal(oracle, expected))
    if mismatch or expected.size != answer.best.survivors:
        raise AssertionError('ticket membership differs from independent original NumPy rule executor')
    return {
        'method':method, 'seed':seed,'evaluations':answer.evaluations,
        'elapsed_seconds':elapsed,
        'best_genome':answer.best.genome,'survivors':answer.best.survivors,
        'fitness':answer.best.fitness,'feasible':answer.best.feasible,
        'selected_rule_count':answer.best.rule_count,
        'selected_rule_names':list(answer.selected_rules),
        'best_trace':list(answer.best_trace),
        'stage_evaluations':answer.stage_evaluations,
        'independent_oracle_mismatch':mismatch,
        'candidate_sha256':hashlib.sha256(oracle.astype('<i4').tobytes()).hexdigest(),
    }


def _summarize(trials):
    return [
        {
            'method':m, 'trials':len(rows),
            'feasible_trials':sum(v['feasible'] for v in rows),
            'median_fitness':statistics.median(v['fitness'] for v in rows),
            'median_survivors':statistics.median(v['survivors'] for v in rows),
            'median_elapsed_seconds':statistics.median(v['elapsed_seconds'] for v in rows),
            'min_fitness':min(v['fitness'] for v in rows),
            'max_fitness':max(v['fitness'] for v in rows),
        }
        for m in METHODS
        if (rows := [v for v in trials if v['method'] == m])
    ]


def run_experiment(*, seeds=(0, 1, 2, 3, 4, 5, 6, 7),
                   evaluations=300, include_infeasible=True):
    seeds = tuple(seeds)
    if not seeds or len(set(seeds)) != len(seeds) or any(type(x) is not int or x < 0 for x in seeds):
        raise ValueError('seeds must be a nonempty distinct tuple of nonnegative integers')
    if type(evaluations) is not int or not (1 <= evaluations <= 100_000):
        raise ValueError('evaluations must be in 1..100000')
    cases, masks, minimum_all, cold_seconds, inventory_sha = _build_problem()
    p = SearchProblem(masks=masks, rule_names=tuple(n for n,_ in cases),
                      universe_size=100000,target=36_000,min_survivors=28_000,
                      max_survivors=42_000,min_active=2)
    scenarios = {}
    for name, problem in [
        ('feasible', p),
        *(([('infeasible_100',SearchProblem(masks=masks,rule_names=p.rule_names,
                                            universe_size=100000,target=100,
                                            min_survivors=1,max_survivors=100,
                                            min_active=2))]) if include_infeasible else []),
    ]:
        trials = []
        for seed in seeds:
            # Change method order across trials to reduce systematic CPU/cache drift.
            methods = METHODS[seed % len(METHODS):]+METHODS[:seed % len(METHODS)]
            for m in methods:
                trials.append(_trial(m,problem,cases,seed,evaluations))
        scenarios[name] = {
            'target_tickets':problem.target,
            'allowed_tickets':[problem.min_survivors,problem.max_survivors],
            'best_possible_survivors':minimum_all,
            'proven_infeasible':minimum_all > problem.max_survivors,
            'independent_oracle_mismatches':sum(t['independent_oracle_mismatch'] for t in trials),
            'trials':trials,'summary':_summarize(trials),
        }
    return {
        'schema':'pl5-v3715-ga-cs-cost-matched-1','domain':100_000,
        'source_rule_pool':'benchmark_high_throughput_v3714._rules',
        'rule_count':len(cases),'rule_names':[name for name,_ in cases],
        'inventory_sha256':inventory_sha,
        'precompile_seconds':cold_seconds,
        'logical_rule_bitmap_bytes':len(cases)*BYTES_PER_MASK,
        'protocol':{
            'methods':list(METHODS), 'seeds':list(seeds),
            'evaluations_per_method_per_seed':evaluations,
            'ga_switch_ratio':.30,'population_size':12,
            'fitness_uses_draw_labels':False,
            'fitness':'feasibility; log distance to 36000 retained and 0.014 penalty per enabled rule',
            'historical_real_draws_used':False,
            'objective_cost_metric':'evaluations (repeated calls count too)',
            'real_wall_clock_metric':'perf_counter_ns, per-method, precompiled index cost separately logged',
            'allocation':'two preset scenarios: 28000-42000 admissible and 1-100 impossible',
        },
        'scenarios':scenarios,
        'environment':{
            'platform':platform.platform(),'python':platform.python_version(),
            'numpy':np.__version__,'cpu_count':os.cpu_count(),
        },
        'limitations':[
            'Uses all 100000 PL5 candidates and existing rule definitions, but no verified real draw dataset',
            'Fitness is a predefined engineering compression target, not empirical head-prize coverage',
            'The 100-ticket scenario is mathematically infeasible with these 20 frozen rules',
            'GA+CS is heuristic and has no mathematical optimality guarantee',
            'Different methods can use different Python overhead despite equal fitness-call counts',
            'Single-host measurements do not imply the same result on Windows',
            'No lottery advantage is established and production selection is disabled',
        ],
        'production_enabled':False,
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--seeds',type=int,nargs='+',default=list(range(8)))
    parser.add_argument('--evaluations',type=int,default=300)
    parser.add_argument('--skip-infeasible',action='store_true')
    args=parser.parse_args()
    result=run_experiment(seeds=tuple(args.seeds),evaluations=args.evaluations,
                          include_infeasible=not args.skip_infeasible)
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive create prevents accidentally overwriting prior evidence.
    with out.open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
        f.write('\n')
    print(json.dumps({'result_path':str(out),
                      'trials_by_scenario':{k:len(v['trials']) for k,v in result['scenarios'].items()},
                      'oracle_mismatches':sum(v['independent_oracle_mismatches'] for v in result['scenarios'].values()),
                      'production_enabled':False},ensure_ascii=False))


if __name__=='__main__':
    main()
