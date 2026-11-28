"""INTERNAL/AI_AUTHORED: fixed-workload count-only benchmark.
Hypothesis: closed evaluation including moment extraction reduces wall time
versus cached-table subset DP and cached-table partition inversion.
No historical records; no candidate identities generated. Seven rotated
warm batches per method, identical inputs, exact result checks, no timing gate.
Shared coefficient table construction and imports excluded, inversion cache
warmed once. Results describe this environment only; no cold-start claim.
"""
import hashlib
import json
import platform
from statistics import median
from time import perf_counter_ns
import nonuniform_quotient_count_v3814 as dp
import moment_quotient_count_v3815 as mo
from closed_quotient_count_v3816 import closed


def run():
    table = dp.table()
    original_dp, original_mo = dp.table, mo.table
    dp.table = mo.table = lambda: table
    methods = (('subset_dp_cached', dp.counts), ('inversion_cached', mo.counts),
               ('closed_with_moments', lambda f: closed(mo.moments(f))))
    cases = {'sum10': [(10,), (5,5), (2,2,2,2,2), (1,2,3,4), (1,)*10],
             'abstract_large': [(2,)*32, tuple(range(1,33)), (1,2,3,4)*16]}
    result = {}
    try:
        for name, inputs in cases.items():
            expected = [dp.counts(f) for f in inputs]
            for _, fn in methods:
                assert [fn(f) for f in inputs] == expected
            times = {label: [] for label, _ in methods}
            for repeat in range(7):
                for offset in range(3):
                    label, fn = methods[(repeat+offset)%3]
                    start = perf_counter_ns()
                    actual = [fn(f) for f in inputs]
                    elapsed = perf_counter_ns()-start
                    assert actual == expected
                    times[label].append(elapsed)
            result[name] = {'inputs': inputs, 'histogram_sha256': hashlib.sha256(json.dumps(expected,separators=(',',':')).encode()).hexdigest(),
                            'batch_ns': times, 'median_ns': {k: median(v) for k,v in times.items()}}
    finally:
        dp.table, mo.table = original_dp, original_mo
    return {'source':'INTERNAL/AI_AUTHORED','python':platform.python_version(), 'system':platform.system(), 'machine':platform.machine(), 'results':result,
            'limitations':['warm count-only workload','shared table setup excluded','no candidate enumeration or historical coverage','no cross-platform timing ranking']}


if __name__ == '__main__':
    print(json.dumps(run(),sort_keys=True))
