"""Finite-sample rank conformal budgets with pre-draw integer scale factors.

A *fixed* trained ranking model and *fixed* difficulty-scaling model produce
scores rank / scale. If calibration and future normalized scores are
exchangeable, an n+1 split conformal quantile yields marginal coverage for
sets {rank <= min(100000, ceil(q * future_scale))}.

This does not imply exchangeability in lottery draws or after adaptation.
Financial limits are hard caps: if required set exceeds cap, full target is
NOT feasible, and no coverage guarantee is claimed for purchased tickets.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import ceil
import re

from .conformal_audit_v3713 import DOMAIN, _issues, _ranks
from .number_validation import is_numeric_issue

_SHA256 = re.compile(r'[0-9a-f]{64}')


def _hash(value: str, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f'{label} requires lowercase hex SHA256 identifier')
    return value


def _scales(values, n: int) -> tuple[int,...]:
    factors = tuple(values)
    if len(factors) != n or any(type(v) is not int or not 1 <= v <= DOMAIN for v in factors):
        raise ValueError('difficulty scales must match rows and be positive integers')
    return factors


@dataclass(frozen=True)
class ScaledRankCalibration:
    model_sha256: str
    scale_model_sha256: str
    training_end_issue: str
    last_calibration_issue: str
    n_calibration: int
    alpha: float
    quantile_index: int
    quantile_numerator: int
    quantile_denominator: int
    fallback_full_domain: bool
    guarantee_kind: str = 'marginal_conditional_on_normalized_score_exchangeability'


@dataclass(frozen=True)
class DailyBudget:
    issue: str
    difficulty_scale: int
    alpha: float
    required_tickets: int
    affordable_max_tickets: int
    purchasable_tickets: int
    feasible: bool
    status: str
    guarantee_applies_to_purchasable: bool
    guarantee_requires_exchangeability: bool = True
    model_precommitment_unverified: bool = True
    fair_draw_coverage_reference: float = 0.0
    predictive_advantage: str = 'NOT_ESTABLISHED'


def calibrate_scaled_ranks(ranks, difficulty_scales, calibration_issues, *,
                           alpha: float, training_end_issue: str,
                           frozen_model_sha256: str, frozen_scale_sha256: str) -> ScaledRankCalibration:
    if type(alpha) not in (int,float) or not 0 < alpha < 1:
        raise ValueError('alpha must lie strictly between 0 and 1')
    _hash(frozen_model_sha256,'ranking model')
    _hash(frozen_scale_sha256,'difficulty model')
    if not is_numeric_issue(training_end_issue):
        raise ValueError('training_end_issue must be an ASCII numeric identifier')
    ids = _issues(calibration_issues,after=int(training_end_issue))
    observed = _ranks(ranks,len(ids))
    scales = _scales(difficulty_scales,len(ids))
    k = ceil((len(ids)+1)*(1-float(alpha)))
    fallback = k > len(ids)
    quantile = Fraction(DOMAIN,1) if fallback else sorted(Fraction(r,s) for r,s in zip(observed,scales))[k-1]
    return ScaledRankCalibration(
        model_sha256=frozen_model_sha256,
        scale_model_sha256=frozen_scale_sha256,
        training_end_issue=training_end_issue,
        last_calibration_issue=ids[-1],
        n_calibration=len(ids),alpha=float(alpha),quantile_index=k,
        quantile_numerator=quantile.numerator,quantile_denominator=quantile.denominator,
        fallback_full_domain=fallback,
    )


def recommend_daily_budget(calibration: ScaledRankCalibration, issue: str, *,
                           difficulty_scale: int, affordable_max_tickets: int) -> DailyBudget:
    if not isinstance(calibration,ScaledRankCalibration):
        raise ValueError('requires frozen calibration')
    if not is_numeric_issue(issue) or int(issue) <= int(calibration.last_calibration_issue):
        raise ValueError('future issue must be strictly later than all calibration issues')
    scale = _scales((difficulty_scale,),1)[0]
    if type(affordable_max_tickets) is not int or not 0 <= affordable_max_tickets <= DOMAIN:
        raise ValueError('affordable_max_tickets must be integer in 0..100000')
    q=Fraction(calibration.quantile_numerator,calibration.quantile_denominator)
    required=DOMAIN if calibration.fallback_full_domain else min(DOMAIN,ceil(q*scale))
    feasible=required <= affordable_max_tickets
    actual=min(required,affordable_max_tickets)
    return DailyBudget(
        issue=issue,difficulty_scale=scale,alpha=calibration.alpha,
        required_tickets=required,affordable_max_tickets=affordable_max_tickets,
        purchasable_tickets=actual,feasible=feasible,
        status='coverage_target_feasible' if feasible else 'coverage_target_unaffordable',
        guarantee_applies_to_purchasable=feasible,
        fair_draw_coverage_reference=actual/DOMAIN,
    )


def evaluate_dynamic_holdout(calibration: ScaledRankCalibration, records) -> dict:
    """Offline audit (issue, pre-draw scale, financial cap, realized rank).

    Caller is responsible for proving scales and rankings were set before
    each draw; this function cannot verify historical precommitment.
    """
    observations=list(records)
    if not observations or any(not isinstance(row,(tuple,list)) or len(row)!=4 for row in observations):
        raise ValueError('holdout records require (issue, scale, cap, realized_rank)')
    ids=_issues((row[0] for row in observations),after=int(calibration.last_calibration_issue))
    observed=_ranks((row[3] for row in observations),len(ids))
    recommended=[recommend_daily_budget(calibration,row[0],difficulty_scale=row[1],affordable_max_tickets=row[2]) for row in observations]
    calibrated_hits=sum(r<=d.required_tickets for r,d in zip(observed,recommended))
    purchasable_hits=sum(r<=d.purchasable_tickets for r,d in zip(observed,recommended))
    return {
        'schema':'pl5-v3713-dynamic-conformal-budget-holdout-1',
        'n_issues':len(ids),
        'calibrated_hits':calibrated_hits,
        'calibrated_coverage':calibrated_hits/len(ids),
        'actually_purchasable_hits':purchasable_hits,
        'purchasable_coverage':purchasable_hits/len(ids),
        'unaffordable_days':sum(not d.feasible for d in recommended),
        'coverage_guarantee_for_capped_sets':all(d.feasible for d in recommended),
        'coverage_guarantee_requires_normalized_score_exchangeability':True,
        'frozen_predraw_scale_attested_not_verified':True,
        'fair_draw_reference_for_actual_spend':sum(d.purchasable_tickets for d in recommended)/(len(ids)*DOMAIN),
        'predictive_advantage':'NOT_ESTABLISHED',
    }
