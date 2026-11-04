import pytest
from pailie5.filter_validation_v35 import evaluate_filter
from pailie5.nca_v36 import Observation, Operator, operators, fit_and_test

def test_filter_baseline():
    r=evaluate_filter([{'00001'},{'00002'}],['00001','00003'])
    assert r.removal_rate==1/100000 and r.miss_rate==0.5

def test_held_out():
    r=fit_and_test([Observation('001','00001',0),Observation('002','00002',1)],
                   [Observation('003','99999',2)])
    assert not r['production_enabled'] and r['test_count']==1

def test_future_rejected():
    with pytest.raises(ValueError):
        fit_and_test([Observation('001','00000',0,False)],[Observation('002','00000',0)])

def test_overlap_rejected():
    with pytest.raises(ValueError):
        fit_and_test([Observation('001','00000',0)],[Observation('001','00000',0)])

def test_operator_shape():
    with pytest.raises(ValueError): Operator('bad',(0,1))
    assert len(operators())==10
