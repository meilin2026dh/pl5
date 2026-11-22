import pytest
from pailie5.codebook_v3713 import encode_one_hot, positional_distance, select_diverse_codebook, audit_codebook
from pailie5.covering_arrays_v3713 import generate_pl5_covering_array


def test_one_hot_is_fixed_weight_five_and_doubles_positional_distance():
    assert len(encode_one_hot('30742'))==50
    assert sum(encode_one_hot('30742'))==5
    assert sum(x!=y for x,y in zip(encode_one_hot('30742'),encode_one_hot('30743')))==2
    assert positional_distance('30742','30743')==1
    with pytest.raises(ValueError):
        encode_one_hot('٣٠٧٤٢')


def test_fixed_budget_min_distance_joint_opt_maintains_hard_constraints():
    candidates=generate_pl5_covering_array(2)
    rows=select_diverse_codebook(candidates,budget=100,min_distance=3,strength=2)
    assert len(rows)==100
    assert rows==select_diverse_codebook(candidates,budget=100,min_distance=3,strength=2)
    report=audit_codebook(rows, strength=2)
    assert report['min_positional_distance']>=3
    assert report['min_binary_one_hot_distance']>=6
    assert report['coverage']['covered']>=850
    assert report['retained_count']==100


def test_infeasible_budget_and_input_validation_are_explicit():
    rows=select_diverse_codebook(['00000','00001','11111'],budget=3,min_distance=5)
    assert len(rows)==2
    with pytest.raises(ValueError):
        select_diverse_codebook(['00000'],budget=-1)
    with pytest.raises(ValueError):
        select_diverse_codebook(['00000'],budget=1,min_distance=6)
    with pytest.raises(ValueError):
        select_diverse_codebook(['00000','00000'],budget=1)
    assert audit_codebook([],strength=2)['min_positional_distance'] is None
