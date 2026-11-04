"""Prerecorded finite study protocols and refusal evidence."""
import pytest
from pailie5.generated_study_v3710 import (CASES, POSITIVE, protocol,
                                             challenge_data, run_predeclared)


def test_protocol_rejects_posthoc_changes():
    p=protocol((8811,))
    assert p['production_enabled'] is False
    assert 'iid_random' in p['cases']
    bad={**p, 'max_features':2000}
    with pytest.raises(ValueError, match='preregistration'):
        run_predeclared(bad)


def test_predeclared_finite_synthetic_study_reproducible():
    p=protocol((8811,))
    a=run_predeclared(p)
    b=run_predeclared(p)
    assert a==b
    assert len(a['trials'])==len(CASES)
    for t in a['trials']:
        assert t['train_sha256']!=t['held_sha256']
        assert t['production_enabled'] is False
        assert t['fit_access_to_holdout_labels'] is False
        assert t['frozen_before_holdout'] is True
    assert a['summary']['real_lottery_advantage_established'] is False


def test_frozen_study_controls_and_genuine_new_mathematical_targets():
    a=run_predeclared(protocol((8812,)))
    controls={t['case']:t for t in a['trials'] if t['case'] not in POSITIVE}
    assert controls['iid_random']['status']!='identified'
    assert controls['train_noise']['status']!='identified'
    assert controls['two_component']['status']!='identified'
    assert controls['concept_drift']['train_generated_from_clean_truth'] is True
    assert controls['concept_drift']['evaluated_on_shifted_truth'] is True


def test_seed_changes_predeclared_target_truth():
    assert challenge_data('xor_shift',8811).tobytes()!=challenge_data('xor_shift',8812).tobytes()


def test_identified_training_does_not_imply_validity_after_drift():
    rows=run_predeclared(protocol((8811,8812)))['trials']
    drift=[r for r in rows if r['case']=='concept_drift']
    assert all(r['status']=='identified' for r in drift)
    assert all(r['held_errors']>0 for r in drift)


def test_ambiguous_generated_completion_abstains_instead_of_overclaiming():
    from pailie5.primitive_study_v377 import split_truth
    from pailie5.generated_primitives_v3710 import fit_counterexample_primitive
    # An official held-out case exhibits multiple consistent full-table models.
    seed=8811*37+3*131
    train,_=split_truth(challenge_data('min_bucket',seed),seed+11)
    fit=fit_counterexample_primitive(train)
    assert fit.status=='unidentifiable'
    assert fit.candidate_models>1
    assert fit.predict(7,9) is None
