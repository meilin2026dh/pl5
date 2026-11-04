import pytest
from pailie5.conformal_audit_v3713 import calibrate_rank_cutoff, assess_future_ranks, audit_fixed_filter

MODEL_HASH='b'*64

def _cal(ranks,alpha=0.1, issues=None, end='100'):
    return calibrate_rank_cutoff(ranks,issues or [str(i) for i in range(101,101+len(ranks))],alpha=alpha,frozen_model_sha256=MODEL_HASH,training_end_issue=end)


def test_n_plus_one_split_conformal_quantile_and_holdout():
    ranks=list(range(1000,100000,1000))  # 99 ranks
    c=_cal(ranks)
    assert c.n_calibration==99
    assert c.quantile_index==90
    assert c.cutoff==90000
    assert c.fallback_full_domain is False
    report=assess_future_ranks(c,[1,95000,30000],['300','301','302'])
    assert report['hits']==2
    assert report['misses']==1
    assert report['empirical_coverage']==pytest.approx(2/3)
    assert report['fair_draw_coverage_reference']==0.9
    assert report['miss_rate_upper_bound']>=1/3
    assert report['model_sha256']==MODEL_HASH
    assert report['is_conditional_guarantee'] is False


def test_small_calibration_samples_fall_back_to_full_domain():
    c=_cal([1,10000,90000], alpha=0.1)
    assert c.fallback_full_domain is True
    assert c.cutoff==100000
    assert assess_future_ranks(c,[100000],['200'])['hits']==1


def test_risk_bound_zero_misses_is_positive_and_not_overconfident():
    c=_cal(list(range(1000,100000,1000)))
    report=assess_future_ranks(c,[100,101,102],['300','301','302'])
    assert 0.6 < report['miss_rate_upper_bound'] < 1
    assert report['predictive_advantage']=='NOT_ESTABLISHED'


def test_data_leak_and_malformed_inputs_rejected():
    with pytest.raises(ValueError):
        _cal([1,10],issues=['102','101'])
    with pytest.raises(ValueError):
        _cal([0],issues=['101'])
    with pytest.raises(ValueError):
        _cal([90000],issues=['100'])
    with pytest.raises(ValueError):
        _cal([1000],issues=['１０１'])
    with pytest.raises(ValueError):
        _cal([1000],alpha=0)
    with pytest.raises(ValueError):
        _cal([1000],end='100',issues=['101'],alpha=1)
    with pytest.raises(ValueError):
        assess_future_ranks(_cal([1000],issues=['101']),[1],['101'])
    with pytest.raises(ValueError):
        assess_future_ranks(_cal([1000],issues=['101']),[1],['200'],confidence=1)


def test_fixed_precommitted_filter_separate_binary_risk_audit():
    results=audit_fixed_filter(
        [('201','12345'),('202','00001')],
        {'201':['12345','34567'],'202':['11111','12345']},
        training_end_issue='150',precommitted=True,confidence=0.95)
    assert results['hits']==1 and results['misses']==1
    assert results['fair_draw_coverage_reference']==pytest.approx(2/100000)
    assert results['conformal_guarantee'] is False
    with pytest.raises(ValueError):
        audit_fixed_filter([('201','12345')],{'201':['12345']},training_end_issue='150',precommitted=False)
    with pytest.raises(ValueError):
        audit_fixed_filter([('201','12345')],{'201':['12345','12345']},training_end_issue='150',precommitted=True)
