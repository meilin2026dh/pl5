"""TDD: V3.7.9 operator/boundary search must see training triples only."""
import numpy as np
import pytest

from pailie5.structure_search_v372 import CellDataset
from pailie5.primitive_study_v377 import split_truth
from pailie5.adaptive_primitives_v379 import fit_adaptive_primitive, evaluate_adaptive


def target(kind, *, threshold=9):
    a, b = np.indices((10, 10), dtype=np.int64)
    u = (3*a*a+7*a+2)
    v = (b*b+3*b+1)
    if kind == 'a2b':
        return np.asarray((u+v+7*a*a*b)%10, dtype=np.uint8)
    if kind == 'ab2':
        return np.asarray((u+v+3*a*b*b)%10, dtype=np.uint8)
    if kind == 'sum_split':
        return np.asarray(np.where(a+b<threshold, 3*a+7*b, 7*a*b+3*a+1)%10, dtype=np.uint8)
    if kind == 'difference_split':
        return np.asarray(np.where(a-b<1, 3*a+7*b, 7*a*b+3*a+1)%10, dtype=np.uint8)
    raise AssertionError(kind)


@pytest.mark.parametrize('kind', ['a2b', 'ab2','sum_split','difference_split'])
def test_searches_basis_and_boundary_from_training_only(kind):
    train, holdout = split_truth(target(kind), 511)
    model = fit_adaptive_primitive(train)
    assert model.status == 'identified', model.reason
    assert model.family in ('interaction_basis','dynamic_piecewise')
    assert evaluate_adaptive(model, holdout)['errors'] == 0
    assert model.to_dict()['production_enabled'] is False


def test_held_out_answers_cannot_change_fit():
    train, holdout = split_truth(target('a2b'), 811)
    altered = CellDataset(tuple((a,b,(y+1)%10) for a,b,y in holdout.rows))
    first = fit_adaptive_primitive(train)
    assert first.to_dict() == fit_adaptive_primitive(train).to_dict()
    assert evaluate_adaptive(first,altered)['errors'] == len(holdout.rows)


def test_rejects_independent_random_noise():
    truth = np.random.default_rng(989898).integers(0,10,(10,10),dtype=np.uint8)
    train, _ = split_truth(truth, 511)
    model = fit_adaptive_primitive(train)
    assert model.status != 'identified'
    assert model.predict(1,2) is None


def test_rejects_train_holdout_overlap():
    train, _ = split_truth(target('a2b'), 511)
    model = fit_adaptive_primitive(train)
    if model.status == 'identified':
        with pytest.raises(ValueError,match='overlap'):
            evaluate_adaptive(model,train)


def test_rejects_unidentifiable_sparse_data():
    model = fit_adaptive_primitive(CellDataset(((0,0,1),(1,1,2))))
    assert model.status != 'identified'


def test_refuses_boolean_digit_and_bad_range():
    model = fit_adaptive_primitive(split_truth(target('a2b'), 511)[0])
    with pytest.raises(ValueError): model.predict(True, 0)
    with pytest.raises(ValueError): model.predict(10,0)
