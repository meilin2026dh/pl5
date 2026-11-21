import pytest
from pailie5.hdse_registry_v26 import grow,status
from pailie5.highdim_v26 import proposals


def test_growth_is_persistent_reproducible_and_never_auto_promotes(tmp_path):
    db=tmp_path/'new'/'capabilities.sqlite'
    assert status(db)['status']=='not_initialized'
    r1=grow(db,base_seed=1,maximum=12)
    r2=grow(db,base_seed=1,maximum=12)
    assert r1['new_capabilities']==12
    assert r2['registered_total']>=r1['registered_total']
    assert r1['seed']!=r2['seed']
    view=status(db)
    assert view['cycles']==2 and view['registered_total']==r2['registered_total']
    assert all(row['card']['prediction_advantage']=='unverified' for row in view['recent'])
    assert r2['automatic_predictive_promotion'] is False


def test_different_semantics_and_invalid_inputs(tmp_path):
    db=tmp_path/'db.sqlite'
    with pytest.raises(ValueError):grow(db,maximum=13)
    with pytest.raises(ValueError):grow(db,base_seed=-1)
    assert len({s.id for s in proposals(14,12)})==12
