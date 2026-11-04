"""Shared strict PL5 digit validation for the research-only filters.

ASCII is intentional: Unicode isdecimal/isdigit also accepts other numeral systems.
Do not coerce values to strings: a 5-digit draw is an identifier, not an integer.
"""
import re

_DRAW_RE = re.compile(r"[0-9]{5}")
_ISSUE_RE = re.compile(r"[0-9]+")


def is_five_digit_draw(value: object) -> bool:
    return isinstance(value, str) and _DRAW_RE.fullmatch(value) is not None


def is_numeric_issue(value: object) -> bool:
    return isinstance(value, str) and _ISSUE_RE.fullmatch(value) is not None
