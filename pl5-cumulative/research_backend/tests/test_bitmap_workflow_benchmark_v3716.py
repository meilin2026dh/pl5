"""V3.7.16 reproducible end-to-end workflow benchmark contract."""
from benchmark_bitmap_workflows_v3716 import run_benchmark


def test_all_three_real_research_workflows_have_exact_results():
    outcome=run_benchmark(repeats=1,seed=3716)
    assert outcome['schema']=='pl5-v3716-end-to-end-1'
    assert outcome['data_source']['kind']=='bundled_synthetic_demo'
    assert outcome['domain']==100000
    assert outcome['rules']==20
    assert set(outcome['workflows'])=={'pattern_intersection','rolling_rank','rolling_sculpt'}
    for entry in outcome['workflows'].values():
        assert entry['equivalence']['exact'] is True
        assert entry['latency_ms']['cold_bitmap']>=0
        assert len(entry['latency_ms']['legacy_runs'])==1
        assert len(entry['latency_ms']['warm_bitmap_runs'])==1
        assert entry['warm_speed_ratio']>0
