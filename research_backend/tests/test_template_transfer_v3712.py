"""V3.7.12: independent tests of bounded, source-informed unary-template transfer."""
import numpy as np
import pytest
from pailie5.generated_study_v3710 import challenge_data
from pailie5.primitive_study_v377 import split_truth
from pailie5.structure_search_v372 import CellDataset
from pailie5.cross_task_v3711 import certify_transfer_bank, evaluate_provisional
from pailie5.template_transfer_v3712 import (
    TemplateConfig, source_template_candidates, fit_template_transfer,
    evaluate_template_pair, source_acquisition_ledger,
)

@pytest.fixture(scope='module')
def bank_and_sources():
    source=[]
    for i,case in enumerate(('xor_shift','abs_scaled','gcd_shift')):
        seed=9311+i*131
        source.append(split_truth(challenge_data(case,seed),seed+17))
    return certify_transfer_bank(tuple(source)),tuple(source)


def truth(case,seed):
    rng=np.random.default_rng(seed+371212)
    a,b=np.indices((10,10),dtype=np.int64)
    u=rng.integers(0,10,size=10)[a]
    v=rng.integers(0,10,size=10)[b]
    k=int(rng.choice([1,3,7,9]))
    if case=='swapped_xor': feature=np.bitwise_xor(a*a,b+1)
    elif case=='swapped_abs': feature=np.abs((a+1)-(2*b+1))
    elif case=='lifted_gcd': feature=np.gcd(a*a,b+1)
    elif case=='canonical_early': feature=a*a*(b//3)
    elif case=='outside_grammar': feature=np.where((a+3*b)%7<3,np.bitwise_xor(a+1,b*b),np.gcd(a+1,b+1))
    elif case=='iid_random':return rng.integers(0,10,size=(10,10),dtype=np.uint8)
    else:raise ValueError(case)
    return np.asarray((u+v+k*feature)%10,dtype=np.uint8)


def test_candidate_order_uses_source_only_and_proposes_unseen_unary_compositions(bank_and_sources):
    bank,_=bank_and_sources
    ordered=source_template_candidates(bank,TemplateConfig())
    assert len(ordered)==16
    assert len(set(ordered))==16
    assert ordered[:3]==bank.specs
    assert ('square','xor','inc') in ordered[:8]
    assert ('inc','absdiff','twice_inc') in ordered[:8]
    assert ('square','gcd','inc') in ordered[:10]
    assert ('square','xor','inc') not in bank.specs


@pytest.mark.parametrize('case',('swapped_xor','swapped_abs','lifted_gcd'))
def test_related_but_new_unary_family_can_be_fitted_without_holdout_labels(bank_and_sources,case):
    bank,_=bank_and_sources
    train,held=split_truth(truth(case,9811),9811+17)
    fitted=fit_template_transfer(train,bank,TemplateConfig())
    assert fitted.status=='provisional_identified',fitted.to_dict()
    assert evaluate_provisional(fitted,held)['errors']==0
    assert fitted.features_checked==16
    assert fitted.to_dict()['production_enabled'] is False
    assert fitted.selected_spec not in bank.specs


def test_control_detects_negative_transfer_with_equal_target_feature_slots(bank_and_sources):
    bank,_=bank_and_sources
    train,held=split_truth(truth('canonical_early',9831),9831+17)
    pair=evaluate_template_pair(train,held,bank,TemplateConfig())
    assert pair['source_informed']['feature_slots']==16
    assert pair['canonical']['feature_slots']==16
    assert pair['canonical']['status']=='provisional_identified'
    assert pair['canonical']['heldout_errors']==0
    assert pair['source_informed']['status']!='provisional_identified'


@pytest.mark.parametrize('case',('iid_random','outside_grammar'))
def test_unseen_structures_are_not_promoted_without_train_evidence(bank_and_sources,case):
    bank,_=bank_and_sources
    train,_=split_truth(truth(case,9841),9841+17)
    fitted=fit_template_transfer(train,bank,TemplateConfig())
    assert fitted.status!='provisional_identified'


def test_source_reuse_and_holdout_overlap_are_rejected(bank_and_sources):
    bank,source=bank_and_sources
    with pytest.raises(ValueError,match='source'):
        fit_template_transfer(source[0][0],bank,TemplateConfig())
    train,_=split_truth(truth('swapped_xor',9811),9811+17)
    with pytest.raises(ValueError,match='overlap'):
        evaluate_template_pair(train,train,bank,TemplateConfig())


def test_source_acquisition_cost_is_explicit_not_claimed_fully_compute_matched(bank_and_sources):
    bank,sources=bank_and_sources
    ledger=source_acquisition_ledger(bank,sources)
    assert ledger['source_count']==3
    assert ledger['source_feature_tables_examined']>0
    assert ledger['includes_legacy_source_fit_cost'] is False
    assert ledger['pipeline_compute_matched'] is False
    assert ledger['source_bank_id']==bank.identity
    with pytest.raises(ValueError,match='sources'):
        source_acquisition_ledger(bank,sources[:2])


def test_template_config_rejects_unsafe_or_invalid_feature_budgets():
    for v in (True,0,-1,1.2,500):
        with pytest.raises(ValueError):TemplateConfig(max_features=v)
