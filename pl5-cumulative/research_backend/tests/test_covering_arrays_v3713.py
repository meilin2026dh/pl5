import pytest
from itertools import combinations
from pailie5.covering_arrays_v3713 import generate_pl5_covering_array, audit_interactions

@pytest.mark.parametrize('strength,maximum',[(2,150),(3,1500)])
def test_generation_reaches_full_coverage_without_optimality_claim(strength,maximum):
    rows=generate_pl5_covering_array(strength)
    assert len(rows)==len(set(rows))
    assert len(rows)<=maximum
    assert all(len(r)==5 and r.isascii() and r.isdecimal() for r in rows)
    report=audit_interactions(rows,strength)
    assert report['covered']==len(tuple(combinations(range(5),strength)))*10**strength
    assert report['missing']==0
    assert report['coverage_fraction']==1.0
    assert report['is_proven_minimum'] is False
    assert generate_pl5_covering_array(strength)==rows

def test_exact_audit_counts_and_rejects_bad_inputs():
    x=audit_interactions(['00000'],2)
    assert x['covered']==10 and x['required']==1000
    assert x['missing']==990
    with pytest.raises(ValueError):
        audit_interactions(['１２３４５'],2)
    with pytest.raises(ValueError):
        audit_interactions(['0000'],2)
    with pytest.raises(ValueError):
        audit_interactions(['00000','00000'],2)
    with pytest.raises(ValueError):
        generate_pl5_covering_array(4)
