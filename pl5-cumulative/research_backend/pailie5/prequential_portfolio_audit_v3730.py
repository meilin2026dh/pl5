"""Leakage-audited prequential *selection* of already frozen PL5 prediction arms.

Research-only retrospective analysis. A row's outcome never participates in
choosing its own arm; the selector uses only older, settled comparison rows.
The input is a complete run_walk_forward report, not independent evidence of
predraw commitment, authentic data, or predictive advantage.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any

from scipy.stats import binomtest

from .research_validation_v3719 import DOMAIN

SCHEMA = "pl5-prequential-portfolio-audit-1"


def _hash(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def evaluate_prequential_portfolio(
    report: dict[str, Any], *, calibration_periods: int = 3,
    lookback: int = 5, outcome_delay: int = 0,
) -> dict[str, Any]:
    """Choose the best *past* rolling hit count, deterministic frozen tie order.

    For target at zero-based index i, eligible feedback ends strictly before
    i - outcome_delay. The initial calibration periods are not scored.
    Full per-issue predictions must be present; a missing arm is a hard error.
    The rule/hyperparameters MUST be fixed before an evaluation is interpreted.
    """
    if any(type(v) is not int for v in (calibration_periods, lookback, outcome_delay)):
        raise ValueError("window arguments must be integers, not booleans")
    if calibration_periods < 1 or lookback < 1 or outcome_delay < 0:
        raise ValueError("invalid calibration/lookback/delay")
    if not isinstance(report, dict) or report.get("evidence_level") != "RETROSPECTIVE_WALK_FORWARD_ONLY":
        raise ValueError("requires a retrospective walk-forward report")
    protocol = report.get("protocol")
    if not isinstance(protocol, dict):
        raise ValueError("missing protocol")
    methods = protocol.get("methods")
    k = protocol.get("top_k")
    if (not isinstance(methods, (tuple, list)) or len(methods) < 2
            or len(methods) != len(set(methods)) or "random" not in methods
            or any(not isinstance(x, str) for x in methods)
            or type(k) is not int or not 1 <= k <= DOMAIN):
        raise ValueError("invalid fixed method set or ticket budget")
    predictions = report.get("predictions")
    if not isinstance(predictions, list) or not predictions:
        raise ValueError("missing prediction ledger")
    grouped: dict[str, dict[str, dict]] = {}
    issue_order: list[str] = []
    last_issue = -1
    for row in predictions:
        if not isinstance(row, dict):
            raise ValueError("malformed prediction")
        issue = row.get("issue")
        method = row.get("method")
        actual = row.get("actual")
        digest = row.get("candidate_sha256")
        history_digest = row.get("history_sha256")
        if (not isinstance(issue, str) or not re.fullmatch(r"[0-9]+", issue)
                or method not in methods or not isinstance(actual, str)
                or not re.fullmatch(r"[0-9]{5}", actual)
                or type(row.get("hit")) is not bool
                or type(row.get("candidate_count")) is not int
                or row["candidate_count"] != k
                or not isinstance(digest, str)
                or not re.fullmatch(r"[a-f0-9]{64}", digest)
                or not isinstance(history_digest, str)
                or not re.fullmatch(r"[a-f0-9]{64}", history_digest)):
            raise ValueError("invalid method, ticket budget, outcome or frozen digest")
        if issue not in grouped:
            if int(issue) <= last_issue:
                raise ValueError("nonchronological or interleaved issues")
            last_issue = int(issue)
            issue_order.append(issue)
            grouped[issue] = {}
        if method in grouped[issue]:
            raise ValueError("duplicate method for issue")
        if grouped[issue] and any(
            prev["actual"] != actual or prev.get("history_sha256") != row.get("history_sha256")
            for prev in grouped[issue].values()
        ):
            raise ValueError("inconsistent issue outcome/history")
        grouped[issue][method] = row
    if len(predictions) != len(issue_order) * len(methods):
        raise ValueError("incomplete frozen prediction matrix")
    if any(set(grouped[issue]) != set(methods) for issue in issue_order):
        raise ValueError("missing method for issue")
    if len(issue_order) <= calibration_periods:
        raise ValueError("no evaluation periods after calibration")
    if report.get("test_count") != len(issue_order):
        raise ValueError("reported denominator does not match complete ledger")

    decisions: list[dict[str, Any]] = []
    for i in range(calibration_periods, len(issue_order)):
        cutoff = i - outcome_delay
        start = max(0, cutoff - lookback)
        history_issues = issue_order[start:cutoff]
        # Empty history uses the first listed arm, as registered, not outcome.
        prior_hits = {
            arm: sum(int(grouped[t][arm]["hit"]) for t in history_issues)
            for arm in methods
        }
        selected = max(methods, key=lambda arm: prior_hits[arm])
        issue = issue_order[i]
        picked = grouped[issue][selected]
        control = grouped[issue]["random"]
        decisions.append({
            "issue": issue, "selected_arm": selected,
            "eligible_feedback_periods": len(history_issues),
            "feedback_last_issue": history_issues[-1] if history_issues else None,
            "past_hits": prior_hits,
            "candidate_sha256": picked["candidate_sha256"],
            "hit": picked["hit"], "random_hit": control["hit"],
        })
    n = len(decisions)
    hits = sum(int(row["hit"]) for row in decisions)
    controls = sum(int(row["random_hit"]) for row in decisions)
    portfolio_only = sum(int(row["hit"] and not row["random_hit"]) for row in decisions)
    random_only = sum(int(row["random_hit"] and not row["hit"]) for row in decisions)
    discordant = portfolio_only + random_only
    fair_null_p = k / DOMAIN
    # Under the *conditional* iid-uniform null, a past-measurable fixed-K
    # selection has P(hit | previous outcomes)=K/DOMAIN for every period.
    # This remains true with adaptive model choice, but not with lookahead,
    # misspecified candidate size, or post-hoc selection across experiments.
    null_hit_p = float(binomtest(hits, n, p=fair_null_p,
                                alternative="greater").pvalue)
    # With equal frozen set sizes and a uniformly random independent draw,
    # portfolio-only and random-only discordances are conditionally symmetric.
    # The two arms may share candidates; only discordant periods contribute.
    paired_p = (float(binomtest(portfolio_only, discordant, p=0.5,
                               alternative="greater").pvalue)
                if discordant else 1.0)
    return {
        "schema": SCHEMA, "source_schema": report.get("schema"),
        "input_dataset_sha256": report.get("dataset_sha256"),
        "input_protocol_sha256": report.get("protocol_sha256"),
        "input_prediction_ledger_sha256": _hash(predictions),
        "selection_rule": "highest_eligible_rolling_hits; ties in fixed protocol.methods order",
        "calibration_periods": calibration_periods, "lookback": lookback,
        "outcome_delay": outcome_delay, "methods": list(methods), "top_k": k,
        "evaluation_periods": n, "selected_hits": hits, "random_control_hits": controls,
        "fair_expected_hits": n * k / DOMAIN, "decisions": decisions,
        "null_model": "INDEPENDENT_UNIFORM_FIVE_DIGIT_DRAWS_CONDITIONAL_ON_ALL_PRIOR_HISTORY",
        "one_sided_exact_binomial_p_unadjusted": null_hit_p,
        "paired_portfolio_only_hits": portfolio_only,
        "paired_random_only_hits": random_only,
        "paired_both_hit": sum(int(row["hit"] and row["random_hit"]) for row in decisions),
        "paired_neither_hit": sum(int(not row["hit"] and not row["random_hit"]) for row in decisions),
        "one_sided_exact_discordance_p_unadjusted": paired_p,
        "formal_significance_claim": False,
        "evidence_level": "RETROSPECTIVE_ADAPTIVE_SELECTION_ONLY",
        "independent_predraw_commitment_verified": False,
        "selection_compute_budget_equalized": False,
        "predictive_advantage": "NOT_ESTABLISHED",
        "warnings": [
            "Select this rule and all parameters BEFORE an untouched evaluation; after-the-fact parameter tuning invalidates inference.",
            "All base-arm predictions and their origins must be separately audited; SHA digests alone do not establish predraw creation.",
            "Selector's combined computation cost is not equalized against single-arm controls.",
            "Exact null p-values assume independently uniform draws and genuine prior-frozen equal-size candidate sets; observed history cannot verify those premises.",
            "The two one-sided p-values are exploratory and unadjusted for multiple methods, windows or repeated research rounds; no significance gate is issued.",
            "Repeated searches, correlated tests and dataset revisions are not corrected by this descriptive output.",
        ],
    }
