"""V3.7.7: tests are intentionally written before implementation."""
import numpy as np
import pytest
from pailie5.structure_search_v372 import CellDataset
from pailie5.latent_primitives_v377 import fit_additive_primitive, evaluate_frozen_latent


def table_additive():
    return np.array([[(a*a + 3*a + b*b*7 + 2*b) % 10 for b in range(10)] for a in range(10)])


def data(truth, indices):
    return CellDataset(tuple((int(i//10), int(i%10), int(truth.flat[i])) for i in indices))


def split(truth, seed=712):
    order = np.random.default_rng(seed).permutation(100)
    return data(truth, order[:70]), data(truth, order[70:])


def test_discover_heldout_additive_operator_without_target_truth():
    train, unseen = split(table_additive())
    fit = fit_additive_primitive(train)
    assert fit.status == 'identified'
    assert fit.training_errors == 0
    report = evaluate_frozen_latent(fit, unseen)
    assert report['errors'] == 0 and report['count'] == 30
    assert report['coverage'] == 1.0
    assert report['production_enabled'] is False


def test_holdout_label_change_does_not_change_fit():
    train, unseen = split(table_additive())
    fit = fit_additive_primitive(train)
    snapshot = fit.to_dict()
    changed = CellDataset(tuple((a,b,(y+1)%10) for a,b,y in unseen.rows))
    assert evaluate_frozen_latent(fit, changed)['errors'] == 30
    assert fit.to_dict() == snapshot


def test_nonseparable_table_is_rejected():
    truth = np.array([[a*b % 10 for b in range(10)] for a in range(10)])
    train, unseen = split(truth)
    model = fit_additive_primitive(train)
    assert model.status == 'rejected_inconsistent'
    with pytest.raises(ValueError, match='not identified'):
        evaluate_frozen_latent(model, unseen)


def test_random_data_does_not_get_false_certificate():
    for seed in range(10):
        rng = np.random.default_rng(seed)
        train, unused = split(rng.integers(0,10,(10,10)),seed=seed+700)
        assert fit_additive_primitive(train).status == 'rejected_inconsistent'


def test_sparse_underdetermined_data_abstains():
    rows = CellDataset(((0,0,1),(1,1,2),(2,2,3)))
    model = fit_additive_primitive(rows)
    assert model.status == 'unidentifiable'
    assert model.predict(0,1) is None


def test_overlapping_train_holdout_is_rejected():
    train, unseen = split(table_additive())
    with pytest.raises(ValueError, match='overlap'):
        evaluate_frozen_latent(fit_additive_primitive(train), train)


def test_strict_digit_validation_kept():
    with pytest.raises(ValueError):
        fit_additive_primitive(CellDataset(((0,0,3), (0,1,True))))


def test_fingerprint_and_determinism():
    train, unseen = split(table_additive())
    first = fit_additive_primitive(train)
    assert first.to_dict() == fit_additive_primitive(train).to_dict()
    assert len(first.identity) == 64
    assert first.to_dict()['predictive_advantage'] == 'NOT_ESTABLISHED'


def test_does_not_accept_malformed_operator():
    train, unseen = split(table_additive())
    fit = fit_additive_primitive(train)
    with pytest.raises((ValueError, TypeError)):
        evaluate_frozen_latent(fit, {'unseen': True})
