"""V3.7.14 reproducible performance and exactness experiment.

Compare against the *real* existing NumPy BasicConstraint executor. Times are
host-specific and DO NOT reflect prediction success or prove universal speed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import time
from pathlib import Path

import numpy as np

from pailie5.basic_filters import BasicConstraint, apply_basic_filters
from pailie5.high_throughput_v3714 import DOMAIN, ExactFilterEngine
from pailie5.pattern_rules import indicator_table


def _rules() -> list[tuple[str, BasicConstraint]]:
    """20 deterministic static rules; no access to future data or labels."""
    base = [
        ('sum_range',BasicConstraint('sum', minimum=8,maximum=37)),
        ('span_range',BasicConstraint('span',minimum=2,maximum=9)),
        ('odd_count',BasicConstraint('odd_count',minimum=1,maximum=4)),
        ('unique_count',BasicConstraint('unique_count',minimum=2,maximum=5)),
        ('high_count',BasicConstraint('high_count',minimum=1,maximum=4)),
    ]
    for i in range(1,6):
        base.append((f'position_{i}_not9', BasicConstraint(f'digit_{i}',denied=(9,))))
    for i in range(1,6):
        base.append((f'position_{i}_not0', BasicConstraint(f'digit_{i}',denied=(0,))))
    base.extend([
        ('max_repeats',BasicConstraint('max_frequency',maximum=3)),
        ('head_sum',BasicConstraint('head_sum', minimum=2,maximum=16)),
        ('tail_sum',BasicConstraint('tail_sum', minimum=2,maximum=16)),
        ('first_last_gap',BasicConstraint('first_last_gap',maximum=8)),
        ('adjacent_equal',BasicConstraint('adjacent_equal',maximum=2)),
    ])
    assert len(base)==20
    return base


def _clock(fn) -> tuple[int,np.ndarray]:
    start = time.perf_counter_ns()
    result = fn()
    return time.perf_counter_ns()-start, result


def _percentile(values: list[int], pct: float) -> float:
    return float(np.percentile(np.asarray(values,dtype=float),pct)/1e9)


def run_benchmark(*, repeats:int=8, seed:int=3714) -> dict:
    if type(repeats) is not int or not 1 <= repeats <= 1000:
        raise ValueError('repeats must be integer in 1..1000')
    # Both pipelines reuse the same precomputed indicator arrays; this cost is
    # separately attributable to the shared PL5 engine, not to the bitmap.
    indicator_table()
    cases=_rules()
    names=[name for name,_ in cases]
    rules=dict(cases)
    e=ExactFilterEngine()
    for name, rule in cases:
        e.add_basic(name,rule)

    # Cold compilation of all cached rules, done once. This is intentionally
    # reported separately from the repeatedly queried warm cache.
    cold_begin=time.perf_counter_ns()
    all_first=e.evaluate(all_of=names)
    cold_elapsed=(time.perf_counter_ns()-cold_begin)/1e9
    naive_first=apply_basic_filters([rule for _,rule in cases])
    if not np.array_equal(all_first,naive_first):
        raise AssertionError('cold conjunction differs from legacy NumPy oracle')

    rng=np.random.default_rng(seed)
    # Candidate subsets are fixed by seed; include a full 20-rule conjunction.
    query_names=[]
    for width in (4,8,12,20):
        for _ in range(5):
            q=tuple(sorted(rng.choice(names,size=width,replace=False).tolist()))
            query_names.append(q)

    lats_numpy: list[int]=[]
    lats_bitmap: list[int]=[]
    checks=0
    counts=[]
    digests=[]
    # Alternate execution order to reduce simple temporal drift bias.
    for trial in range(repeats):
        for j,q in enumerate(query_names):
            if (trial+j)%2==0:
                t_old,old=_clock(lambda:apply_basic_filters([rules[n] for n in q]))
                t_new,new=_clock(lambda:e.evaluate(all_of=q))
            else:
                t_new,new=_clock(lambda:e.evaluate(all_of=q))
                t_old,old=_clock(lambda:apply_basic_filters([rules[n] for n in q]))
            if not np.array_equal(old,new):
                raise AssertionError(f'filter mismatch at trial={trial} query={q}')
            checks+=1
            lats_numpy.append(t_old)
            lats_bitmap.append(t_new)
            if trial==0:
                counts.append({'rules':len(q),'remaining':int(new.size)})
                digests.append(hashlib.sha256(new.astype('<i4').tobytes()).hexdigest())

    # Complete index pass with one rule replaced, without rebuilding others.
    replacement=BasicConstraint('digit_1',minimum=3,maximum=8)
    reconfig_start=time.perf_counter_ns()
    e.add_basic(names[5],replacement,replace=True)
    changed=e.evaluate(all_of=names)
    update_elapsed=(time.perf_counter_ns()-reconfig_start)/1e9
    expected=apply_basic_filters([replacement if n==names[5] else r for n,r in cases])
    if not np.array_equal(changed,expected):
        raise AssertionError('incremental replacement differs from full legacy recomputation')

    stats=e.stats()
    med_old=_percentile(lats_numpy,50)
    med_new=_percentile(lats_bitmap,50)
    result={
        'schema':'PL5-V3.7.14-exact-bitset-benchmark-1',
        'benchmark_version':'3.7.14',
        'domain':DOMAIN,'n_static_rules':len(cases),
        'seed':seed,'repeat_count':repeats,'queries_per_repeat':len(query_names),
        'tested_queries':checks,'mismatch_count':0,
        'latency_seconds':{
            'numpy_indicator_table_warm':True,
            'bitmap_cold_compile':cold_elapsed,
            'legacy_numpy_median':med_old,
            'legacy_numpy_p95':_percentile(lats_numpy,95),
            'bitmap_warm_median':med_new,
            'bitmap_warm_p95':_percentile(lats_bitmap,95),
            'bitmap_single_rule_replacement':update_elapsed,
            'warm_speedup_median':round(med_old/med_new,4) if med_new else None,
        },
        'memory_bytes':{
            'logical_bitmap_storage':stats['cached_bytes'],
            'python_integer_allocations':stats['cached_python_bytes'],
        },
        'compiled_rules':stats['cached_rules'],
        'build_count':stats['compilations'],
        'query_results_first_repeat':counts,
        'query_hashes_first_repeat':digests,
        'environment':{
            'python':platform.python_version(),
            'numpy':np.__version__,
            'platform':platform.platform(),
            'processor':platform.processor(),
            'cpu_count':os.cpu_count(),
            'clock':'perf_counter_ns',
        },
        'limits':[
            'cold compilation includes a 100000-element mask for every static rule',
            'warm querying reuses cached rules whereas the legacy oracle recomputes them',
            'only 20 predefined static rules; deferred expensive calls measured by unit test, not this benchmark',
            'performance varies by hardware, rule selectivity, and query reuse',
            'this filter engine does not confer any lottery predictive advantage',
        ],
    }
    return result


def main() -> None:
    ap=argparse.ArgumentParser(description='Compare exact bitmap PL5 filtering with existing NumPy executor')
    ap.add_argument('--output',default='docs/v3714/benchmark.json')
    ap.add_argument('--repeats',type=int,default=8)
    ap.add_argument('--seed',type=int,default=3714)
    args=ap.parse_args()
    result=run_benchmark(repeats=args.repeats,seed=args.seed)
    dest=Path(args.output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'path':str(dest),'queries':result['tested_queries'],
                      'mismatches':result['mismatch_count'],
                      'warm_speedup':result['latency_seconds']['warm_speedup_median']},ensure_ascii=False))

if __name__=='__main__':
    main()
