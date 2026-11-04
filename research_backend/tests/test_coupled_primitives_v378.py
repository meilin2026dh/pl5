"""First written against missing V3.7.8 functionality (TDD regression tests)."""
import numpy as np
import pytest

from pailie5.structure_search_v372 import CellDataset
from pailie5.coupled_primitives_v378 import fit_coupled_primitive, evaluate_coupled
from pailie5.primitive_study_v377 import make_truth, split_truth


def samples(truth, seed=1729):
    return split_truth(np.asarray(truth, dtype=np.uint8), seed)


def test_bilinear_coupling_identified_without_holdout_labels():
    truth = make_truth('coupled_product', 7777)
    train, holdout = samples(truth)
    learned = fit_coupled_primitive(train)
    assert learned.status == 'identified'
    assert learned.family == 'bilinear_mod10'
    result = evaluate_coupled(learned, holdout)
    assert result['count'] == 30 and result['errors'] == 0
    assert result['production_enabled'] is False


def test_piecewise_switch_identified():
    truth = make_truth('coupled_threshold', 7137)
    train, holdout = samples(truth, 1234)
    learned = fit_coupled_primitive(train)
    assert learned.status == 'identified'
    assert learned.family == 'piecewise_linear_mod10'
    assert evaluate_coupled(learned, holdout)['errors'] == 0


def test_additive_predecessor_still_supported():
    truth = make_truth('latent_quadratic', 134)
    train, holdout = samples(truth)
    learned = fit_coupled_primitive(train)
    assert learned.status == 'identified'
    assert evaluate_coupled(learned, holdout)['errors'] == 0


def test_random_negative_control_abstains():
    truth = make_truth('iid_random', 20261103)
    train, holdout = samples(truth)
    learned = fit_coupled_primitive(train)
    assert learned.status != 'identified'
    assert learned.predict(0, 0) is None
    with pytest.raises(ValueError):
        evaluate_coupled(learned, holdout)


def test_holdout_label_changes_cannot_change_fitted_primitive():
    truth = make_truth('coupled_product', 233)
    train, holdout = samples(truth)
    altered = CellDataset(tuple((a, b, (y + 1) % 10) for a, b, y in holdout.rows))
    learned = fit_coupled_primitive(train)
    assert learned.to_dict() == fit_coupled_primitive(train).to_dict()
    assert evaluate_coupled(learned, holdout)['errors'] == 0
    assert evaluate_coupled(learned, altered)['errors'] == len(holdout.rows)


def test_overlap_refused():
    truth = make_truth('coupled_product', 42)
    train, _ = samples(truth)
    learned = fit_coupled_primitive(train)
    with pytest.raises(ValueError, match='overlap'):
        evaluate_coupled(learned, train)


def test_insufficient_observations_abstains():
    train = CellDataset(((0, 0, 1), (1, 1, 2)))
    model = fit_coupled_primitive(train)
    assert model.status != 'identified'
    assert model.predict(2, 2) is None


def test_frozen_prediction_refuses_noninteger_digits():
    truth = make_truth('coupled_product', 99)
    train, _ = samples(truth)
    learned = fit_coupled_primitive(train)
    with pytest.raises(ValueError):
        learned.predict(True, 0)
    with pytest.raises(ValueError):
        learned.predict(0, 10)


def test_piecewise_alternative_structure_does_not_leak():
    truth = make_truth('coupled_threshold', 2025)
    train, held = samples(truth, 414)
    changed = CellDataset(tuple((a, b, (y + 4) % 10) for a, b, y in held.rows))
    model = fit_coupled_primitive(train)
    assert model.source_data_sha256 == train.fingerprint
    assert model.to_dict()['source_data_sha256'] == train.fingerprint
    assert evaluate_coupled(model, held)['errors'] == 0
    assert evaluate_coupled(model, changed)['errors'] == len(held.rows)


def test_structured_fit_abstains_when_other_family_unidentifiable():
    # Five-parameter piecewise curve can fit sparse training, while an
    # additive table can have many completions: do not proclaim uniqueness.
    full = make_truth('coupled_threshold', 57)
    pairs = [(1,3),(2,5),(1,1),(2,0),(3,2)]
    sparse = CellDataset(tuple((a,b,int(full[a,b])) for a,b in pairs))
    model = fit_coupled_primitive(sparse)
    assert model.status == 'unidentifiable'
    assert model.predict(9,9) is None
