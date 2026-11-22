"""Benchmark correctness and schema, not host-specific speed thresholds."""
from benchmark_high_throughput_v3714 import run_benchmark


def test_benchmark_audits_every_query_and_cost_dimensions():
    result=run_benchmark(repeats=1, seed=1414)
    assert result['domain']==100_000
    assert result['n_static_rules']==20
    assert result['mismatch_count']==0
    assert result['tested_queries'] >= 12
    assert result['latency_seconds']['bitmap_warm_median'] >= 0
    assert result['latency_seconds']['legacy_numpy_median'] >= 0
    assert result['latency_seconds']['bitmap_cold_compile'] >= 0
    assert result['memory_bytes']['logical_bitmap_storage'] == 20*12500
