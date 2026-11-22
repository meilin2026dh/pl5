"""对10万号码的用户定义模式偏好排序（**未校准预测概率**）。

对公平独立开奖，任何时刻每个号码的真实条件概率均为 1/100000。
本模块将启发式反延续惩罚做指数归一化以产生模型分配的权重，
因此 rank/model_probability 仅表达用户偏好，不能解释成统计上已证明的中奖优势。
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import math
from typing import Iterable

import numpy as np
import pandas as pd

from .engine import UNIVERSE
from .pattern_rules import (
    Configuration, Rule, filter_next, indicator_values, _context_values, _transform,
    CONTEXT_INDICATORS, _valid_draw_numbers,
)
from .basic_filters import BasicConstraint, apply_basic_filters


FAIR_PROBABILITY = 1.0 / 100_000


def rule_key(rule: Rule) -> str:
    """内容寻址身份；记录同一期检测到的同一实际规则。"""
    raw = (rule.indicator, rule.transform, rule.pattern, rule.window, rule.mode,
           tuple(rule.observed), tuple(rule.banned_values))
    return hashlib.sha256(repr(raw).encode('utf-8')).hexdigest()[:16]


@dataclass
class RankOutput:
    table: pd.DataFrame
    rule_details: list[dict]
    metadata: dict

    def summary(self, *, top_k: int = 1000) -> dict:
        if not 1 <= top_k <= len(self.table):
            raise ValueError('top_k不合法')
        t = self.table
        top = t.iloc[:top_k]
        return {
            **self.metadata,
            'top_k': top_k,
            'fair_top_k_coverage': top_k / 100_000,
            'model_assigned_top_k_mass': float(top['model_probability'].sum()),
            'top_k_probability_sum_is_not_a_validated_hit_rate': True,
            'unique_score_count': int(t['heuristic_score'].nunique()),
            'max_model_probability': float(t.iloc[0]['model_probability']),
            'min_model_probability': float(t.iloc[-1]['model_probability']),
            'fair_each_number_probability': FAIR_PROBABILITY,
        }


def _signal_weight(fraction: float) -> float:
    """覆盖率大的规则影响小些；这是偏好权重，不是统计学估计。"""
    return float(np.sqrt(max(0.0, 1.0 - fraction)))


@dataclass
class _RankCoreStateV3718:
    """Frozen scores for the entire universe, independent of any future target."""
    order: np.ndarray
    probabilities: np.ndarray
    penalty: np.ndarray
    selected_rule_count: int
    contributing_indicators: int
    hit_count: np.ndarray | None
    basic_ok: np.ndarray | None
    pattern_kept: np.ndarray | None
    rule_details: list[dict]


def _rank_core_v3718(
    history: list[str],
    config: Configuration | None = None,
    *,
    strength: float = 1.0,
    selected_rule_keys: Iterable[str] | None = None,
    basic_constraints: list[BasicConstraint] | None = None,
    basic_catalog=None,
    optimize_context: bool = False,
    include_audit: bool = True,
) -> _RankCoreStateV3718:
    """Single source of ranking semantics for full and light rolling APIs.

    Both paths enumerate, score, normalize and sort *all* 100,000 numbers.
    When include_audit=False we skip only arrays needed to display the full
    table; the future draw is never supplied to this function.
    """
    history_ids = _valid_draw_numbers(history)
    if not np.isfinite(strength) or not 0.0 <= strength <= 8.0:
        raise ValueError('strength必须在0至8之间')
    cfg = config or Configuration()
    result = filter_next(history, cfg, optimize_context=optimize_context)
    selected = set(selected_rule_keys) if selected_rule_keys is not None else None
    available = {rule_key(r) for r in result.rules}
    if selected is not None and not selected.issubset(available):
        raise ValueError('选择了不属于当前历史与配置的规则')

    by_indicator: dict[str, np.ndarray] = {}
    hit_count = np.zeros(100_000, dtype=np.int16) if include_audit else None
    info: list[dict] = []
    selected_count = 0
    ctx_cache: dict[tuple[str, str], np.ndarray] = {}
    for r in result.rules:
        key = rule_key(r)
        active = (r.status == 'applied') if selected is None else (key in selected)
        weight = _signal_weight(r.raw_removed_rate) if active else 0.0
        if include_audit:
            info.append({**r.as_dict(), 'rule_key': key,
                         'selected_for_ranking': active,
                         'heuristic_weight': float(weight)})
        if not active:
            continue
        selected_count += 1
        cache_key = (r.indicator, r.transform)
        if cache_key not in ctx_cache:
            if r.indicator in CONTEXT_INDICATORS:
                vals = _transform(_context_values(r.indicator, history_ids)[1], r.transform)
            else:
                vals = indicator_values(r.indicator, r.transform)
            ctx_cache[cache_key] = vals
        applies = np.isin(ctx_cache[cache_key], r.banned_values)
        if hit_count is not None:
            hit_count += applies.astype(np.int16)
        component = by_indicator.setdefault(r.indicator, np.zeros(100_000, dtype=np.float64))
        np.maximum(component, applies.astype(np.float64) * weight, out=component)

    penalty = np.zeros(100_000, dtype=np.float64)
    for comp in by_indicator.values():
        penalty += comp
    logits = -float(strength) * penalty
    centered = logits - np.max(logits)
    unnormalized = np.exp(centered)
    probabilities = unnormalized / np.sum(unnormalized)
    order = np.lexsort((UNIVERSE, penalty))

    # Even the lightweight API must preserve BasicConstraint validation.
    basic_ok = None
    if basic_constraints:
        valid_ids = (apply_basic_filters(basic_constraints) if basic_catalog is None
                     else basic_catalog.select(basic_constraints))
        if include_audit:
            basic_ok = np.zeros(100_000, dtype=bool)
            basic_ok[valid_ids] = True
    elif include_audit:
        basic_ok = np.ones(100_000, dtype=bool)
    return _RankCoreStateV3718(
        order=order, probabilities=probabilities, penalty=penalty,
        selected_rule_count=selected_count,
        contributing_indicators=len(by_indicator), hit_count=hit_count,
        basic_ok=basic_ok,
        pattern_kept=result.kept if include_audit else None,
        rule_details=info,
    )


def rank_all_numbers(
    history: list[str],
    config: Configuration | None = None,
    *,
    strength: float = 1.0,
    selected_rule_keys: Iterable[str] | None = None,
    basic_constraints: list[BasicConstraint] | None = None,
    basic_catalog=None,
) -> RankOutput:
    """Full, 100,000-row auditable heuristic ranking (not calibrated odds)."""
    state = _rank_core_v3718(
        history, config, strength=strength, selected_rule_keys=selected_rule_keys,
        basic_constraints=basic_constraints, basic_catalog=basic_catalog,
        optimize_context=False, include_audit=True,
    )
    order = state.order
    table = pd.DataFrame({
        'rank': np.arange(1, 100_001, dtype=np.int32),
        'number': [f'{int(v):05d}' for v in UNIVERSE[order]],
        'heuristic_score': np.round(-state.penalty[order], 7),
        'model_probability': state.probabilities[order],
        'fair_probability': np.full(100_000, FAIR_PROBABILITY),
        'hit_rules': state.hit_count[order],
        'basic_pass': state.basic_ok[order],
        'pattern_hard_filter_kept': np.isin(UNIVERSE[order], state.pattern_kept),
    })
    count = state.selected_rule_count
    metadata = {
        'history_length': len(history), 'strength': float(strength),
        'selected_rule_count': count,
        'indicators_contributing': state.contributing_indicators,
        'model_type': 'uncalibrated_heuristic_softmax',
        'interpretation': '模型主观权重，非经过样本外验证的真实条件中奖概率',
        'probability_sum': float(state.probabilities.sum()),
        'zero_signal': (count == 0 or strength == 0),
    }
    return RankOutput(table=table, rule_details=state.rule_details, metadata=metadata)


def rolling_rank_backtest(
    history: list[str], config: Configuration | None = None, *,
    warmup: int = 30, max_periods: int = 25, top_k: int = 1000,
    strength: float = 1.0,
    basic_constraints: list[BasicConstraint] | None = None,
    basic_catalog=None,
    target_only: bool = False,
) -> dict:
    """逐期前向样本外评估；此处仅为探索性回测，不是封存外推验证。"""
    cfg = config or Configuration()
    _valid_draw_numbers(history)
    if warmup < max(cfg.windows):
        raise ValueError('warmup不能少于最大窗口')
    if max_periods < 1 or not 1 <= top_k <= 100_000:
        raise ValueError('max_periods/top_k无效')
    start = max(warmup, len(history) - max_periods)
    if start >= len(history):
        raise ValueError('历史长度不足')
    rows = []
    total_logloss = 0.0
    for t in range(start, len(history)):
        if target_only:
            # Build complete ranking from history[:t] BEFORE inspecting target.
            ranking = rank_target_snapshot_v3717(history[:t], cfg, strength=strength,
                                                  basic_constraints=basic_constraints,
                                                  basic_catalog=basic_catalog)
            actual = history[t]
            row = ranking.extract(actual)
            selected_rule_count = ranking.selected_rule_count
        else:
            ranking = rank_all_numbers(history[:t], cfg, strength=strength,
                                       basic_constraints=basic_constraints,
                                       basic_catalog=basic_catalog)
            actual = history[t]
            # number 的5位字符串匹配，留存前导零。
            row = ranking.table.loc[ranking.table['number'].eq(actual)].iloc[0]
            selected_rule_count = ranking.metadata['selected_rule_count']
        rank = int(row['rank'])
        p = float(row['model_probability'])
        total_logloss -= math.log(p)
        rows.append({
            'draw_index': t, 'actual': actual, 'rank': rank,
            'top_k_hit': bool(rank <= top_k),
            'model_probability': p,
            'model_log_loss': -math.log(p),
            'fair_log_loss': math.log(100_000),
            'selected_rule_count': int(selected_rule_count),
        })
    n = len(rows)
    hits = sum(x['top_k_hit'] for x in rows)
    return {
        'periods': n, 'top_k': top_k, 'top_k_hits': hits,
        'observed_top_k_hit_rate': hits/n,
        'fair_expected_top_k_hits': n*top_k/100_000,
        'average_model_log_loss': total_logloss/n,
        'fair_log_loss': math.log(100_000),
        'log_loss_improvement_vs_fair': math.log(100_000)-total_logloss/n,
        'note': '探索性滚动回测；重复调参会造成数据窥探。只有预注册、封存测试及未来前向验证才能评估可迁移性。',
        'details': rows,
    }

@dataclass
class RankTargetSnapshotV3717:
    """Frozen all-number ranking before actual target lookup (no look-ahead)."""
    order: np.ndarray
    probabilities: np.ndarray
    selected_rule_count: int

    def extract(self, actual: str) -> dict:
        from .pattern_rules import _valid_draw_numbers
        target = int(_valid_draw_numbers([actual])[0])
        match = np.flatnonzero(self.order == target)
        if len(match) != 1:
            raise AssertionError('full 100000-universe ranking lost the target')
        index = int(match[0])
        return {'rank':index + 1,'model_probability':float(self.probabilities[target]),
                'selected_rule_count':self.selected_rule_count}


def rank_target_snapshot_v3717(
    history: list[str],
    config: Configuration | None = None,
    *,
    strength: float = 1.0,
    selected_rule_keys: Iterable[str] | None = None,
    basic_constraints: list[BasicConstraint] | None = None,
    basic_catalog=None,
) -> RankTargetSnapshotV3717:
    """Freeze the same full-universe scoring state without building a DataFrame.

    The observed outcome is looked up *after* scores and order are frozen.
    """
    state = _rank_core_v3718(
        history, config, strength=strength, selected_rule_keys=selected_rule_keys,
        basic_constraints=basic_constraints, basic_catalog=basic_catalog,
        optimize_context=True, include_audit=False,
    )
    return RankTargetSnapshotV3717(state.order, state.probabilities, state.selected_rule_count)
