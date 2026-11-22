"""V3.7.13 frozen rank-based split conformal calibration and binary risk audit.

Classic exchangeable split conformal gives >=1-alpha MARGINAL coverage if
scorer is frozen before calibration and calibration and future observations
are exchangeable. It cannot turn a tiny PL5 selection into a 90%-cover set.
All provenance claims supplied by callers must be externally attested.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil
import re
from scipy.stats import beta

from .number_validation import is_five_digit_draw, is_numeric_issue

DOMAIN = 100000
_SHA256 = re.compile(r'[0-9a-f]{64}')


def _issues(issues, *, after: int) -> tuple[str, ...]:
    if isinstance(issues, (str, bytes)):
        raise ValueError('issues must be a chronological list')
    values = tuple(issues)
    if not values:
        raise ValueError('at least one labeled issue is required')
    previous = after
    for issue in values:
        if not is_numeric_issue(issue) or int(issue) <= previous:
            raise ValueError('issue identifiers must be ASCII numeric, unique and strictly increasing after previous stage')
        previous = int(issue)
    return values


def _ranks(ranks, n: int) -> tuple[int, ...]:
    values = tuple(ranks)
    if len(values) != n:
        raise ValueError('ranks and issues must have identical lengths')
    if any(type(x) is not int or not 1 <= x <= DOMAIN for x in values):
        raise ValueError('rank must be an integer in 1..100000')
    return values


def _rate_confidence(confidence: float) -> float:
    if type(confidence) not in (float, int) or not 0 < confidence < 1:
        raise ValueError('confidence must lie in (0,1)')
    return float(confidence)


def _miss_upper(misses: int, total: int, confidence: float) -> float:
    if misses == total:
        return 1.0
    return float(beta.ppf(confidence, misses + 1, total - misses))


@dataclass(frozen=True)
class RankCalibration:
    schema: str
    model_sha256: str
    training_end_issue: str
    last_calibration_issue: str
    n_calibration: int
    alpha: float
    quantile_index: int
    cutoff: int
    fallback_full_domain: bool
    coverage_type: str = 'exchangeability_dependent_marginal_not_conditional'


def calibrate_rank_cutoff(ranks, calibration_issues, *, alpha: float,
                          frozen_model_sha256: str, training_end_issue: str) -> RankCalibration:
    if type(alpha) not in (float, int) or not 0 < alpha < 1:
        raise ValueError('alpha must lie strictly between 0 and 1')
    if not isinstance(frozen_model_sha256, str) or _SHA256.fullmatch(frozen_model_sha256) is None:
        raise ValueError('frozen model requires lowercase SHA256 identifier')
    if not is_numeric_issue(training_end_issue):
        raise ValueError('training_end_issue must be an ASCII numeric issue id')
    issue_ids = _issues(calibration_issues, after=int(training_end_issue))
    scores = _ranks(ranks, len(issue_ids))
    index = ceil((len(scores) + 1) * (1 - float(alpha)))
    fallback = index > len(scores)
    cutoff = DOMAIN if fallback else sorted(scores)[index - 1]
    return RankCalibration(
        schema='pl5-v3713-split-conformal-rank-1', model_sha256=frozen_model_sha256,
        training_end_issue=training_end_issue, last_calibration_issue=issue_ids[-1],
        n_calibration=len(scores), alpha=float(alpha), quantile_index=index,
        cutoff=cutoff, fallback_full_domain=fallback,
    )


def assess_future_ranks(calibration: RankCalibration, ranks, test_issues, *, confidence: float = 0.95) -> dict:
    if not isinstance(calibration, RankCalibration):
        raise ValueError('requires frozen RankCalibration')
    confidence = _rate_confidence(confidence)
    issues = _issues(test_issues, after=int(calibration.last_calibration_issue))
    scores = _ranks(ranks, len(issues))
    hits = sum(r <= calibration.cutoff for r in scores)
    misses = len(scores) - hits
    return {
        'schema': 'pl5-v3713-conformal-holdout-audit-1',
        'model_sha256': calibration.model_sha256, 'cutoff': calibration.cutoff,
        'n': len(scores), 'hits': hits, 'misses': misses,
        'empirical_coverage': hits / len(scores),
        'miss_rate_upper_bound': _miss_upper(misses, len(scores), confidence),
        'miss_rate_bound_confidence': confidence,
        'fair_draw_coverage_reference': calibration.cutoff / DOMAIN,
        'calibration_exchangeability_required': True,
        'model_freeze_and_chronology_require_external_attestation': True,
        'is_conditional_guarantee': False,
        'predictive_advantage': 'NOT_ESTABLISHED',
    }


def audit_fixed_filter(labeled_draws, kept_by_issue, *, training_end_issue: str,
                       precommitted: bool, confidence: float = 0.95) -> dict:
    """Out-of-time 0/1 fixed-filter audit, NOT conformal guarantee.

    The caller *attests* sets were created before the draw. The software
    cannot cryptographically establish that fact from arbitrary input data.
    """
    if precommitted is not True:
        raise ValueError('must explicitly attest precommitted candidate sets')
    if not is_numeric_issue(training_end_issue):
        raise ValueError('training_end_issue must be an ASCII numeric issue id')
    confidence = _rate_confidence(confidence)
    observations = list(labeled_draws)
    if any(not isinstance(x, (tuple, list)) or len(x) != 2 for x in observations):
        raise ValueError('labeled_draws requires (issue, winning_number) rows')
    issues = _issues((i for i, _ in observations), after=int(training_end_issue))
    if set(kept_by_issue) != set(issues):
        raise ValueError('missing or extra candidate set for draw issue')
    hits = 0
    total_kept = 0
    for issue, actual in observations:
        if not is_five_digit_draw(actual):
            raise ValueError('actual draw must be a valid ASCII PL5 identifier')
        kept = list(kept_by_issue[issue])
        if len(kept) != len(set(kept)) or len(kept) > DOMAIN or any(not is_five_digit_draw(x) for x in kept):
            raise ValueError('candidate sets require unique valid PL5 identifiers')
        total_kept += len(kept)
        hits += actual in set(kept)
    misses = len(issues) - hits
    return {
        'schema': 'pl5-v3713-precommitted-filter-audit-1',
        'n': len(issues), 'hits': hits, 'misses': misses,
        'empirical_coverage': hits / len(issues),
        'miss_rate_upper_bound': _miss_upper(misses, len(issues), confidence),
        'miss_rate_bound_confidence': confidence,
        'fair_draw_coverage_reference': total_kept / (len(issues) * DOMAIN),
        'precommitment_attested_not_verified': True,
        'conformal_guarantee': False,
        'predictive_advantage': 'NOT_ESTABLISHED',
    }
