import pytest
from pailie5.primitive_study_v377 import make_truth, split_truth, run_trial, protocol


def test_predefined_tasks_and_split_are_ordered_and_disjoint():
    for case in ('latent_quadratic','latent_cubic','latent_mixed','coupled_product','coupled_threshold','iid_random'):
        target = make_truth(case, 712)
        assert target.shape == (10,10)
        train, unseen = split_truth(target, 713)
        assert len(train.rows) == 70 and len(unseen.rows) == 30
        assert set(train.pairs).isdisjoint(unseen.pairs)


def test_recovery_and_rejection_are_explicit():
    positive = run_trial('latent_quadratic', 712, 250)
    assert positive['model_status'] == 'identified'
    assert positive['latent_holdout_accuracy'] == 1
    assert positive['baseline_holdout_count'] == 30
    negative = run_trial('iid_random', 712, 250)
    assert negative['model_status'] == 'rejected_inconsistent'
    assert negative['latent_holdout_accuracy'] is None


def test_protocol_is_bounded_and_reproducible():
    d = protocol((712,713), 250)
    assert d['max_baseline_evaluations_per_trial'] == 250
    assert d['test_pairs_per_trial'] == 30
    assert d['production_enabled'] is False
    assert run_trial('latent_cubic',712,250) == run_trial('latent_cubic',712,250)


def test_bad_budget_rejected():
    with pytest.raises(ValueError):
        run_trial('latent_cubic',712,0)


def test_serialized_preregistered_protocol_is_accepted():
    import json
    from pailie5.primitive_study_v377 import run_predeclared
    saved = json.loads(json.dumps(protocol((712,),100)))
    report = run_predeclared(saved)
    assert report['summary']['trials'] == 6
    assert report['summary']['structured_tasks'] == 3


def test_structured_case_seed_changes_the_target_not_only_split():
    import numpy as np
    for case in ('latent_quadratic','latent_cubic','latent_mixed'):
        assert not np.array_equal(make_truth(case,712),make_truth(case,713)), case


def test_cli_research_output_is_append_safe(tmp_path):
    import json, subprocess, sys
    from pathlib import Path
    program = Path(__file__).resolve().parents[1] / 'research_primitive_v377.py'
    plan = tmp_path / 'protocol.json'
    plan.write_text(json.dumps(protocol((712,),100)), encoding='utf8')
    output = tmp_path / 'result.json'
    args = [sys.executable,str(program),'--protocol',str(plan),'--output',str(output)]
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text())['summary']['trials'] == 6
    # Research evidence is immutable by default; no accidental re-run overwrite.
    assert subprocess.run(args, capture_output=True, text=True, timeout=30).returncode != 0
