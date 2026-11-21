"""V3.7.16 end-to-end PL5 benchmark: unchanged legacy vs opt-in cached bitsets.

Runs real PL5 pattern discovery, full-universe ranking, and sculpting, using
bundled synthetic history (NOT authenticated real draw history). Both paths
share the same rules, history, and query sequences; no lottery advantage claimed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import statistics
import time
from pathlib import Path

import numpy as np

from benchmark_high_throughput_v3714 import _rules
from pailie5.basic_filters import combine_basic_and_pattern
from pailie5.basic_filter_catalog_v3716 import BasicFilterCatalog
from pailie5.pattern_rules import Configuration, filter_next
from pailie5.probability_ranker import rolling_rank_backtest
from pailie5.sculpting import rolling_sculpt_backtest


DATA_PATH = Path(__file__).parent / 'data' / 'synthetic_demo.csv'


def _context() -> Configuration:
    return Configuration(indicators=(
        'sum','span','odd_count','digit_5','same_positions_prev'),
        transforms=('raw',),
        patterns=('constant','strict_up','period2'),
        windows=(3,4), lookback=10, max_rules=25, min_keep=2500,
        max_total_remove=0.8)


def _read_history() -> tuple[list[str], str]:
    raw = DATA_PATH.read_bytes()
    with DATA_PATH.open(encoding='utf-8', newline='') as handle:
        rows=list(csv.DictReader(handle))
    history=[x['number'] for x in rows]
    if len(history)<65 or any(len(x)!=5 or not x.isascii() or not x.isdigit()
                              for x in history):
        raise ValueError('bundled research demo has malformed history')
    return history,hashlib.sha256(raw).hexdigest()


def _pattern_batch(history, config, rules, selections, catalog):
    """Research pipeline: history -> rule discovery -> intersections per subset."""
    outputs=[]
    for period in range(len(history)-3, len(history)):
        patterns=filter_next(history[:period],config)
        for chosen in selections:
            outputs.append(combine_basic_and_pattern(
                chosen,patterns.kept,basic_catalog=catalog))
    return outputs


def _compare(a,b):
    if isinstance(a,list):
        if len(a)!=len(b):
            raise AssertionError('intersection workflow produced a different number of experiments')
        for index,(x,y) in enumerate(zip(a,b)):
            if not np.array_equal(x,y):
                raise AssertionError(f'exact candidate mismatch at intersection job {index}')
        return {'exact':True,'units':len(a),'observed_items':sum(len(x) for x in a)}
    if a!=b:
        raise AssertionError('full forward research workflow report differs from legacy')
    return {'exact':True,'units':a['periods'],
            'observed_items':a.get('hits',a.get('top_k_hits'))}


def _measure(action):
    started=time.perf_counter_ns()
    result=action()
    return (time.perf_counter_ns()-started)/1e6,result


def _digest(result):
    if isinstance(result,list):
        h=hashlib.sha256()
        for arr in result:
            h.update(np.asarray(arr,dtype='<i4').tobytes())
            h.update(b'|')
        return h.hexdigest()
    return hashlib.sha256(json.dumps(result,sort_keys=True,ensure_ascii=False).encode('utf-8')).hexdigest()


def run_benchmark(*, repeats=4, seed=3716) -> dict:
    if type(repeats) is not int or not 1 <= repeats <= 60:
        raise ValueError('repeats must be integer in 1..60')
    if type(seed) is not int or seed<0:
        raise ValueError('seed must be a nonnegative integer')
    history,history_sha=_read_history()
    config=_context()
    names_and_rules=_rules()
    rules=[rule for _,rule in names_and_rules]
    if len(set(rules)) != len(rules):
        raise AssertionError('benchmark rule inventory cannot contain duplicated definitions')
    rng=np.random.default_rng(seed)
    selections=[[rules[int(j)] for j in rng.choice(len(rules),size=k,replace=False)]
                for k in (4,7,9,12)]
    workflows={
        'pattern_intersection':lambda c:_pattern_batch(history,config,rules,selections,c),
        'rolling_rank':lambda c:rolling_rank_backtest(
            history,config,warmup=65,max_periods=3,top_k=1000,
            basic_constraints=rules,basic_catalog=c),
        'rolling_sculpt':lambda c:rolling_sculpt_backtest(
            history,config,k=100,warmup=65,max_periods=3,
            basic=rules,basic_catalog=c),
    }
    results={}
    for name,workflow in workflows.items():
        catalog=BasicFilterCatalog(rules)
        cold_ms, cold_result = _measure(lambda:workflow(catalog))
        legacy_ms, legacy_result = _measure(lambda:workflow(None))
        verified=_compare(legacy_result,cold_result)
        lats_legacy=[legacy_ms]
        lats_cached=[]
        # The first (already verified) legacy pass is an oracle-only warmup,
        # not included in medians; warm all shared indicator tables before timing.
        for i in range(repeats):
            if (i+seed)%2:
                ms_a,a=_measure(lambda:workflow(None))
                ms_b,b=_measure(lambda:workflow(catalog))
            else:
                ms_b,b=_measure(lambda:workflow(catalog))
                ms_a,a=_measure(lambda:workflow(None))
            _compare(a,b)
            lats_legacy.append(ms_a)
            lats_cached.append(ms_b)
        lats_legacy=lats_legacy[1:]
        old_med=statistics.median(lats_legacy)
        new_med=statistics.median(lats_cached)
        results[name]={
            'equivalence':verified,
            'digest_sha256':_digest(legacy_result),
            'latency_ms':{
                'cold_bitmap':round(cold_ms,5),
                'oracle_warmup_not_in_medians':round(legacy_ms,5),
                'legacy_runs':[round(x,5) for x in lats_legacy],
                'warm_bitmap_runs':[round(x,5) for x in lats_cached],
                'legacy_median':round(old_med,5),
                'warm_bitmap_median':round(new_med,5),
            },
            'warm_speed_ratio':round(old_med/new_med,5) if new_med else None,
            'catalog_stats':catalog.stats(),
        }
    before=sum(x['latency_ms']['legacy_median'] for x in results.values())
    after=sum(x['latency_ms']['warm_bitmap_median'] for x in results.values())
    return {
        'schema':'pl5-v3716-end-to-end-1',
        'data_source':{'kind':'bundled_synthetic_demo','name':DATA_PATH.name,
                       'sha256':history_sha,'periods':len(history),
                       'authentic_draw_data':False},
        'configuration':{'pattern_indicators':list(config.indicators),
                         'windows':list(config.windows),'transforms':list(config.transforms),
                         'pattern_types':list(config.patterns)},
        'domain':100000,'rules':len(rules),'seed':seed,'repeats':repeats,
        'workflows':results,
        'aggregate':{'sum_legacy_medians_ms':round(before,5),
                     'sum_warm_bitmap_medians_ms':round(after,5),
                     'weighted_warm_ratio':round(before/after,5) if after else None},
        'python':platform.python_version(),'numpy':np.__version__,
        'platform':platform.platform(),
        'limits':[
            'This is an end-to-end execution comparison for actual PL5 research routines, not real authenticated draw history.',
            'Legacy defaults remain unchanged; only opt-in calls use cached exact bitmaps.',
            'Cache warmup and memory cost are reported; history-dependent patterns are recomputed at each period.',
            'The work may be dominated by pattern detection and full-universe ranking, obscuring bitmap microbenchmark gains.',
            'These rankings and compressed sets are not calibrated lottery-win predictions.',
        ]
    }


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument('--repeats',type=int,default=4)
    p.add_argument('--seed',type=int,default=3716)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    report=run_benchmark(repeats=args.repeats,seed=args.seed)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'workflows':list(report['workflows']),'aggregate':report['aggregate']},ensure_ascii=False))


if __name__=='__main__':
    main()
