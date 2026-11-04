"""Regression-first: training-only compositional proposals missing from V3.7.9."""
import math
import numpy as np
import pytest

from pailie5.structure_search_v372 import CellDataset
from pailie5.primitive_study_v377 import split_truth
from pailie5.adaptive_primitives_v379 import fit_adaptive_primitive
from pailie5.generated_primitives_v3710 import (
    GeneratorConfig, fit_counterexample_primitive, evaluate_generated,
)


def data(kind):
    a,b = np.indices((10,10), dtype=np.int64)
    u=3*a*a+7*a+2
    v=b*b+3*b+1
    if kind == 'xor_shift': feature=np.bitwise_xor(a+1,b*b)
    elif kind == 'abs_scaled': feature=np.abs((2*a+1)-(b+1))
    elif kind == 'gcd_shift':
        feature=np.array([[math.gcd(int(x)+1,int(y)+1) for y in range(10)]
                           for x in range(10)])
    else: raise ValueError(kind)
    return np.asarray((u+v+3*feature)%10,dtype=np.uint8)


@pytest.mark.parametrize('kind', ['xor_shift','abs_scaled','gcd_shift'])
def test_discovers_composition_missing_from_prior_grammar(kind):
    truth=data(kind)
    train, held=split_truth(truth, 32014)
    assert fit_adaptive_primitive(train).status != 'identified'
    model=fit_counterexample_primitive(train)
    assert model.status=='identified', model.to_dict()
    assert model.family=='generated_interaction'
    assert model.witness_rectangles>0
    assert model.to_dict()['generation_source']=='train_only_contradiction_witnesses'
    assert evaluate_generated(model,held)['errors']==0
    assert model.to_dict()['production_enabled'] is False
    assert model.to_dict()['predictive_advantage']=='NOT_ESTABLISHED'


def test_fit_cannot_see_heldout_or_test_answers():
    train,held=split_truth(data('xor_shift'),32114)
    model=fit_counterexample_primitive(train)
    assert model.to_dict()==fit_counterexample_primitive(train).to_dict()
    bad=CellDataset(tuple((a,b,(v+1)%10) for a,b,v in held.rows))
    assert evaluate_generated(model,bad)['errors']==len(held.rows)
    with pytest.raises(ValueError, match='overlap'):
        evaluate_generated(model,train)


def test_iid_random_training_refused():
    rng=np.random.default_rng(117121)
    train,held=split_truth(rng.integers(0,10,(10,10),dtype=np.uint8),33014)
    model=fit_counterexample_primitive(train)
    assert model.status!='identified'
    assert model.predict(0,9) is None


def test_single_corruption_in_training_refused():
    train,_=split_truth(data('xor_shift'),34014)
    rows=list(train.rows)
    a,b,v=rows[17]
    rows[17]=(a,b,(v+1)%10)
    model=fit_counterexample_primitive(CellDataset(tuple(rows)))
    assert model.status!='identified'


def test_incomplete_search_budget_is_not_promoted():
    train,_=split_truth(data('xor_shift'),32014)
    model=fit_counterexample_primitive(train,GeneratorConfig(max_features=2))
    assert model.status=='budget_exhausted'
    assert model.predict(0,0) is None


def test_sparse_nonidentifiable_cannot_promote():
    model=fit_counterexample_primitive(CellDataset(((0,0,1),(1,1,2))))
    assert model.status!='identified'
    assert model.predict(5,5) is None


def test_existing_grammar_fallback_not_a_new_discovery():
    a,b=np.indices((10,10),dtype=np.int64)
    train,held=split_truth(np.asarray((a*a+2*b+3*a*b)%10,dtype=np.uint8),6609)
    model=fit_counterexample_primitive(train)
    assert model.status=='identified'
    assert model.family=='legacy_v379'
    assert evaluate_generated(model,held)['errors']==0
    assert model.to_dict()['novel_relative_to_v379'] is False


def test_invalid_configuration_and_input():
    for n in (-1,0,1.5,True,1000000):
        with pytest.raises(ValueError): GeneratorConfig(max_features=n)
    model=fit_counterexample_primitive(split_truth(data('xor_shift'),32014)[0])
    for a,b in [(True,0),(10,0),(0,'3')]:
        with pytest.raises(ValueError): model.predict(a,b)
