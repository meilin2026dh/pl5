"""PL5 多空间并行实验、竞争诊断与完整10万号码的启发式排序。

统计意义：反延续是一种用户定义的集合偏好，不是历史事件改变随机开奖概率的证据。
研究规则来源与数据源的信任隔离由其它模块负责。这里绝不调用网络或运行外部代码。
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable
import hashlib
import math

import numpy as np
import pandas as pd

from .engine import UNIVERSE
from .pattern_rules import (
    Configuration, Rule, PATTERNS, CONTEXT_INDICATORS, filter_next,
    historical_indicators, indicator_values, _context_values, _transform,
    _valid_draw_numbers,
)
from .probability_ranker import rule_key
from .space_mapping import SPACES, register_space_indicators

ORIGINAL_SPACE = 'pl5'
DISPLAY = {'pl5': '排列五原始空间', **{k: s.label for k, s in SPACES.items()}}


def space_of_indicator(indicator: str) -> str:
    for name in SPACES:
        if indicator.startswith(name + '__'):
            return name
    return ORIGINAL_SPACE


def select_indicators(indicators: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    """按用户选择的空间和指标建立唯一、可复现的注册表。"""
    register_space_indicators()
    names = []
    from .pattern_rules import indicator_table, EXTRA_INDICATORS
    valid = set(indicator_table()) | set(EXTRA_INDICATORS) | set(CONTEXT_INDICATORS)
    for space, metrics in indicators.items():
        if space not in DISPLAY:
            raise ValueError(f'未知空间: {space}')
        for metric in metrics:
            key = metric if space == ORIGINAL_SPACE else f'{space}__{metric}'
            if key not in valid or space_of_indicator(key) != space:
                raise ValueError(f'空间 {space} 不支持指标 {metric}')
            if key not in names:
                names.append(key)
    if not names:
        raise ValueError('至少选择一个指标')
    return tuple(names)


def _spacewise_rules(history: list[str], indicators: dict[str, tuple[str,...]],
                     windows:tuple[int,...],patterns:tuple[str,...],
                     transforms:tuple[str,...],max_rules:int) -> tuple[list[Rule], list[Rule]]:
    """先按空间独立发现规则，再轮询竞争名额；禁止一空间提前耗尽全局配额。"""
    by_space: dict[str,list[Rule]] = {}
    all_rules=[]
    for space,metric_names in indicators.items():
        if not metric_names: continue
        names=select_indicators({space:metric_names})
        config=Configuration(indicators=names,windows=windows,patterns=patterns,
                             transforms=transforms,max_rules=max_rules)
        out=filter_next(history,config)
        by_space[space]=[r for r in out.rules if r.status=='applied']
        all_rules.extend(out.rules)
    # 同一空间内部按旧版的覆盖率顺序；不同空间交替使用名额。
    chosen=[]
    while len(chosen)<max_rules and any(by_space.values()):
        for space in indicators:
            if by_space.get(space):
                chosen.append(by_space[space].pop(0))
                if len(chosen)>=max_rules: break
    return all_rules, chosen


def _candidate_signal(rule: Rule, past: np.ndarray, cached: dict) -> np.ndarray:
    key = (rule.indicator, rule.transform)
    if key not in cached:
        if rule.indicator in CONTEXT_INDICATORS:
            values = _context_values(rule.indicator, past)[1]
        else:
            values = indicator_values(rule.indicator, 'raw')
        cached[key] = _transform(values, rule.transform)
    return np.isin(cached[key], rule.banned_values)


def _competition(rules: list[Rule], masks: list[np.ndarray], max_pairs: int) -> tuple[list[dict], dict]:
    """规则覆盖、边际贡献及跨空间相关性。按固定顺序审计，不靠择优回测选择。"""
    N = len(UNIVERSE)
    taken = np.zeros(N, dtype=bool)
    rows: list[dict] = []
    space_union: dict[str, np.ndarray] = {}
    for r, m in zip(rules, masks):
        sp = space_of_indicator(r.indicator)
        space_union.setdefault(sp, np.zeros(N, dtype=bool))
        space_union[sp] |= m
        novel = m & ~taken
        newly_removed = int(novel.sum())
        intersection = int((m & taken).sum())
        rows.append({
            'rule_key': rule_key(r), 'space': sp, 'indicator': r.indicator,
            'transform': r.transform, 'pattern': r.pattern, 'window': r.window,
            'raw_exclusions': int(m.sum()), 'raw_coverage': float(m.mean()),
            'marginal_exclusions': newly_removed,
            'marginal_coverage': newly_removed / N,
            'redundancy_vs_prior': intersection / max(1, int(m.sum())),
            'rule_status': r.status,
        })
        taken |= m
    # 用空间组合的交并指标，避免将两个空间的规则视为独立概率证据。
    overlaps: list[dict] = []
    keys = list(space_union)
    for a, b in combinations(keys, 2):
        ma, mb = space_union[a], space_union[b]
        intersection = int((ma & mb).sum())
        union = int((ma | mb).sum())
        p_a, p_b = float(ma.mean()), float(mb.mean())
        denom = math.sqrt(p_a * (1-p_a) * p_b * (1-p_b))
        overlaps.append({
            'space_a': a, 'space_b': b, 'intersection': intersection,
            'union': union, 'jaccard': intersection / union if union else 0.,
            'phi_correlation': (intersection / N - p_a*p_b)/denom if denom else None,
            'independent_expected_intersection': N*p_a*p_b,
        })
    # 每对规则都可审计；超过max_pairs时按有意义的重叠度排序显示前几项。
    pairwise = []
    for i, j in combinations(range(len(masks)), 2):
        mi, mj = masks[i], masks[j]
        inter = int((mi & mj).sum())
        union = int((mi | mj).sum())
        if union:
            pairwise.append({'rule_a': rule_key(rules[i]), 'rule_b': rule_key(rules[j]),
                             'space_a': space_of_indicator(rules[i].indicator),
                             'space_b': space_of_indicator(rules[j].indicator),
                             'intersection': inter, 'jaccard': inter / union})
    pairwise.sort(key=lambda r: (-r['jaccard'], r['rule_a'], r['rule_b']))
    summary = {
        'total_union_removed': int(taken.sum()),
        'total_union_coverage': float(taken.mean()),
        'per_space': {key: {'rules': sum(space_of_indicator(r.indicator)==key for r in rules),
                            'union_excluded': int(mask.sum()),
                            'union_coverage': float(mask.mean())}
                      for key, mask in space_union.items()},
        'space_overlap': overlaps,
        'top_rule_overlaps': pairwise[:max_pairs],
        'pairwise_total': len(pairwise),
    }
    return rows, summary


@dataclass
class ParallelResult:
    table: pd.DataFrame
    rule_table: pd.DataFrame
    competition: dict
    metadata: dict
    history_table: pd.DataFrame

    def top(self, count: int = 1000) -> pd.DataFrame:
        if not 1 <= count <= 100_000:
            raise ValueError('count须在1到100000之间')
        return self.table.head(count)


def multi_space_study(
    history: list[str], indicators: dict[str, tuple[str, ...]], *,
    windows: tuple[int, ...] = (3, 4),
    patterns: tuple[str, ...] = ('constant', 'strict_up', 'strict_down', 'arithmetic', 'period2'),
    transforms: tuple[str, ...] = ('raw',),
    selected_rule_keys: Iterable[str] | None = None,
    strength: float = 1.0,
    max_rules: int = 35,
) -> ParallelResult:
    """各空间并行发现规则，统一诊断，再生成100000注的非校准启发式排序。"""
    if not np.isfinite(strength) or not 0 <= strength <= 8:
        raise ValueError('strength必须介于0..8')
    if not 1 <= max_rules <= 120:
        raise ValueError('max_rules须在1..120')
    past = _valid_draw_numbers(history)
    names = select_indicators(indicators)
    all_rules, recommended = _spacewise_rules(history, indicators, windows, patterns,
                                               transforms, max_rules)
    allowed = {rule_key(r) for r in all_rules}
    chosen = set(selected_rule_keys) if selected_rule_keys is not None else None
    if chosen is not None and not chosen.issubset(allowed):
        raise ValueError('包含本轮不存在的规则键，不能套用上一轮的选项')
    active = ([r for r in all_rules if rule_key(r) in chosen] if chosen is not None
              else recommended)
    # 安全上限既适用于自动选择，也适用于手工强制选择。
    if len(active) > max_rules:
        raise ValueError(f'最多选择{max_rules}条规则；可先缩小指标或模式范围')
    cache = {}
    masks = [_candidate_signal(r, past, cache) for r in active]
    rows, competition = _competition(active, masks, max_pairs=60)

    # 每个空间内部同一指标取最大惩罚；不同空间加权平均，而非独立概率证据相乘。
    # 将单规则覆盖率转换为轻量惩罚；不按“历史出现规律 => 下一期概率降低”解释。
    space_features: dict[str, dict[str, np.ndarray]] = {}
    by_space_count = {}
    for r, mask in zip(active, masks):
        space = space_of_indicator(r.indicator)
        by_space_count[space] = by_space_count.get(space, 0) + 1
        per_ind = space_features.setdefault(space, {})
        component = per_ind.setdefault(r.indicator, np.zeros(100_000, dtype=np.float32))
        weight = np.float32(np.sqrt(1.0 - float(mask.mean())))
        np.maximum(component, mask.astype(np.float32)*weight, out=component)
    scores = {}
    for space, comps in space_features.items():
        # 指标平均，规避某空间因为注册指标更多而被过度加权。
        scores[space] = sum(comps.values(), start=np.zeros(100_000,dtype=np.float32)) / max(1,len(comps))
    penalty = (sum(scores.values(), start=np.zeros(100_000,dtype=np.float32)) / len(scores)
               if scores else np.zeros(100_000, dtype=np.float32))
    hit_count = np.zeros(100_000, dtype=np.int16)
    for mask in masks: hit_count += mask.astype(np.int16)
    logits = -strength * penalty.astype(np.float64)
    weights = np.exp(logits-logits.max())
    probs = weights / weights.sum()
    order = np.lexsort((UNIVERSE, penalty))
    data = {
        'rank': np.arange(1,100_001,dtype=np.int32),
        'number': [f'{int(n):05d}' for n in UNIVERSE[order]],
        'heuristic_score': np.round(-penalty[order], 7),
        'model_weight': probs[order],
        'fair_probability': np.full(100_000,1e-5),
        'rule_hits': hit_count[order],
    }
    for space in indicators:
        data['penalty_'+space] = scores.get(space,np.zeros(100_000,dtype=np.float32))[order]
    config_signature = hashlib.sha256(repr((names,windows,patterns,transforms,strength,max_rules)).encode()).hexdigest()
    meta = {'history_length':len(history), 'spaces':list(indicators),
            'indicators':list(names), 'detected_rules':len(all_rules),
            'accepted_rules':len(active), 'config_sha256':config_signature,
            'model_weights_sum':float(probs.sum()),
            'fair_each_number_probability':1e-5,
            'note':'排序是未校准的用户偏好；公平独立开奖下真实中奖概率均为1/100000。'}
    recent = historical_indicators(history, names)
    return ParallelResult(pd.DataFrame(data),pd.DataFrame(rows),competition,meta,pd.DataFrame(recent))


def competition_backtest(
    history: list[str], indicators: dict[str, tuple[str,...]], *,
    windows: tuple[int,...]=(3,4),
    patterns: tuple[str,...]=('constant','strict_up','strict_down','arithmetic','period2'),
    transforms: tuple[str,...]=('raw',),
    warmup:int=40, max_periods:int=20, max_rules:int=35,
) -> dict:
    """按规则结构签名、空间做严格过去信息滚动对照。

    该报告是探索性样本外回测，不能对调参过程中重复使用的历史样本宣称统计显著性。
    每条规则的expected_removed是其当期候选集合占比的合计。
    """
    ids=_valid_draw_numbers(history)
    names=select_indicators(indicators)
    cfg=Configuration(indicators=names,windows=windows,patterns=patterns,
                      transforms=transforms,max_rules=max_rules)
    cfg.validate()
    if warmup<max(cfg.windows) or max_periods<1:
        raise ValueError('历史长度或回测窗口参数错误')
    start=max(warmup,len(ids)-max_periods)
    if start>=len(ids):
        raise ValueError('没有可供回测的开奖期数')
    spaces = list(indicators)
    template_stats={}
    sp_stats={sp:{'space':sp,'observed_excluded':0,'expected_excluded':0.,
                  'active_periods':0,'periods':0} for sp in spaces}
    detail=[]
    for t in range(start,len(ids)):
        past=ids[:t]
        actual=int(ids[t])
        detected, recommended = _spacewise_rules(history[:t], indicators, windows,
                                                   patterns, transforms,max_rules)
        recommended_keys={rule_key(r) for r in recommended}
        cache={}
        unions={sp:np.zeros(100000,dtype=bool) for sp in spaces}
        for rule in detected:
            sp=space_of_indicator(rule.indicator)
            if sp not in sp_stats: continue
            structural=(rule.indicator,rule.transform,rule.pattern,rule.window)
            stat=template_stats.setdefault(structural,{
                'space':sp,'indicator':rule.indicator,'transform':rule.transform,
                'pattern':rule.pattern,'window':rule.window,
                'triggered_periods':0,'applied_periods':0,
                'observed_excluded_if_triggered':0,'expected_excluded_if_triggered':0.,
                'observed_excluded_if_applied':0,'expected_excluded_if_applied':0.,
            })
            stat['triggered_periods']+=1
            mask=_candidate_signal(rule,past,cache)
            covered=bool(mask[actual])
            rate=float(mask.mean())
            stat['observed_excluded_if_triggered']+=int(covered)
            stat['expected_excluded_if_triggered']+=rate
            if rule_key(rule) in recommended_keys:
                stat['applied_periods']+=1
                stat['observed_excluded_if_applied']+=int(covered)
                stat['expected_excluded_if_applied']+=rate
                unions[sp]|=mask
        record={'index':t,'actual':history[t]}
        for sp,mask in unions.items():
            s=sp_stats[sp]
            present=bool(mask.any())
            s['active_periods']+=int(present)
            s['periods']+=1
            s['observed_excluded']+=int(mask[actual])
            s['expected_excluded']+=float(mask.mean())
            record[sp+'_excluded']=bool(mask[actual])
            record[sp+'_expected_exclusion']=float(mask.mean())
        detail.append(record)
    for s in sp_stats.values():
        s['observed_exclusion_rate']=s['observed_excluded']/s['periods']
        s['random_expected_exclusion_rate']=s['expected_excluded']/s['periods']
    rows=list(template_stats.values())
    rows.sort(key=lambda r:(r['space'],r['indicator'],r['pattern'],r['window']))
    for r in rows:
        n=r['triggered_periods']
        r['observed_exclusion_rate_if_triggered']=r['observed_excluded_if_triggered']/n
        r['random_expected_exclusion_rate_if_triggered']=r['expected_excluded_if_triggered']/n
    return {'periods':len(detail),'warmup':warmup,'start_index':start,
            'per_space':list(sp_stats.values()),'per_rule':rows,'details':detail,
            'fair_baseline':'逐期剔除集合大小 / 100000；仅在规则事先固定且开奖独立均匀条件下成立',
            'note':'每期只使用其之前开奖构造规则。多算法尝试和重复回测导致选择偏差；本结果不是正式独立封存验证。'}
