"""RED-first research protocol checks for true independent target tasks."""
import pytest
from pailie5.transfer_study_v3711 import protocol, run_study


def test_protocol_is_frozen_and_source_tasks_disjoint_by_seed():
    p=protocol((9541,))
    assert p['feature_budget_each_arm']==8
    assert p['source_seeds'] != p['target_seeds']
    assert p['production_enabled'] is False
    with pytest.raises(ValueError,match='preregistration'):
        run_study({**p,'feature_budget_each_arm':25})


def test_one_seed_study_has_positive_control_noise_and_drift_cases():
    out=run_study(protocol((9541,)))
    assert out['summary']['trials']==6
    assert out['summary']['structured_tasks']==3
    assert out['summary']['negative_controls']==1
    assert out['summary']['noise_cases']==1
    assert out['summary']['drift_cases']==1
    assert len(out['source_bank']['source_training_sha256'])==3
    assert all(t['feature_evaluations_transfer']==8 for t in out['trials'])
    assert all(t['feature_evaluations_baseline']==8 for t in out['trials'])
    assert out['summary']['production_enabled'] is False
    assert out['summary']['real_lottery_advantage_established'] is False


def test_source_target_provenance_and_deterministic_replay():
    p=protocol((9541,))
    a=run_study(p)
    b=run_study(p)
    assert a == b
    source=set(a['source_bank']['source_training_sha256'])
    assert all(t['train_sha256'] not in source for t in a['trials'])
    assert all(t['fit_access_to_target_holdout_labels'] is False for t in a['trials'])
    assert all(t['frozen_before_target_holdout'] is True for t in a['trials'])
    assert all(t['source_bank_id']==a['source_bank']['bank_id'] for t in a['trials'])
    assert a['summary']['source_training_cost_included_in_budget'] is False


def test_positive_target_improvement_relative_to_fixed_grammar_order():
    a=run_study(protocol((9541,)))
    structured=[t for t in a['trials'] if t['case'] in ('xor_shift','abs_scaled','gcd_shift')]
    assert all(t['transfer_status']=='provisional_identified' for t in structured)
    assert all(t['transfer_holdout_errors']==0 for t in structured)
    assert all(t['baseline_status']!='provisional_identified' for t in structured)
    assert a['summary']['compute_matched_full_pipeline'] is False
