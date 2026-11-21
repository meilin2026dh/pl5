import numpy as np
import pytest
from pailie5.math_language_v37 import Expression, discover, properties, transfer


def test_exact_discovery_and_certification():
    table = Expression('affine',(1,1,0)).evaluate()
    r = discover(table)
    assert r['exact_certified']
    assert r['observed_errors'] == 0
    assert r['properties']['commutative']
    assert r['properties']['associative']
    assert r['properties']['identities'] == [0]


def test_unseen_cell_diagnostic():
    table = Expression('affine',(1,1,0)).evaluate()
    altered = table.copy()
    altered[9,9] = (int(altered[9,9])+1)%10
    mask = np.ones((10,10), dtype=bool)
    mask[9,9] = False
    result = discover(altered, mask)
    assert result['observed_errors'] == 0
    assert result['unseen_errors'] == 1
    assert not result['exact_certified']


def test_nontrivial_operation_properties():
    table = Expression('affine',(1,0,0)).evaluate()
    p = properties(table)
    assert not p['commutative']
    assert not p['associative'] or not p['identities']


def test_transfer_requires_same_exact_expression():
    x = Expression('affine',(1,1,0)).evaluate()
    assert transfer(x,x)['shared_expression']
    y = Expression('affine',(1,1,1)).evaluate()
    assert not transfer(x,y)['shared_expression']


def test_invalid_table_rejected():
    with pytest.raises(ValueError):
        discover(np.zeros((9,10),dtype=int))
