import numpy as np
import pytest
from pailie5.math_language_v37 import Expression
from pailie5.operator_evolution_v371 import evolve, EvolutionConfig

def masks():
    t = np.ones((10,10),dtype=bool)
    t[::2,::2] = False
    return t, ~t

def test_reproducible_and_exact_seed():
    x = Expression('affine',(1,1,0)).evaluate()
    a,b = masks()
    r = evolve(x,a,b)
    assert r == evolve(x,a,b)
    assert r['train_errors'] == r['validation_errors'] == 0

def test_validation_is_not_used_for_selection():
    x = Expression('affine',(1,1,0)).evaluate()
    a,b = masks()
    altered=x.copy()
    altered[b] = (altered[b]+1)%10
    r,s=evolve(x,a,b),evolve(altered,a,b)
    assert r['table'] == s['table']
    assert s['validation_errors'] > 0

def test_no_production_activation():
    x = Expression('affine',(1,1,0)).evaluate()
    a,b=masks()
    assert evolve(x,a,b)['production_enabled'] is False

def test_overlapping_masks_rejected():
    x=np.zeros((10,10),dtype=int)
    a=np.ones((10,10),dtype=bool)
    with pytest.raises(ValueError): evolve(x,a,a)

def test_bad_configuration_rejected():
    x=np.zeros((10,10),dtype=int)
    a,b=masks()
    with pytest.raises(ValueError): evolve(x,a,b,EvolutionConfig(population=1))
