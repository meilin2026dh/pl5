"""Dynamic conformal budget tests: user finance cap is a ceiling, never a floor."""
import pytest
from pailie5.dynamic_budget_v3713 import calibrate_scaled_ranks, recommend_daily_budget, evaluate_dynamic_holdout

H = 'f' * 64
S = 'a' * 64


def _cal(ranks=None, scales=None, alpha=0.2):
    values = list(range(1000, 10000, 1000)) if ranks is None else ranks
    factors = [1] * len(values) if scales is None else scales
    return calibrate_scaled_ranks(values, factors, [str(i) for i in range(101,101+len(values))],
                                  alpha=alpha, training_end_issue='100',
                                  frozen_model_sha256=H, frozen_scale_sha256=S)


def test_budget_changes_only_with_frozen_predraw_difficulty():
    c = _cal()
    assert c.quantile_index == 8
    assert (c.quantile_numerator, c.quantile_denominator) == (8000, 1)
    low = recommend_daily_budget(c, '200', difficulty_scale=1, affordable_max_tickets=10000)
    high = recommend_daily_budget(c, '200', difficulty_scale=2, affordable_max_tickets=10000)
    assert (low.required_tickets,low.feasible,low.purchasable_tickets)==(8000,True,8000)
    assert (high.required_tickets,high.feasible,high.purchasable_tickets)==(16000,False,10000)
    assert high.status == 'coverage_target_unaffordable'
    assert high.guarantee_applies_to_purchasable is False
    assert low.guarantee_applies_to_purchasable is True
    assert low.guarantee_requires_exchangeability is True


def test_small_calibration_must_require_entire_space_and_never_exceed_finances():
    c=_cal([100,200,300], [1,2,3], 0.1)
    assert c.fallback_full_domain is True
    x=recommend_daily_budget(c,'200',difficulty_scale=1,affordable_max_tickets=100)
    assert x.required_tickets==100000
    assert x.purchasable_tickets==100
    assert x.feasible is False


def test_rank_normalization_calibrates_exact_ratios_not_integer_truncations():
    c=_cal([1,3,5,7,9,11,13,15,17], [2]*9)
    assert c.quantile_numerator==15
    assert c.quantile_denominator==2
    assert recommend_daily_budget(c,'200',difficulty_scale=3,affordable_max_tickets=25).required_tickets==23


def test_holdout_audit_chronology_and_unaffordable_days_reported_separately():
    c=_cal()
    rows=[('200',2,10000,12000),('201',1,10000,8100),('202',1,9000,3000)]
    out=evaluate_dynamic_holdout(c,rows)
    assert out['n_issues']==3
    assert out['calibrated_hits']==2
    assert out['actually_purchasable_hits']==1
    assert out['unaffordable_days']==1
    assert out['coverage_guarantee_for_capped_sets'] is False
    assert out['fair_draw_reference_for_actual_spend'] == pytest.approx((10000+8000+8000)/300000)


def test_invalid_inputs_and_leakage_are_rejected():
    with pytest.raises(ValueError): _cal(scales=[1,0,1,1,1,1,1,1,1])
    with pytest.raises(ValueError): _cal(scales=[1.5]*9)
    with pytest.raises(ValueError): recommend_daily_budget(_cal(),'109',difficulty_scale=1,affordable_max_tickets=100)
    with pytest.raises(ValueError): recommend_daily_budget(_cal(),'200',difficulty_scale=0,affordable_max_tickets=100)
    with pytest.raises(ValueError): recommend_daily_budget(_cal(),'200',difficulty_scale=1,affordable_max_tickets=-1)
    with pytest.raises(ValueError): recommend_daily_budget(_cal(),'200',difficulty_scale=1,affordable_max_tickets=100000.5)
    with pytest.raises(ValueError): evaluate_dynamic_holdout(_cal(), [('200',1,1000,500),('199',2,1000,501)])
