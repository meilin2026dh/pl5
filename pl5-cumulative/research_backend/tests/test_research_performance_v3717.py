"""Benchmark schema + exact existing full-workflow audit, no unstable speed minimum."""
from benchmark_research_performance_v3717 import run_benchmark


def test_benchmark_runs_same_workflows_with_identical_reports():
    result=run_benchmark(repeats=1,seed=3717)
    assert result['schema']=='pl5-v3717-end-to-end-1'
    assert result['synthetic_history'] is True
    assert result['domain']==100000
    assert set(result['workflows']) == {'rolling_rank','rolling_sculpt','contextual_pattern'}
    for row in result['workflows'].values():
        assert row['exact_same_result'] is True
        assert row['legacy_digest']==row['fast_digest']
        assert row['timing_ms']['legacy_median'] > 0
        assert row['timing_ms']['fast_median'] > 0
        assert len(row['timing_ms']['legacy_runs'])==1
        assert len(row['timing_ms']['fast_runs'])==1
    assert result['workflow_mismatches']==0
