"""PL5 V1.1 — Evolutionary Solution-Space Sculpting Engine (ESSE).

Decisions are *reversible*, all 100,000 identities remain in memory and the
trace is deterministic. The scores are **preferences**, not estimated winning
probabilities. For independent uniform draws the conditional win probability
of any deterministic, history-measurable K-number selection is K / 100000.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence
import hashlib
import math
import re

import numpy as np
import pandas as pd

from .engine import UNIVERSE
from .pattern_rules import (
    Configuration, Rule, filter_next, CONTEXT_INDICATORS,
    _context_values, _transform, _valid_draw_numbers, indicator_values,
)
from .probability_ranker import rule_key
from .basic_filters import BasicConstraint, apply_basic_filters

N = 100_000


def _as_mask(mask: np.ndarray) -> np.ndarray:
    arr = np.asarray(mask)
    if arr.shape != (N,) or arr.dtype != np.dtype('bool'):
        raise ValueError('雕刻刀必须提供长度100000的bool过滤掩码')
    copy = np.array(arr, dtype=bool, copy=True)
    copy.flags.writeable = False
    return copy


@dataclass(frozen=True, eq=False)
class Knife:
    """A ``True`` value in ``excluded`` means that knife wants to cut the number.

    ``group`` is a correlated family; scores use groupwise maximum, not sums.
    ``evidence`` is an informational label only, NOT an automatic proof or approval.
    """
    key: str
    label: str
    excluded: np.ndarray
    group: str = 'misc'
    source: str = 'manual'
    weight: float = 1.0
    evidence: str = 'unverified'

    def __post_init__(self):
        if not self.key or not self.label or not self.group:
            raise ValueError('key/label/group不得为空')
        if not math.isfinite(self.weight) or self.weight < 0 or self.weight > 10:
            raise ValueError('权重必须在[0,10]')
        object.__setattr__(self, 'excluded', _as_mask(self.excluded))


@dataclass(frozen=True)
class Stage:
    step: int
    key: str
    label: str
    before: int
    after: int
    newly_removed: int
    already_removed: int
    raw_removed: int
    fair_coverage_after: float
    unique_recoverable: int

    def as_dict(self) -> dict:
        return vars(self).copy()


@dataclass
class Sculpture:
    kept_mask: np.ndarray
    penalty: np.ndarray
    removed_by_count: np.ndarray
    stages: list[Stage]
    audit: dict


class SculptSession:
    """Recompute from the immutable universe after each action; do not mutate masks.

    ``approved_keys`` must be supplied by an EXTERNAL review system, never
    derived from a user-editable ``Knife.evidence`` value. Strict mode rejects
    all other knives, including UI-supplied self-described 'validated' labels.
    """
    def __init__(self, knives: Sequence[Knife], *, enabled: Iterable[str] | None = None,
                 mode: str = 'explore', approved_keys: Iterable[str] = (),
                 seed: int = 20261101):
        self.knives = {k.key: k for k in knives}
        if len(self.knives) != len(knives):
            raise ValueError('雕刻刀key重复')
        if mode not in ('explore', 'strict'):
            raise ValueError('mode只允许 explore/strict')
        self.mode = mode
        self.approved = frozenset(approved_keys)
        if not self.approved.issubset(self.knives):
            raise ValueError('存在无法识别的审批key')
        self._order = [k.key for k in knives]
        requested = set(self.knives if enabled is None else enabled)
        if not requested.issubset(self.knives):
            raise ValueError('启用列表存在未知雕刻刀')
        self._enabled = requested
        self._protected: set[int] = set()
        self._weights = {k.key: k.weight for k in knives}
        self.seed = int(seed)
        self._undo: list[tuple] = []
        self._redo: list[tuple] = []

    def _state(self):
        return (self._order.copy(), self._enabled.copy(), self._protected.copy(), self._weights.copy())

    def _record(self):
        self._undo.append(self._state())
        self._redo.clear()

    def _load(self, state):
        self._order, self._enabled, self._protected, self._weights = state

    def undo(self) -> bool:
        if not self._undo: return False
        self._redo.append(self._state())
        self._load(self._undo.pop())
        return True

    def redo(self) -> bool:
        if not self._redo: return False
        self._undo.append(self._state())
        self._load(self._redo.pop())
        return True

    @property
    def enabled_keys(self) -> tuple[str, ...]:
        return tuple(k for k in self._order if k in self._enabled)

    @property
    def active_keys(self) -> tuple[str, ...]:
        return tuple(k for k in self.enabled_keys if self.mode == 'explore' or k in self.approved)

    @property
    def order(self) -> tuple[str, ...]:
        return tuple(self._order)

    @property
    def protected(self) -> tuple[str, ...]:
        return tuple(f'{n:05d}' for n in sorted(self._protected))

    def set_enabled(self, key: str, enabled: bool) -> None:
        if key not in self.knives: raise KeyError(key)
        if (key in self._enabled) == bool(enabled): return
        self._record()
        if enabled: self._enabled.add(key)
        else: self._enabled.remove(key)

    def set_selected(self, keys: Iterable[str]) -> None:
        selected = set(keys)
        if not selected.issubset(self.knives): raise ValueError('选择了未知规则')
        if selected == self._enabled: return
        self._record(); self._enabled = selected

    def set_order(self, new_order: Iterable[str]) -> None:
        order = list(new_order)
        if len(order) != len(self.knives) or len(set(order)) != len(order) or set(order) != set(self.knives):
            raise ValueError('必须提供所有雕刻刀且不得重复')
        if order == self._order: return
        self._record(); self._order = order

    def move(self, key: str, direction: int) -> None:
        if key not in self.knives: raise KeyError(key)
        i = self._order.index(key)
        j = i + direction
        if not 0 <= j < len(self._order): return
        self._record()
        self._order[i], self._order[j] = self._order[j], self._order[i]

    def protect(self, number: str, value: bool = True) -> None:
        if not re.fullmatch(r'[0-9]{5}', number):
            raise ValueError('恢复号码必须输入完整五位数字，如00128')
        n = int(number)
        if (n in self._protected) == value: return
        self._record()
        if value: self._protected.add(n)
        else: self._protected.remove(n)

    def set_weight(self, key: str, weight: float) -> None:
        if key not in self.knives: raise KeyError(key)
        if not math.isfinite(weight) or weight < 0 or weight > 10:
            raise ValueError('权重必须在0到10之间')
        if self._weights[key] == weight: return
        self._record(); self._weights[key] = float(weight)

    def weight_of(self, key: str) -> float:
        return self._weights[key]

    def _protected_mask(self) -> np.ndarray:
        p = np.zeros(N, dtype=bool)
        if self._protected: p[list(self._protected)] = True
        return p

    def sculpt(self) -> Sculpture:
        protection = self._protected_mask()
        kept = np.ones(N, dtype=bool)
        cuts = np.zeros(N, dtype=np.uint16)
        steps = []
        groups: dict[str, np.ndarray] = {}
        # Note: unique_recoverable is order-INDEPENDENT, i.e. the portion cut
        # by exactly one currently active knife (excluding protected numbers).
        for key in self.active_keys:
            cuts += (self.knives[key].excluded & ~protection).astype(np.uint16)
        for i,key in enumerate(self.active_keys, 1):
            knife = self.knives[key]
            ban = knife.excluded & ~protection
            newly = int((kept & ban).sum())
            before = int(kept.sum())
            already = int((~kept & ban).sum())
            kept &= ~ban
            steps.append(Stage(i,key,knife.label,before,int(kept.sum()),newly,
                               already,int(ban.sum()),float(kept.mean()),
                               int((ban & (cuts == 1)).sum())))
            score = ban.astype(np.float64) * self._weights[key]
            if knife.group not in groups: groups[knife.group] = score
            else: np.maximum(groups[knife.group],score,out=groups[knife.group])
        penalty = np.zeros(N, dtype=np.float64)
        if groups:
            for score in groups.values(): penalty += score
            penalty /= len(groups)  # number of same-group knives cannot inflate weight
        audit = {
            'mode': self.mode, 'requested': len(self._enabled),
            'active': len(self.active_keys), 'unapproved_blocked': len(self.enabled_keys)-len(self.active_keys),
            'kept': int(kept.sum()), 'removed': N-int(kept.sum()),
            'fair_random_coverage': float(kept.mean()),
            'protected': list(self.protected),
            'statistical_status': 'uncalibrated_research_preferences',
            'notes': '压缩率不是预测概率优势；禁用某一刀可恢复其独有排除号码；顺序仅改变每步边际量，不改变最终交集。',
        }
        return Sculpture(kept,penalty,cuts,steps,audit)

    def counterfactual(self) -> list[dict]:
        """Actual recoverable count if any SINGLE active knife is disabled."""
        art = self.sculpt()
        return [dict(key=stage.key,label=stage.label,raw_removed=stage.raw_removed,
                     recoverable_if_disabled=stage.unique_recoverable,
                     overlap_with_other_knives=stage.raw_removed-stage.unique_recoverable,
                     new_exclusions_in_order=stage.newly_removed)
                for stage in art.stages]

    def _tie_rank(self) -> np.ndarray:
        """Reproducible 64-bit mixing, no numeric-order favoritism on equal scores."""
        z = UNIVERSE.astype(np.uint64) ^ np.uint64(self.seed % (1 << 64))
        z ^= z >> np.uint64(30)
        z *= np.uint64(0xbf58476d1ce4e5b9)
        z ^= z >> np.uint64(27)
        z *= np.uint64(0x94d049bb133111eb)
        z ^= z >> np.uint64(31)
        return z

    def rank(self, *, k: int = 100, strength: float = 1.0, 
             locked_kept_first: bool = True) -> tuple[pd.DataFrame, dict]:
        """Return FULL 100k ranked table and top-K summary.

        In ``locked_kept_first`` mode choose kept first. If insufficient survive,
        recover low-penalty excluded candidates (quota-repair). This is a
        *selection mechanism*, not evidence that the top-K is better than chance.
        """
        if not 1 <= k <= N: raise ValueError('k应为1到100000')
        if not math.isfinite(strength) or not 0 <= strength <= 8:
            raise ValueError('strength应处于0到8')
        a = self.sculpt()
        ties = self._tie_rank()
        # numpy lexsort uses the last key as primary: kept first, then penalty, then tie.
        if len(self._protected) > k:
            raise ValueError('用户保护号码数超过本期K注，无法保证全部选入')
        if locked_kept_first:
            priority = (~a.kept_mask).astype(np.int8) + 1
        else:
            priority = np.ones(N,dtype=np.int8)
        if self._protected:
            priority[list(self._protected)] = 0  # user-pinned numbers enter final K
        order = np.lexsort((ties,a.penalty,priority))
        logits = -strength * a.penalty
        weights = np.exp(logits-logits.max())
        weights /= weights.sum()  # preference distribution only, NOT calibrated
        selected = np.zeros(N, dtype=bool)
        selected[order[:k]] = True
        rescued = int((selected & ~a.kept_mask).sum())
        table = pd.DataFrame({
            'rank':np.arange(1,N+1,dtype=np.int32),
            'number':np.char.zfill(UNIVERSE[order].astype(str),5),
            'selected_top_k':selected[order],
            'hard_kept':a.kept_mask[order],
            'restored_for_quota':(selected & ~a.kept_mask)[order],
            'penalty':np.round(a.penalty[order],8),
            'preference_weight_uncalibrated':weights[order],
            'fair_probability':np.full(N,1/N,dtype=np.float64),
            'cut_by_knives':a.removed_by_count[order],
        })
        summary = {**a.audit,'k':k,'selected':k,'restored_for_quota':rescued,
                   'selection_policy':'hard_kept_first' if locked_kept_first else 'score_first',
                   'fair_top_k_coverage': k/N,
                   'fair_10_draw_at_least_one':1-(1-k/N)**10,
                   'preference_weight_top_k':float(weights[order[:k]].sum()),
                   'preference_weight_is_predictive_probability':False,
                   'state_sha256':self.state_hash()}
        return table, summary

    def rank_target_snapshot_v3717(self, *, k: int = 100, strength: float = 1.0,
                                   locked_kept_first: bool = True):
        """Full 100k sorting, but no full 100k-row Pandas table for rolling audit."""
        if not 1 <= k <= N: raise ValueError('k应为1到100000')
        if not math.isfinite(strength) or not 0 <= strength <= 8:
            raise ValueError('strength应处于0到8')
        a = self.sculpt()
        ties = self._tie_rank()
        if len(self._protected) > k:
            raise ValueError('用户保护号码数超过本期K注，无法保证全部选入')
        if locked_kept_first:
            priority = (~a.kept_mask).astype(np.int8) + 1
        else:
            priority = np.ones(N,dtype=np.int8)
        if self._protected:
            priority[list(self._protected)] = 0
        order = np.lexsort((ties,a.penalty,priority))
        logits = -strength * a.penalty
        weights = np.exp(logits-logits.max())
        weights /= weights.sum()
        selected = np.zeros(N,dtype=bool)
        selected[order[:k]] = True
        rescued = int((selected & ~a.kept_mask).sum())
        summary = {**a.audit,'k':k,'selected':k,'restored_for_quota':rescued,
                   'selection_policy':'hard_kept_first' if locked_kept_first else 'score_first',
                   'fair_top_k_coverage':k/N,
                   'fair_10_draw_at_least_one':1-(1-k/N)**10,
                   'preference_weight_top_k':float(weights[order[:k]].sum()),
                   'preference_weight_is_predictive_probability':False,
                   'state_sha256':self.state_hash()}
        return SculptTargetSnapshotV3717(order,a.kept_mask,selected,summary)

    def state_hash(self) -> str:
        payload = repr((self.mode,self.active_keys,self._order,self.protected,
                        [(k,self._weights[k]) for k in self._order],self.seed))
        return hashlib.sha256(payload.encode('utf8')).hexdigest()

    def suggest_greedy_order(self) -> list[str]:
        """Largest additional exclusion first; this optimizes visualization, not accuracy.

        Does not mutate the session. Use set_order() explicitly to apply.
        """
        remaining = list(self.active_keys)
        used = np.zeros(N, dtype=bool)
        result: list[str] = []
        allowed = ~self._protected_mask()
        while remaining:
            key = max(remaining,key=lambda k:(int((self.knives[k].excluded & allowed & ~used).sum()),-self._order.index(k)))
            result.append(key);used |= self.knives[key].excluded & allowed
            remaining.remove(key)
        return result + [k for k in self._order if k not in result]


@dataclass
class SculptTargetSnapshotV3717:
    order: np.ndarray
    kept: np.ndarray
    selected: np.ndarray
    summary: dict

    def extract(self, actual: str) -> dict:
        # The actual number is used only AFTER all 100000 positions have been ranked.
        index = int(_valid_draw_numbers([actual])[0])
        position = np.flatnonzero(self.order == index)
        if len(position) != 1:
            raise AssertionError('target missing from exact full-universe ranking')
        return {'rank':int(position[0])+1,
                'selected_top_k':bool(self.selected[index]),
                'hard_kept':bool(self.kept[index])}


def knives_from_history(history: list[str], config: Configuration,
                        basic: Sequence[BasicConstraint] = (), *,
                        max_knives: int = 120,
                        basic_catalog=None, optimize_context: bool = False) -> tuple[list[Knife], set[str]]:
    """Generate new next-draw knives from the PAST ONLY, including mapped indicators.

    Discovered rules may be included even when previous hard-filter guard skipped
    them. Only previously 'applied' rules are enabled by default.
    """
    _valid_draw_numbers(history)
    found=filter_next(history,config,optimize_context=optimize_context)
    past=np.asarray([int(x) for x in history],dtype=np.int32)
    cache: dict[tuple[str,str],np.ndarray] = {}
    knives: list[Knife] = []
    defaults: set[str] = set()
    for rule in found.rules[:max_knives]:
        ck=(rule.indicator,rule.transform)
        if ck not in cache:
            vals = _context_values(rule.indicator,past)[1] if rule.indicator in CONTEXT_INDICATORS else indicator_values(rule.indicator,'raw')
            cache[ck] = _transform(vals,rule.transform)
        ban = np.isin(cache[ck],rule.banned_values)
        key='pattern:'+rule_key(rule)
        knives.append(Knife(key,rule.as_dict()['label'],ban,group=rule.indicator,
                             source='pattern:'+rule.status))
        if rule.status=='applied': defaults.add(key)
    for i,constraint in enumerate(basic):
        allowed=(apply_basic_filters([constraint]) if basic_catalog is None
                 else basic_catalog.select([constraint]))
        ban=np.ones(N,dtype=bool);ban[allowed]=False
        key=f'basic:{i}:{constraint.indicator}'
        knives.append(Knife(key,f'基础规则：{constraint.indicator} {constraint}',ban,
                             group=constraint.indicator,source='basic'))
        defaults.add(key)
    return knives,defaults


def rolling_sculpt_backtest(history: list[str], config: Configuration, *,
                            k: int = 100, warmup: int = 80, max_periods: int = 20,
                            strength: float = 1.0, basic: Sequence[BasicConstraint] = (),
                            basic_catalog=None, target_only: bool = False) -> dict:
    """Exploratory walk-forward evaluation, generates rules only from history[:t].

    Do not tune on this report and then claim it is an untouched validation set.
    """
    _valid_draw_numbers(history)
    if warmup < max(config.windows) or max_periods < 1 or not 1 <= k <= N:
        raise ValueError('回测参数无效')
    start = max(warmup,len(history)-max_periods)
    if start >= len(history): raise ValueError('历史不足')
    rows = []
    for t in range(start,len(history)):
        knives, defaults = knives_from_history(history[:t],config,basic,
                                                basic_catalog=basic_catalog,
                                                optimize_context=target_only)
        session = SculptSession(knives,enabled=defaults,seed=20261101)
        if target_only:
            ranked = session.rank_target_snapshot_v3717(k=k,strength=strength)
            target = history[t]
            actual = ranked.extract(target)
            meta = ranked.summary
        else:
            ranked, meta = session.rank(k=k,strength=strength)
            target = history[t]
            # Full rank computed without the target; locate actual only AFTER ranking.
            actual = ranked.loc[ranked['number'] == target].iloc[0]
        rows.append({'draw_index':t,'actual':target,'rank':int(actual['rank']),
                     'top_k_hit':bool(actual['selected_top_k']),
                     'hard_kept':bool(actual['hard_kept']),
                     'hard_keep_size':meta['kept'],
                     'rescued_for_quota':meta['restored_for_quota'],
                     'rules':meta['active']})
    hits = sum(r['top_k_hit'] for r in rows)
    n = len(rows)
    return {'periods':n,'k':k,'hits':hits,'observed_hit_rate':hits/n,
            'fair_expected_hits':n*k/N,'fair_hit_rate':k/N,
            'fair_10_draw_at_least_one':1-(1-k/N)**10,
            'exploratory_only':True,
            'note':'逐期训练数据截至t-1；仍是可重复调参的探索性回测，非独立前瞻验证。',
            'details':rows}
