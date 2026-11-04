"""V3.6 independent external-digit association research (not production betting).

Chronology uses strictly increasing numeric issue IDs; optional timezone-aware
metadata checks publication-before-draw in the *supplied* data. Verification
of timestamps against an independent original publisher is a separate step.
"""
from dataclasses import dataclass
from datetime import datetime

from .number_validation import is_five_digit_draw, is_numeric_issue


@dataclass(frozen=True)
class Observation:
    issue: str
    draw: str
    external_digit: int
    available_before_draw: bool = True
    draw_at: str | None = None
    external_published_at: str | None = None


@dataclass(frozen=True)
class Operator:
    name: str
    table: tuple[int, ...]

    def __post_init__(self):
        if len(self.table) != 10 or any(type(x) is not int or not 0 <= x <= 9 for x in self.table):
            raise ValueError('invalid operator table')


def operators():
    return [Operator(f'shift_{k}', tuple((d + k) % 10 for d in range(10))) for k in range(10)]


def _aware_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or 'T' not in value:
        raise ValueError('timestamp must be an ISO 8601 string with an explicit timezone')
    try:
        timestamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('invalid timestamp') from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError('timestamp requires timezone offset')
    return timestamp


def validate(rows):
    if not rows or any(not is_numeric_issue(r.issue) for r in rows):
        raise ValueError('empty or nonnumeric issue')
    issue_ids = [int(r.issue) for r in rows]
    if any(left >= right for left, right in zip(issue_ids, issue_ids[1:])):
        raise ValueError('issues must be strictly increasing')
    if any(not is_five_digit_draw(r.draw) or
           type(r.external_digit) is not int or not 0 <= r.external_digit <= 9 or
           type(r.available_before_draw) is not bool or not r.available_before_draw
           for r in rows):
        raise ValueError('invalid data or look-ahead')


def _check_publication_metadata(rows):
    """Validate all-or-none source metadata and return draw timestamps if supplied."""
    has_any = any(r.draw_at is not None or r.external_published_at is not None for r in rows)
    if not has_any:
        return None
    if any(r.draw_at is None or r.external_published_at is None for r in rows):
        raise ValueError('partial timestamp evidence; include both fields on all rows')
    draw_times = []
    for row in rows:
        draw_time = _aware_timestamp(row.draw_at)
        published_time = _aware_timestamp(row.external_published_at)
        if published_time > draw_time:
            raise ValueError('external feature was published after draw')
        draw_times.append(draw_time)
    if any(left >= right for left, right in zip(draw_times, draw_times[1:])):
        raise ValueError('draw timestamps must be strictly increasing')
    return draw_times


def miss_rate(rows, op, position):
    validate(rows)
    if position not in range(5):
        raise ValueError('invalid position')
    return sum(int(r.draw[position]) == op.table[r.external_digit] for r in rows) / len(rows)


def fit_and_test(train, test, candidates=None):
    validate(train)
    validate(test)
    # Both sets must be wholly in chronological order, not only disjoint.
    if int(train[-1].issue) >= int(test[0].issue):
        raise ValueError('training issues must precede all test issues')
    all_times = _check_publication_metadata([*train, *test])
    if all_times is not None and all_times[len(train) - 1] >= all_times[len(train)]:
        raise ValueError('training draw time must precede test draw time')
    candidates = list(operators() if candidates is None else candidates)
    if not candidates:
        raise ValueError('no operators')
    score, _, position, op = min((miss_rate(train, op, p), op.name, p, op)
                                 for op in candidates for p in range(5))
    return {'operator': op.name, 'position': position, 'train_miss_rate': score,
            'test_miss_rate': miss_rate(test, op, position), 'baseline': 0.1,
            'test_count': len(test), 'timestamp_alignment_verified': all_times is not None,
            'production_enabled': False}
