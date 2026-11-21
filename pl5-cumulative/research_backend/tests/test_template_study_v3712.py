"""Predeclared experiment, fixed seeds, scope and source-cost ledger."""
import pytest
from pailie5.template_study_v3712 import protocol, run_study


def test_preregistration_is_immutable_and_not_tuned_to_holdout():
    p=protocol((9811,))
    assert p['target_candidate_feature_slots_each_arm']==16
    assert p['source_cost_included_in_ledger'] is True
    assert p['full_pipeline_compute_matched'] is False
    with pytest.raises(ValueError,match='protocol'):
        run_study({**p,'target_candidate_feature_slots_each_arm':17})


def test_protocol_has_positive_and_negative_controls_and_replay():
    p=protocol((9811,))
    first=run_study(p)
    second=run_study(p)
    assert first==second
    assert first['summary']['target_trials']==6
    assert first['summary']['source_feature_tables_examined']>0
    assert first['summary']['target_feature_slots_each_arm']==16
    assert all(row['fit_used_target_holdout_labels'] is False for row in first['trials'])
    assert all(row['source_informed']['feature_slots']==row['canonical']['feature_slots']==16
               for row in first['trials'])
    assert first['summary']['production_enabled'] is False
    assert first['summary']['real_lottery_advantage_established'] is False


def test_alternative_family_success_and_negative_transfer_are_reported():
    result=run_study(protocol((9811,)))
    by_case={r['case']:r for r in result['trials']}
    for case in ('swapped_xor','swapped_abs','lifted_gcd'):
        assert by_case[case]['source_informed']['heldout_errors']==0
    assert by_case['canonical_early']['canonical']['heldout_errors']==0
    assert by_case['canonical_early']['source_informed']['status']!='provisional_identified'
    assert by_case['iid_random']['source_informed']['status']!='provisional_identified'


def test_familywise_monitor_has_null_and_observed_shift_controls():
    out=run_study(protocol((9811,)))
    shift=out['shift_controls']
    assert shift['prespecified_windows_per_schedule']==4
    assert shift['null_schedules']>=128
    assert shift['empirical_null_fpr']<0.06
    assert shift['shift_alarm'] is True
    assert shift['fixed_family_alpha']==0.01
    assert shift['drift_is_observed_not_predicted'] is True
