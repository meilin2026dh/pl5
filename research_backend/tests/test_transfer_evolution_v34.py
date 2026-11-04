"""Certified mathematical transfer, not lottery forecasting."""
import numpy as np
import pytest
from pailie5.operator_metalearning_v33 import learn,fixtures,LearnedOperator
from pailie5.transfer_evolution_v34 import transfer,public_result
from pailie5.primitive_categories_v31 import run_operator_on_100k,compose_abilities

@pytest.fixture(scope='module')
def parent():return next(x for x in learn(fixtures()['affine_modular'])['abilities'] if x.family=='affine_orbit')

def test_exact_single_mutation(parent):
    a=parent.table().copy();a[1,7]=(int(a[1,7])+1)%parent.levels
    result=transfer(parent,a)
    assert result['status']=='exact_transfer'
    assert result['changed_count']==1
    assert result['operator'].certify()['exact']
    assert np.array_equal(result['operator'].table(),a)
    assert result['operator'].description_bits<result['raw_bits_proxy']
    assert result['diagnostic']['not_lottery_forecast']
    assert public_result(result)['operator']['status']=='research_only'

def test_aan_esse_100k(parent):
    a=parent.table().copy();a[4,6]=(int(a[4,6])+2)%parent.levels
    op=transfer(parent,a)['operator']
    r=run_operator_on_100k(op,(0,4),(0,))
    assert r['total']==100000
    assert r['removed']+r['retained']==100000
    program={'apply':op.id,'args':[{'digit':0},{'digit':4}]}
    output=compose_abilities(program,{op.id:op})
    assert output['number_count']==100000
    assert int(output['outputs'][12345])==op.call(1,5)

def test_transfer_future_cells_not_used_in_diagnostic(parent):
    a=parent.table().copy();a[1,7]=(int(a[1,7])+1)%parent.levels
    r=transfer(parent,a,seed=20261102)
    assert r['diagnostic']['cell_holdout_mismatches']==1

def test_over_capacity_rejected(parent):
    a=parent.table().copy()
    for i in range(8):a[i,0]=(int(a[i,0])+1)%parent.levels
    assert transfer(parent,a)['status']=='exceeds_transfer_capacity'

def test_identical_does_not_claim_novelty(parent):
    assert transfer(parent,parent.table())['status']=='identical_table_no_new_capability'

def test_wrong_output_range(parent):
    a=np.full((10,10),9,dtype=np.int16)
    with pytest.raises(ValueError):transfer(parent,a)

def test_unsupported_family_rejected():
    op=next(x for x in learn(fixtures()['small_tree'])['abilities'] if x.family=='decision_tree')
    assert transfer(op,op.table())['status']=='unsupported_source_family'

def test_original_operator_hasnt_mutated(parent):
    original=parent.table().copy()
    a=original.copy();a[8,1]=(int(a[8,1])+1)%parent.levels
    transfer(parent,a)
    assert np.array_equal(parent.table(),original)
