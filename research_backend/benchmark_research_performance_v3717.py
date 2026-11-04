"""V3.7.17: end-to-end comparative PL5 research workflow benchmark.

The historical input is the bundled SYNTHETIC sample, not authenticated lottery
records. Both paths compute the complete 100k universe before target lookup.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import time
from pathlib import Path

import numpy as np

from benchmark_bitmap_workflows_v3716 import _read_history, _context
from benchmark_high_throughput_v3714 import _rules
from pailie5.basic_filter_catalog_v3716 import BasicFilterCatalog
from pailie5.pattern_rules import Configuration, filter_next
from pailie5.probability_ranker import rolling_rank_backtest
from pailie5.sculpting import rolling_sculpt_backtest


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def _contextual_pattern(history: list[str], cfg: Configuration, optimized: bool) -> dict:
    all_rows=[]
    for t in range(len(history)-3,len(history)):
        result=filter_next(history[:t],cfg,optimize_context=optimized)
        all_rows.append({
            'period':t,
            'kept_sha':hashlib.sha256(result.kept.astype('<i4').tobytes()).hexdigest(),
            'removed_sha':hashlib.sha256(result.removed.astype('<i4').tobytes()).hexdigest(),
            'audit':result.summary(),
            'rules':[r.as_dict() for r in result.rules],
        })
    return {'periods':len(all_rows),'details':all_rows}


def _clock(action):
    start=time.perf_counter_ns()
    return (time.perf_counter_ns()-start)/1e6,action()


def _time(action):
    start=time.perf_counter_ns()
    result=action()
    return (time.perf_counter_ns()-start)/1e6,result


def _ctx_heavy():
    return Configuration(indicators=(
        'same_positions_prev','digit_overlap_prev','sum_delta_prev',
        'span_delta_prev','lastdigit_delta_prev','same_parity_positions_prev',
        'digit_5','sum'),
        transforms=('raw','mod2','mod3','mod5','mod10'),
        patterns=('constant','strict_up','strict_down','arithmetic','period2','zigzag'),
        windows=(3,4,5),lookback=12,max_rules=80,mode='recurrence')


def run_benchmark(*,repeats:int=8,seed:int=3717) -> dict:
    if type(repeats) is not int or not 1 <= repeats <= 50:
        raise ValueError('repeats must be an integer in range 1..50')
    if type(seed) is not int or seed < 0:
        raise ValueError('seed must be a nonnegative integer')
    history,history_sha=_read_history()
    cfg=_context()
    # Catalog is passed to BOTH baseline and fast path: no bitmap advantage is
    # being claimed from the target-only optimization itself.
    basic=[x[1] for x in _rules()[:6]]
    catalog=BasicFilterCatalog([x[1] for x in _rules()])
    scenarios={
        'rolling_rank':(
            lambda:rolling_rank_backtest(history,cfg,warmup=65,max_periods=5,
                                         top_k=1000,basic_constraints=basic,
                                         basic_catalog=catalog),
            lambda:rolling_rank_backtest(history,cfg,warmup=65,max_periods=5,
                                         top_k=1000,basic_constraints=basic,
                                         basic_catalog=catalog,target_only=True),
        ),
        'rolling_sculpt':(
            lambda:rolling_sculpt_backtest(history,cfg,warmup=65,max_periods=5,
                                           k=100,basic=basic,basic_catalog=catalog),
            lambda:rolling_sculpt_backtest(history,cfg,warmup=65,max_periods=5,
                                           k=100,basic=basic,basic_catalog=catalog,
                                           target_only=True),
        ),
        'contextual_pattern':(
            lambda:_contextual_pattern(history,_ctx_heavy(),False),
            lambda:_contextual_pattern(history,_ctx_heavy(),True),
        ),
    }
    results={}
    for j,(name,(legacy,fast)) in enumerate(scenarios.items()):
        # Start with both warmups, verify complete report, then alternate timing.
        _,expected=_time(legacy)
        _,fresh=_time(fast)
        if expected!=fresh:
            raise AssertionError(f'legacy vs optimized workflow mismatch: {name}')
        legacy_digest=_digest(expected)
        fast_digest=_digest(fresh)
        old_ms=[];new_ms=[]
        for trial in range(repeats):
            if (trial+j+seed)%2:
                a,x=_time(legacy)
                b,y=_time(fast)
            else:
                b,y=_time(fast)
                a,x=_time(legacy)
            if x!=y or x!=expected:
                raise AssertionError(f'optimized workflow mismatch at {name} trial={trial}')
            old_ms.append(a);new_ms.append(b)
        old_med=statistics.median(old_ms);new_med=statistics.median(new_ms)
        results[name]={
            'exact_same_result':True,
            'legacy_digest':legacy_digest,'fast_digest':fast_digest,
            'periods':expected['periods'],
            'timing_ms':{
                'legacy_runs':[round(v,5) for v in old_ms],
                'fast_runs':[round(v,5) for v in new_ms],
                'legacy_median':round(old_med,5),
                'fast_median':round(new_med,5),
                'legacy_p95':round(float(np.percentile(old_ms,95)),5),
                'fast_p95':round(float(np.percentile(new_ms,95)),5),
            },
            'speed_ratio':round(old_med/new_med,5),
        }
    old_sum=sum(v['timing_ms']['legacy_median'] for v in results.values())
    new_sum=sum(v['timing_ms']['fast_median'] for v in results.values())
    return {
        'schema':'pl5-v3717-end-to-end-1',
        'synthetic_history':True,'authenticated_lottery_data':False,
        'history_sha256':history_sha,'history_periods':len(history),
        'domain':100000,'seed':seed,'repeats':repeats,
        'workflows':results,'workflow_mismatches':0,
        'aggregate':{'sum_legacy_median_ms':round(old_sum,5),
                     'sum_fast_median_ms':round(new_sum,5),
                     'weighted_ratio':round(old_sum/new_sum,5)},
        'environment':{'python':platform.python_version(),
                       'numpy':np.__version__,'platform':platform.platform(),
                       'clock':'perf_counter_ns'},
        'limits':[
            'Input is synthetic_demo.csv and must never be presented as authenticated draw history.',
            'Comparison computes complete 100000-candidate rankings, not only the actual outcome.',
            'Warm process measurements exclude data-file loading and package startup.',
            'Relative speed depends on hardware, number of patterns, data and runtime.',
            'Legacy is default. Optimized target-only paths are opt-in.',
            'Neither code path demonstrates predictive lottery advantage.',
        ],
    }


def main():
    parser=argparse.ArgumentParser(description='PL5 V3.7.17 complete research benchmarks')
    parser.add_argument('--seed',type=int,default=3717)
    parser.add_argument('--repeats',type=int,default=8)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=run_benchmark(seed=args.seed,repeats=args.repeats)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v['speed_ratio'] for k,v in report['workflows'].items()}))

if __name__=='__main__':main()
