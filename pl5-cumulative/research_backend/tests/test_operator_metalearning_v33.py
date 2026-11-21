"""V3.3 math operator metalearning full-domain proofs and adversarial cases."""
import json,sqlite3,hashlib
from pathlib import Path
import numpy as np
import pytest
from pailie5.operator_metalearning_v33 import (fixtures,learn,props,MetaRegistry,LearnedOperator,FAMILIES,PROPERTIES,VERSION)
from pailie5.primitive_categories_v31 import run_operator_on_100k,compose_abilities

@pytest.fixture(scope='module')
def samples():return fixtures()

@pytest.mark.parametrize('name,family',[('affine_modular','affine_orbit'),('two_state_piecewise','piecewise_orbit'),
                                 ('sparse_exception','sparse_exceptions'),('small_tree','decision_tree'),
                                 ('linear_quantized','quantized_linear')])
def test_five_models_learn_real_parameters(samples,name,family):
    result=learn(samples[name],source_id=name,maximum=10)
    choices=[x for x in result['abilities'] if x.family==family]
    assert choices,name
    for op in choices:
        assert np.array_equal(op.table(),samples[name])
        assert op.certify()['checked_pairs']==100
        assert op.description_bits<result['raw_bits_proxy']
        assert op.card()['status']=='research_only'


def test_no_false_structure_on_random(samples):
    r=learn(samples['unstructured_random'])
    assert r['status']=='no_exact_compressed_representation'
    assert r['abilities']==[]


def test_no_fabricated_required_property(samples):
    r=learn(samples['two_state_piecewise'],required_properties=['commutative'])
    assert r['status']=='rejected_property_requirements'
    assert r['unmet']==['commutative']


def test_property_detects_true_symmetry():
    a,b=np.indices((10,10))
    t=np.array([0,1,2]*4,dtype=np.uint8)[:10][(a+b)%10]
    assert props(t)['commutative']
    assert props(t)['shift_opposite_invariant']

@pytest.mark.parametrize('bad', [np.ones((10,10),bool),np.ones((10,10),float),np.full((10,10),8,int),
                               np.zeros((2,2),int)])
def test_table_rejects_invalid_domain(bad):
    with pytest.raises(ValueError):learn(bad)

@pytest.mark.parametrize('kwargs',[{'seed':-1},{'holdout_cells':2},{'max_exceptions':8},
                                   {'maximum':200},{'required_properties':['unknown']},
                                   {'required_properties':["__import__('os')"]}])
def test_bounds(kwargs,samples):
    with pytest.raises(ValueError):learn(samples['affine_modular'],**kwargs)


def test_holdout_diagnostic_is_not_prediction(samples):
    result=learn(samples['affine_modular'])
    assert result['cell_holdout_count']==20
    assert 'not lottery' in result['holdout_meaning']
    assert result['predictive_advantage']=='NOT_ESTABLISHED'
    assert len(result['trials'])>0


def test_deterministic_identity(samples):
    a=learn(samples['affine_modular'])
    b=learn(samples['affine_modular'])
    assert [op.id for op in a['abilities']]==[op.id for op in b['abilities']]


def test_database_append_only_tamper_detection(samples,tmp_path):
    db=MetaRegistry(tmp_path/'test.sqlite')
    op=learn(samples['small_tree'])['abilities'][0]
    assert db.register(op)
    assert db.register(op) is False
    assert db.get(op.id).certify()['exact']
    assert len(db.summary())==1
    with sqlite3.connect(db.path) as conn:
        conn.execute('UPDATE operator_v33 SET record=? WHERE id=?',('some corruption',op.id))
    with pytest.raises(ValueError,match='篡改'):db.get(op.id)


def test_math_identity_payload_change_rejected(samples):
    op=learn(samples['affine_modular'])['abilities'][0]
    data=json.loads(json.dumps(op.__dict__))
    data['payload']['orbit'][0]=(data['payload']['orbit'][0]+1)%3
    with pytest.raises(ValueError,match='ID'):LearnedOperator(**data)


def test_vector_rejects_fraction_and_out_of_range(samples):
    op=learn(samples['affine_modular'])['abilities'][0]
    with pytest.raises(ValueError):op.vector(np.array([1.1]),np.array([2.0]))
    with pytest.raises(ValueError):op.vector(np.array([10]),np.array([2]))
    with pytest.raises(ValueError):op.call(True,2)


def test_aan_esse_full_100k_integration(samples):
    op=learn(samples['small_tree'])['abilities'][0]
    mask=run_operator_on_100k(op,(0,4),(0,))
    assert mask['total']==100000 and mask['retained']+mask['removed']==100000
    r=compose_abilities({'apply':op.id,'args':[{'digit':0},{'digit':4}]},{op.id:op})
    assert r['number_count']==100000
    assert int(r['outputs'][12345])==op.call(1,5)
