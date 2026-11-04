"""V3.7.11 RED-first tests: transfer, diagnosis, drift, controlled comparisons."""
from dataclasses import replace
import numpy as np
import pytest

from pailie5.structure_search_v372 import CellDataset
from pailie5.primitive_study_v377 import split_truth
from pailie5.generated_study_v3710 import challenge_data
from pailie5.cross_task_v3711 import (
    TransferConfig, certify_transfer_bank, fit_budgeted_transfer,
    diagnose_training_noise, detect_labeled_shift,
)


def _pair(case, seed):
    return split_truth(challenge_data(case, seed), seed + 17)


def _bank():
    sources=tuple(_pair(case, 9101) for case in ('xor_shift','abs_scaled','gcd_shift'))
    return certify_transfer_bank(sources)


def test_bank_is_certified_from_independent_source_holdouts_only():
    bank=_bank()
    assert len(bank.specs)==3
    assert len(bank.source_training_sha256)==3
    assert len(bank.source_holdout_sha256)==3
    assert all(b in bank.specs for b in (('inc','xor','square'), ('inc','gcd','inc')))
    assert bank.to_dict()['production_enabled'] is False
    assert bank.to_dict()['real_lottery_advantage_established'] is False


def test_source_that_fails_source_holdout_cannot_enter_bank():
    train,held=_pair('xor_shift',9101)
    a,b,y=held.rows[0]
    corrupted=CellDataset(tuple((x,z,(v+1)%10 if (x,z)==(a,b) else v) for x,z,v in held.rows))
    with pytest.raises(ValueError,match='source validation'):
        certify_transfer_bank(((train,corrupted),))


def test_target_cannot_be_reused_as_source_training():
    bank=_bank()
    with pytest.raises(ValueError,match='source'):
        fit_budgeted_transfer(_pair('xor_shift',9101)[0],bank,TransferConfig(max_features=8))


def test_equal_fixed_feature_budget_works_on_new_seed_and_transfer_helps():
    bank=_bank()
    train,held=_pair('xor_shift',9202)
    cfg=TransferConfig(max_features=8)
    transferred=fit_budgeted_transfer(train,bank,cfg)
    baseline=fit_budgeted_transfer(train,None,cfg)
    assert transferred.features_checked==baseline.features_checked==8
    assert transferred.status=='provisional_identified',transferred.to_dict()
    assert all(transferred.predict(a,b)==y for a,b,y in held.rows)
    assert baseline.status!='provisional_identified'
    assert transferred.to_dict()['scope']=='searched candidate subset only'


def test_holdout_labels_never_enter_target_fit():
    bank=_bank()
    train,held=_pair('xor_shift',9202)
    fit=fit_budgeted_transfer(train,bank,TransferConfig(max_features=8))
    bad=CellDataset(tuple((a,b,(y+1)%10) for a,b,y in held.rows))
    # The already-frozen fit is unchanged. Only evaluation differs.
    from pailie5.cross_task_v3711 import evaluate_provisional
    assert evaluate_provisional(fit,held)['errors']==0
    assert evaluate_provisional(fit,bad)['errors']==len(bad.rows)
    with pytest.raises(ValueError,match='overlap'):
        evaluate_provisional(fit,train)


def test_detects_single_label_corruption_but_does_not_auto_promote():
    bank=_bank()
    train,_=_pair('xor_shift',9202)
    edited=list(train.rows)
    a,b,y=edited[0]
    edited[0]=(a,b,(y+1)%10)
    bad=CellDataset(tuple(edited))
    report=diagnose_training_noise(bad,bank,TransferConfig(max_features=8))
    assert report['status']=='single_label_suspected',report
    assert report['suspect_pair']==(a,b)
    assert report['observed_digit']==(y+1)%10
    assert report['suggested_digit']==y
    assert report['production_enabled'] is False
    assert fit_budgeted_transfer(bad,bank,TransferConfig(max_features=8)).status!='provisional_identified'


def test_random_table_stays_unidentified_and_not_diagnosed_as_one_error():
    bank=_bank()
    train,_=_pair('iid_random',9351)
    fit=fit_budgeted_transfer(train,bank,TransferConfig(max_features=8))
    report=diagnose_training_noise(train,bank,TransferConfig(max_features=8))
    assert fit.status!='provisional_identified'
    assert report['status']!='single_label_suspected'


def test_drift_is_evaluated_only_after_labels_arrive_and_not_predicted_early():
    bank=_bank()
    train,held=_pair('xor_shift',9202)
    frozen=fit_budgeted_transfer(train,bank,TransferConfig(max_features=8))
    clean=CellDataset(held.rows[:20])
    shift_truth=challenge_data('abs_scaled',9202)
    changed=CellDataset(tuple((a,b,int(shift_truth[a,b])) for a,b,_ in clean.rows))
    ok=detect_labeled_shift(frozen,clean)
    bad=detect_labeled_shift(frozen,changed)
    assert ok['status']=='no_shift_signal'
    assert bad['status']=='shift_suspected'
    assert bad['observed_errors']>0
    assert bad['fit_was_refreshed'] is False
    assert bad['labels_arrived_after_training'] is True


def test_single_scattered_monitor_error_should_not_trigger_drift_alarm():
    bank=_bank()
    train,held=_pair('xor_shift',9202)
    frozen=fit_budgeted_transfer(train,bank,TransferConfig(max_features=8))
    clean=list(held.rows[:20]);a,b,y=clean[1];clean[1]=(a,b,(y+1)%10)
    report=detect_labeled_shift(frozen,CellDataset(tuple(clean)))
    assert report['status']=='no_shift_signal'
    assert report['observed_errors']==1


def test_configuration_and_window_validation():
    for v in (0,-1,True,1.5,385):
        with pytest.raises(ValueError): TransferConfig(max_features=v)
    bank=_bank()
    train,held=_pair('xor_shift',9202)
    fit=fit_budgeted_transfer(train,bank,TransferConfig(max_features=8))
    with pytest.raises(ValueError,match='exactly'):
        detect_labeled_shift(fit,CellDataset(held.rows[:19]))
    with pytest.raises(ValueError,match='0 <'):
        detect_labeled_shift(fit,CellDataset(held.rows[:20]),expected_error_rate=1.)
