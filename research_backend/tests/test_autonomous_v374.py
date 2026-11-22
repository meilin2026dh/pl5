"""V3.7.4 autonomous research: behavior-based and leakage-control tests."""
from __future__ import annotations
import json
from pathlib import Path
import pytest

from pailie5.ablation_benchmark_v373 import truth_table, split_table
from pailie5.autonomous_v374 import select_warm_starts, run_cycles, choose_next_task


def training(case='shifted_bilinear', seed=37401):
    return split_table(truth_table(case, seed), seed, case)[0]


def test_selector_uses_training_only_and_returns_valid_unique_candidates():
    bank = (("binary", "add", ("a",), ("b",)),
            ("binary", "mul", ("a",), ("b",)),
            ("binary", "add", ("a",), ("b",)))
    selected, count = select_warm_starts(training(), bank, max_items=3)
    assert len(selected) == len(set(selected)) <= 3
    assert count >= len(selected)
    assert all(isinstance(x, tuple) for x in selected)


def test_selector_rejects_unsafe_expression():
    with pytest.raises(ValueError):
        select_warm_starts(training(), (("eval", "payload"),))


def test_run_cycles_pre_registers_and_is_resumable(tmp_path):
    output = tmp_path / 'autonomy'
    first = run_cycles(output, cycles=1, budget=110, seed=37410)
    assert first['completed_cycles'] == 1
    protocol = json.loads((output/'cycles'/'00001'/'protocol.json').read_text())
    assert protocol['test_labels_hidden_from_fit'] is True
    assert protocol['research_only'] is True
    assert (output/'cycles'/'00001'/'result.json').exists()
    original = (output/'cycles'/'00001'/'result.json').read_bytes()
    again = run_cycles(output, cycles=1, budget=110, seed=37410)
    assert again['completed_cycles'] == 2
    assert (output/'cycles'/'00001'/'result.json').read_bytes() == original
    next_protocol = json.loads((output/'cycles'/'00002'/'protocol.json').read_text())
    assert next_protocol['seed'] != protocol['seed']
    assert first['next_hypothesis'] != ''
    assert again['production_enabled'] is False


def test_prevents_parameter_drift_on_resume(tmp_path):
    output = tmp_path / 'autonomy'
    run_cycles(output, cycles=1, budget=105, seed=23)
    with pytest.raises(ValueError, match='locked'):
        run_cycles(output, cycles=1, budget=106, seed=23)


def test_periodic_iid_control_and_adaptive_diagnoses():
    state = {'completed_cycles': 3, 'history': [{'case': 'shifted_bilinear', 'weakness': 0.1}]}
    assert choose_next_task(state, control_every=4) == 'iid_a'
    issues = {'completed_cycles': 1, 'history': [{'case': 'gcd_offsets', 'weakness': 0.9}]}
    assert choose_next_task(issues, control_every=4) == 'gcd_offsets'


def test_model_evaluated_only_after_all_arms_frozen(tmp_path):
    output = tmp_path / 'autonomy'
    run_cycles(output, cycles=1, budget=110, seed=123)
    path = output/'cycles'/'00001'
    result = json.loads((path/'result.json').read_text())
    for arm in result['arms']:
        assert arm['frozen_before_holdout'] is True
        assert arm['training_evaluations'] + arm['selector_evaluations'] <= 110
        assert arm['holdout']['overlapping_pairs'] == 0
    assert len(result['arms']) == 4
    assert result['status'] in ('exploratory_only', 'negative_control')


def test_concurrent_run_is_refused_without_corrupting_workspace(tmp_path):
    output = tmp_path/'autonomy'
    output.mkdir()
    (output/'.run.lock').write_text('another worker', encoding='utf8')
    with pytest.raises(RuntimeError, match='already running'):
        run_cycles(output, cycles=1, budget=110, seed=1)
    assert (output/'.run.lock').exists()


def test_cli_runs_real_cycle(tmp_path):
    import subprocess, sys
    cli = Path(__file__).resolve().parents[1]/'research_autonomous_v374.py'
    p = subprocess.run([sys.executable,str(cli), '--output',str(tmp_path/'runs'),
                        '--cycles','1','--budget','100','--seed','204'],
                       text=True,capture_output=True,timeout=50)
    assert p.returncode == 0, p.stderr
    summary = json.loads(p.stdout)
    assert summary['completed_cycles'] == 1
    assert summary['production_enabled'] is False
