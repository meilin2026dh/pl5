"""传统/基础指标过滤层：所有条件显式设定，默认不过滤任何号码。"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .engine import UNIVERSE
from .pattern_rules import indicator_values, indicator_table, EXTRA_INDICATORS

@dataclass(frozen=True)
class BasicConstraint:
    indicator: str
    minimum: int | None = None
    maximum: int | None = None
    allowed: tuple[int, ...] | None = None
    denied: tuple[int, ...] | None = None


def apply_basic_filters(constraints: list[BasicConstraint]) -> np.ndarray:
    mask = np.ones(100_000, dtype=bool)
    for rule in constraints:
        if rule.indicator not in indicator_table() and rule.indicator not in EXTRA_INDICATORS:
            raise ValueError(f'未知指标：{rule.indicator}')
        vals = indicator_values(rule.indicator, 'raw')
        if rule.minimum is not None: mask &= vals >= rule.minimum
        if rule.maximum is not None: mask &= vals <= rule.maximum
        if rule.allowed is not None: mask &= np.isin(vals, rule.allowed)
        if rule.denied is not None: mask &= ~np.isin(vals, rule.denied)
    return UNIVERSE[mask].copy()


def combine_basic_and_pattern(basic: list[BasicConstraint], pattern_kept: np.ndarray, *,
                              basic_catalog=None) -> np.ndarray:
    """取交集；不把交集数量的降低错误地报告为预测能力提升。"""
    kept = apply_basic_filters(basic) if basic_catalog is None else basic_catalog.select(basic)
    return np.intersect1d(kept, pattern_kept, assume_unique=True)
