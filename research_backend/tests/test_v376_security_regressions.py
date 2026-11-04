"""Regression checks for independently observed BUG-001/002/003.

These must fail on the frozen V3.7.6 baseline and pass after the fixes.
"""
import pytest

from pailie5.filter_validation_v35 import evaluate_filter
from pailie5.nca_v36 import Observation, fit_and_test


def r(issue, draw='00000', ext=0, **kwargs):
    return Observation(issue, draw, ext, **kwargs)


@pytest.mark.parametrize('train_issues,test_issues', [
    (['011', '012'], ['010']),
    (['009', '011'], ['010']),
    (['011', '010'], ['012']),  # unsorted training window
    (['010', '011'], ['013', '012']),  # unsorted held-out window
    (['001'], ['1']),  # same numeric issue, different string padding
])
def test_v36_rejects_temporal_leakage(train_issues, test_issues):
    with pytest.raises(ValueError):
        fit_and_test([r(i) for i in train_issues], [r(i) for i in test_issues])


def test_v36_numeric_issue_order_not_lexicographic():
    result = fit_and_test([r('9')], [r('10')])
    assert result['test_count'] == 1


@pytest.mark.parametrize('invalid_issue', ['abc', '١٢٣', '1a', '', '1.2'])
def test_v36_rejects_ambiguous_issue_identifiers(invalid_issue):
    with pytest.raises(ValueError):
        fit_and_test([r(invalid_issue)], [r('010')])


@pytest.mark.parametrize('nonascii_draw', ['１２３４５', '1234²', '٠١٢٣٤'])
def test_v36_only_accepts_ascii_five_digit_draws(nonascii_draw):
    with pytest.raises(ValueError):
        fit_and_test([r('001', nonascii_draw)], [r('002')])


@pytest.mark.parametrize('nonascii_draw', ['１２３４５', '1234²', '٠١٢٣٤'])
def test_v35_only_accepts_ascii_winners(nonascii_draw):
    with pytest.raises(ValueError):
        evaluate_filter([{'00001'}], [nonascii_draw])


@pytest.mark.parametrize('nonascii_draw', ['１２３４５', '1234²', '٠١٢٣٤'])
def test_v35_only_accepts_ascii_excluded_numbers(nonascii_draw):
    with pytest.raises(ValueError):
        evaluate_filter([{nonascii_draw}], ['00000'])


def test_v35_ascii_leading_zero_is_valid():
    result = evaluate_filter([{'00000'}], ['00000'])
    assert result.removed_winners == 1 and result.removed_count == 1


def test_v36_rejects_external_data_published_after_draw():
    with pytest.raises(ValueError):
        fit_and_test(
            [r('001', draw_at='2026-11-01T19:00:00+08:00',
               external_published_at='2026-11-01T19:01:00+08:00')],
            [r('002', draw_at='2026-11-02T19:00:00+08:00',
               external_published_at='2026-11-02T18:00:00+08:00')]
        )


def test_v36_rejects_partial_timestamp_evidence():
    with pytest.raises(ValueError):
        fit_and_test([r('001', draw_at='2026-11-01T19:00:00+08:00')], [r('002')])


def test_v36_rejects_unzoned_or_mixed_timestamp_evidence():
    with pytest.raises(ValueError):
        fit_and_test([r('001', draw_at='2026-11-01T19:00:00',
                        external_published_at='2026-11-01T18:00:00+08:00')],
                     [r('002')])
    with pytest.raises(ValueError):
        fit_and_test([r('001', draw_at='2026-11-01T19:00:00+08:00',
                        external_published_at='2026-11-01T18:00:00+08:00')],
                     [r('002')])


def test_v36_rejects_inconsistent_issue_and_clock_time():
    with pytest.raises(ValueError):
        fit_and_test(
            [r('001', draw_at='2026-11-02T19:00:00+08:00',
               external_published_at='2026-11-02T18:00:00+08:00')],
            [r('002', draw_at='2026-11-01T19:00:00+08:00',
               external_published_at='2026-11-01T18:00:00+08:00')]
        )


def test_v36_reports_timestamp_verification_status():
    verified = fit_and_test(
        [r('001', draw_at='2026-11-01T19:00:00+08:00',
           external_published_at='2026-11-01T18:00:00+08:00')],
        [r('002', draw_at='2026-11-02T19:00:00+08:00',
           external_published_at='2026-11-02T18:00:00+08:00')]
    )
    assert verified['timestamp_alignment_verified'] is True
    legacy = fit_and_test([r('001')], [r('002')])
    assert legacy['timestamp_alignment_verified'] is False
    assert legacy['production_enabled'] is False
