"""No-lookahead, missing-arm and evidence classification checks for V3.7.30."""
import copy
import hashlib
import pytest
from scipy.stats import binomtest

from pailie5.prequential_portfolio_audit_v3730 import evaluate_prequential_portfolio


def fixture():
    methods = ("random", "alpha", "beta")
    # Hits are developer-authored artificial ledger outcomes, not lottery evidence.
    hits = [
        (False, True, False), (False, True, False),
        (False, False, True), (False, False, True),
        (True, False, True), (False, True, False),
        (False, True, False),
    ]
    predictions = []
    for idx, period in enumerate(hits, 1):
        for arm, hit in zip(methods, period):
            predictions.append({
                "issue": str(idx), "method": arm, "actual": f"{idx:05d}",
                "candidate_count": 100,
                "candidate_sha256": hashlib.sha256(f"{idx}:{arm}".encode()).hexdigest(),
                "history_sha256": hashlib.sha256(f"history:{idx}".encode()).hexdigest(),
                "hit": hit,
            })
    return {
        "schema": "pl5-v3719-research-validation-1",
        "evidence_level": "RETROSPECTIVE_WALK_FORWARD_ONLY",
        "dataset_sha256": "a" * 64, "protocol_sha256": "b" * 64,
        "test_count": len(hits),
        "protocol": {"methods": list(methods), "top_k": 100},
        "predictions": predictions,
    }


def test_prequential_choices_are_past_only_and_deterministic():
    r = fixture()
    a = evaluate_prequential_portfolio(r, calibration_periods=2, lookback=2)
    assert a == evaluate_prequential_portfolio(r, calibration_periods=2, lookback=2)
    assert [x["selected_arm"] for x in a["decisions"]] == [
        "alpha", "alpha", "beta", "beta", "random"
    ]
    assert a["evaluation_periods"] == 5
    assert a["evidence_level"] == "RETROSPECTIVE_ADAPTIVE_SELECTION_ONLY"
    assert a["predictive_advantage"] == "NOT_ESTABLISHED"
    assert a["selection_compute_budget_equalized"] is False


def test_mutating_current_and_future_outcome_cannot_change_current_selection():
    base = fixture()
    original = evaluate_prequential_portfolio(base, calibration_periods=2, lookback=3)
    changed = copy.deepcopy(base)
    for x in changed["predictions"]:
        if int(x["issue"]) >= 5:
            x["hit"] = not x["hit"]
    other = evaluate_prequential_portfolio(changed, calibration_periods=2, lookback=3)
    assert [x["selected_arm"] for x in original["decisions"][:3]] == [
        x["selected_arm"] for x in other["decisions"][:3]
    ]
    assert original["input_prediction_ledger_sha256"] != other["input_prediction_ledger_sha256"]


def test_delay_excludes_recent_results_and_changes_selection():
    r = fixture()
    immediate = evaluate_prequential_portfolio(r, calibration_periods=2, lookback=1)
    delayed = evaluate_prequential_portfolio(r, calibration_periods=2, lookback=1, outcome_delay=1)
    assert immediate["decisions"][0]["selected_arm"] == "alpha"
    assert delayed["decisions"][0]["selected_arm"] == "alpha"
    assert immediate["decisions"][2]["selected_arm"] == "beta"
    assert delayed["decisions"][2]["selected_arm"] == "beta"
    assert delayed["decisions"][0]["feedback_last_issue"] == "1"
    assert immediate["decisions"][0]["feedback_last_issue"] == "2"


@pytest.mark.parametrize("mutation", [
    lambda r: r["predictions"].pop(),
    lambda r: r["predictions"].append(copy.deepcopy(r["predictions"][0])),
    lambda r: r["predictions"][0].update(candidate_count=99),
    lambda r: r["predictions"][0].update(hit=1),
    lambda r: r["predictions"][0].update(candidate_sha256="wrong"),
    lambda r: r["predictions"][0].update(actual="99999"),
    lambda r: r.update(test_count=99),
    lambda r: r.update(evidence_level="EXTERNAL_BLIND_VERIFIED"),
    lambda r: r["predictions"][3].update(issue="0"),
    lambda r: r["predictions"][1].update(history_sha256="different"),
])
def test_fail_closed_on_bad_or_incomplete_ledger(mutation):
    report = fixture()
    mutation(report)
    with pytest.raises(ValueError):
        evaluate_prequential_portfolio(report)


@pytest.mark.parametrize("kwargs", [
    {"calibration_periods": 0}, {"calibration_periods": 7},
    {"lookback": 0}, {"outcome_delay": -1},
    {"calibration_periods": True}, {"outcome_delay": False},
])
def test_bad_window_settings_rejected(kwargs):
    with pytest.raises(ValueError):
        evaluate_prequential_portfolio(fixture(), **kwargs)


def test_exact_null_calibration_and_paired_complete_contingency():
    result = evaluate_prequential_portfolio(fixture(), calibration_periods=2, lookback=2)
    decisions = result["decisions"]
    n = len(decisions)
    assert n == 5
    portfolio_only = sum(x["hit"] and not x["random_hit"] for x in decisions)
    random_only = sum(x["random_hit"] and not x["hit"] for x in decisions)
    both = sum(x["hit"] and x["random_hit"] for x in decisions)
    neither = sum(not x["hit"] and not x["random_hit"] for x in decisions)
    assert portfolio_only + random_only + both + neither == n
    assert result["paired_portfolio_only_hits"] == portfolio_only
    assert result["paired_random_only_hits"] == random_only
    assert result["paired_both_hit"] == both
    assert result["paired_neither_hit"] == neither
    assert result["one_sided_exact_binomial_p_unadjusted"] == pytest.approx(
        binomtest(result["selected_hits"], n, p=0.001, alternative="greater").pvalue
    )
    discordant = portfolio_only + random_only
    assert result["one_sided_exact_discordance_p_unadjusted"] == pytest.approx(
        binomtest(portfolio_only, discordant, p=0.5, alternative="greater").pvalue
        if discordant else 1.0
    )
    assert result["formal_significance_claim"] is False
    assert result["predictive_advantage"] == "NOT_ESTABLISHED"


def test_all_tied_or_identical_arms_have_no_paired_signal():
    report = fixture()
    for row in report["predictions"]:
        row["hit"] = False
    out = evaluate_prequential_portfolio(report, calibration_periods=2)
    assert out["paired_portfolio_only_hits"] == 0
    assert out["paired_random_only_hits"] == 0
    assert out["one_sided_exact_discordance_p_unadjusted"] == 1.0
    assert out["one_sided_exact_binomial_p_unadjusted"] == 1.0


@pytest.mark.parametrize("invalid", ["", "0" * 63, "x" * 64, None])
def test_missing_or_forged_history_digest_fails_closed(invalid):
    report = fixture()
    report["predictions"][0]["history_sha256"] = invalid
    with pytest.raises(ValueError):
        evaluate_prequential_portfolio(report)
