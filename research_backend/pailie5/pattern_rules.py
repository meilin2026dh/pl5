"""PL5 V0.3：指标时序模式研究引擎（不宣称彩票预测优势）。

所有规律必须由过去期号的数据构造；候选号码是假设下期可能出现的10万个结果。
纯NumPy向量化；每条规则可追溯，且有最大剔除比例与最少保留数保护。
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from functools import lru_cache
from collections import OrderedDict
from typing import Callable
import numpy as np

from .engine import DIGITS, UNIVERSE


@dataclass(frozen=True)
class Configuration:
    indicators: tuple[str, ...] = ("sum", "span", "odd_count", "unique_count", "adjacent_equal", "high_count", "digit_5", "digit_1", "head_sum", "tail_sum", "adjacent_up", "adjacent_down", "max_frequency", "first_last_gap", "adjacent_consecutive", "same_positions_prev", "digit_overlap_prev", "sum_delta_prev")
    transforms: tuple[str, ...] = ("raw", "mod2", "mod3", "mod5", "mod10")
    patterns: tuple[str, ...] = ("constant", "strict_up", "strict_down", "arithmetic", "period2", "period3", "zigzag")
    windows: tuple[int, ...] = (3, 4)
    mode: str = "continuation"   # continuation / recurrence
    lookback: int = 12          # recurrence：往前检查多少期曾发生同类模式
    max_rule_remove: float = 0.65  # 单条规则最多剔除多少比例，否则跳过
    max_total_remove: float = 0.80 # 所有规则最多剔除多少比例
    min_keep: int = 1000
    max_rules: int = 120

    def validate(self) -> None:
        table = indicator_table()
        for name in self.indicators:
            if name not in table and name not in EXTRA_INDICATORS and name not in CONTEXT_INDICATORS: raise ValueError(f"未知指标：{name}")
        if not self.indicators: raise ValueError("至少需要一个指标")
        if not self.transforms or any(t not in ("raw", "mod2", "mod3", "mod5", "mod10") for t in self.transforms):
            raise ValueError("不支持的指标变换")
        if not self.patterns or any(p not in PATTERNS for p in self.patterns):
            raise ValueError("不支持的模式")
        if not self.windows or any(w < 3 or w > 12 for w in self.windows):
            raise ValueError("窗口应为3至12")
        if self.mode not in ("continuation", "recurrence"):
            raise ValueError("mode只允许continuation或recurrence")
        if self.lookback < max(self.windows):
            raise ValueError("lookback须大于等于最大窗口长度")
        if not (0 < self.max_rule_remove <= 1 and 0 < self.max_total_remove < 1):
            raise ValueError("剔除比例必须在合理范围")
        if not (1 <= self.min_keep <= 100_000): raise ValueError("最少保留数越界")
        if not 1 <= self.max_rules <= 10000: raise ValueError("max_rules越界")


@lru_cache(maxsize=1)
def indicator_table() -> dict[str, np.ndarray]:
    """一次性计算完整10万号码的指标。用户可通过register_indicator扩展。"""
    a = DIGITS.astype(np.int16)
    dif = np.diff(a, axis=1)
    occurrences = np.stack([(a == digit).sum(axis=1) for digit in range(10)], axis=1)
    table = OrderedDict({
        "sum": a.sum(axis=1),
        "span": a.max(axis=1) - a.min(axis=1),
        "odd_count": (a % 2 == 1).sum(axis=1),
        "high_count": (a >= 5).sum(axis=1),
        "unique_count": (occurrences > 0).sum(axis=1),
        "adjacent_equal": (dif == 0).sum(axis=1),
        "adjacent_up": (dif > 0).sum(axis=1),
        "adjacent_down": (dif < 0).sum(axis=1),
        "adjacent_consecutive": (np.abs(dif) == 1).sum(axis=1),
        "max_frequency": occurrences.max(axis=1),
        "first_last_gap": np.abs(a[:, 0] - a[:, 4]),
        "head_sum": a[:, :2].sum(axis=1),
        "tail_sum": a[:, 3:].sum(axis=1),
        "middle_sum": a[:, 1:4].sum(axis=1),
        "even_position_sum": a[:, [1, 3]].sum(axis=1),
        "odd_position_sum": a[:, [0, 2, 4]].sum(axis=1),
        "mirror_pairs": (a[:, 0] == a[:, 4]).astype(np.int16) + (a[:, 1] == a[:, 3]).astype(np.int16),
        "inner_span": a[:, 1:4].max(axis=1) - a[:, 1:4].min(axis=1),
    })
    for i in range(5):
        table[f"digit_{i + 1}"] = a[:, i]
    return {k: np.asarray(v, dtype=np.int16) for k, v in table.items()}


EXTRA_INDICATORS: dict[str, np.ndarray] = {}


def _shared_multiset(curr: np.ndarray, prev: np.ndarray) -> np.ndarray:
    """两期相同数字的多重集合交集数量（重复数字分别计数）。"""
    shared = np.zeros(len(curr),dtype=np.int16)
    for digit in range(10):
        ca = (curr == digit).sum(axis=1)
        cb = (prev == digit).sum(axis=1)
        shared += np.minimum(ca,cb)
    return shared


CONTEXT_INDICATORS: dict[str, Callable[[np.ndarray, np.ndarray], np.ndarray]] = {
    "same_positions_prev": lambda a,b: np.sum(a == b, axis=1),
    "same_parity_positions_prev": lambda a,b: np.sum((a%2)==(b%2),axis=1),
    "digit_overlap_prev": _shared_multiset,
    "sum_delta_prev": lambda a,b: a.astype(np.int16).sum(axis=1)-b.astype(np.int16).sum(axis=1),
    "span_delta_prev": lambda a,b: (a.max(axis=1)-a.min(axis=1)).astype(np.int16)-(b.max(axis=1)-b.min(axis=1)).astype(np.int16),
    "lastdigit_delta_prev": lambda a,b: a[:,4].astype(np.int16)-b[:,4].astype(np.int16),
}


def register_context_indicator(name: str, fn: Callable[[np.ndarray,np.ndarray],np.ndarray]) -> None:
    """由可信本地开发人员注册跨期指标，禁止直接执行网上发现的源码。"""
    if name in indicator_table() or name in EXTRA_INDICATORS or name in CONTEXT_INDICATORS:
        raise ValueError(f'指标名称重复：{name}')
    sample = np.asarray(fn(DIGITS[:10], DIGITS[1:11]))
    if sample.shape != (10,) or not np.issubdtype(sample.dtype,np.integer):
        raise ValueError('自定义跨期指标必须返回一维整数数组')
    CONTEXT_INDICATORS[name] = fn


def _context_values(name: str, past: np.ndarray) -> tuple[np.ndarray,np.ndarray]:
    """返回历史各期跨期指标、候选相对最新已知开奖的跨期指标。"""
    fn=CONTEXT_INDICATORS[name]
    past_digits = DIGITS[past]
    history_values = np.asarray(fn(past_digits[1:], past_digits[:-1]),dtype=np.int32)
    candidate_values = np.asarray(fn(DIGITS, np.broadcast_to(past_digits[-1],DIGITS.shape)), dtype=np.int32)
    if history_values.shape != (len(past)-1,) or candidate_values.shape != (100_000,):
        raise ValueError(f'跨期指标 {name} 计算结果形状不正确')
    return history_values,candidate_values


def _transform(v: np.ndarray, transform: str) -> np.ndarray:
    return v if transform == 'raw' else v % int(transform[3:])


def register_indicator(name: str, fn: Callable[[np.ndarray], np.ndarray]) -> None:
    """通过受信任的本地Python插件注册指标。禁止直接运行网页/论文附带代码。"""
    if name in indicator_table() or name in EXTRA_INDICATORS:
        raise ValueError(f"指标名称重复：{name}")
    values = np.asarray(fn(DIGITS.copy()))
    if values.shape != (100_000,) or not np.issubdtype(values.dtype, np.integer):
        raise ValueError("自定义指标必须返回长度10万的一维整数数组")
    if not np.all(np.isfinite(values)):
        raise ValueError("指标包含非法数值")
    EXTRA_INDICATORS[name] = values.astype(np.int32)


def indicator_values(name: str, transform: str) -> np.ndarray:
    if name in EXTRA_INDICATORS: v = EXTRA_INDICATORS[name]
    else: v = indicator_table()[name]
    if transform == "raw": return v
    return v % int(transform[3:])


def _constant(seq: np.ndarray) -> bool:
    return bool(np.all(seq == seq[0]))


def _strict_up(seq: np.ndarray) -> bool:
    return bool(np.all(np.diff(seq) > 0))


def _strict_down(seq: np.ndarray) -> bool:
    return bool(np.all(np.diff(seq) < 0))


def _arithmetic(seq: np.ndarray) -> bool:
    dif = np.diff(seq)
    return bool(dif[0] != 0 and np.all(dif == dif[0]))


def _period2(seq: np.ndarray) -> bool:
    return bool(len(seq) >= 4 and len(set(int(v) for v in seq[:2])) > 1 and np.all(seq[2:] == seq[:-2]))


def _period3(seq: np.ndarray) -> bool:
    return bool(len(seq) >= 6 and len(set(int(v) for v in seq[:3])) > 1 and np.all(seq[3:] == seq[:-3]))


def _zigzag(seq: np.ndarray) -> bool:
    dif = np.diff(seq)
    return bool(np.all(dif != 0) and np.all(np.sign(dif[1:]) == -np.sign(dif[:-1])))


def _few_distinct(seq: np.ndarray) -> bool:
    # 过度频繁的二值指标不可一票否决，交给max_rule_remove护栏。
    return bool(len(set(int(v) for v in seq)) <= 2)


PATTERNS: dict[str, Callable[[np.ndarray], bool]] = {
    "constant": _constant, "strict_up": _strict_up, "strict_down": _strict_down,
    "arithmetic": _arithmetic, "period2": _period2, "period3": _period3,
    "zigzag": _zigzag, "few_distinct": _few_distinct,
}
PATTERN_CN = {"constant":"连续同值", "strict_up":"严格递增", "strict_down":"严格递减",
              "arithmetic":"等差推进", "period2":"两期周期", "period3":"三期周期",
              "zigzag":"升降交替", "few_distinct":"低多样性（至多两值）"}


@dataclass
class Rule:
    indicator: str
    transform: str
    pattern: str
    window: int
    mode: str
    observed: list[int]
    banned_values: list[int]
    raw_removed: int
    raw_removed_rate: float
    removed_after_previous: int = 0
    status: str = "detected"
    reason: str = ""

    def as_dict(self) -> dict:
        data = asdict(self)
        data["label"] = f"{self.indicator}/{self.transform}：{PATTERN_CN[self.pattern]}"
        return data


@dataclass
class FilterResult:
    kept: np.ndarray
    removed: np.ndarray
    rules: list[Rule]
    triggered: int
    excluded_rules: int
    config: Configuration

    def summary(self) -> dict:
        return {"kept": int(len(self.kept)), "removed": int(len(self.removed)),
                "removed_rate": float(len(self.removed) / 100_000),
                "fair_random_coverage": float(len(self.kept) / 100_000),
                "triggered": self.triggered, "accepted_rules": sum(r.status == "applied" for r in self.rules),
                "excluded_rules": self.excluded_rules}


def _valid_draw_numbers(numbers: list[str]) -> np.ndarray:
    if not numbers: raise ValueError("开奖历史为空")
    if any(len(n) != 5 or not n.isascii() or not n.isdigit() for n in numbers):
        raise ValueError("每期必须是严格五位数字字符串，例如'00128'")
    return np.asarray([int(v) for v in numbers], dtype=np.int32)


def _candidate_rules(seq: np.ndarray, values: np.ndarray, config: Configuration, feature: str, transform: str) -> list[Rule]:
    generated: list[Rule] = []
    domain = np.unique(values)
    for w in config.windows:
        if len(seq) < w: continue
        for pname in config.patterns:
            if pname == "period2" and w < 4: continue
            if pname == "period3" and w < 6: continue
            detector = PATTERNS[pname]
            if config.mode == "continuation":
                observed = seq[-w:]
                if not detector(observed): continue
                # 必须使历史窗口w和下一期组成长度w+1的连续模式
                candidates = [int(v) for v in domain if detector(np.r_[observed, v])]
            else:
                recent = seq[-config.lookback:]
                if not any(detector(recent[i:i+w]) for i in range(len(recent) - w + 1)):
                    continue
                observed = seq[-(w-1):]
                # 必须使新一期形成同类型的w项模式（不要求绝对数值与此前一致）
                candidates = [int(v) for v in domain if detector(np.r_[observed, v])]
            if not candidates: continue
            removed = int(np.isin(values, candidates).sum())
            if removed == 0: continue
            generated.append(Rule(feature, transform, pname, w, config.mode,
                                  observed.tolist(), candidates, removed, removed / 100_000))
    return generated


def filter_next(history: list[str], config: Configuration | None = None, *,
                optimize_context: bool = False) -> FilterResult:
    """根据截至t期的历史构造下一期号码过滤集合。不依赖t+1开奖值。

    optimize_context=True reuses deterministic history-dependent indicators
    only within this invocation; there is no cache shared across draw periods.
    """
    config = config or Configuration()
    config.validate()
    past = _valid_draw_numbers(history)
    # 候选全域与历史号码共享相同的指标计算方式，避免训练/推理口径偏差。
    discovered: list[Rule] = []
    context_raw: dict[str, tuple[np.ndarray,np.ndarray]] = {}
    feature_cache: dict[tuple[str,str], np.ndarray] = {}
    for name in config.indicators:
        for transform in config.transforms:
            if name in CONTEXT_INDICATORS:
                if optimize_context:
                    if name not in context_raw:
                        context_raw[name] = _context_values(name, past)
                    raw_history, raw_feature = context_raw[name]
                else:
                    raw_history, raw_feature = _context_values(name, past)
                feature_values = _transform(raw_feature,transform)
                history_values = _transform(raw_history,transform)
            else:
                feature_values = indicator_values(name, transform)
                history_values = feature_values[past].astype(np.int32)
            if optimize_context:
                feature_cache[(name,transform)] = feature_values
            discovered.extend(_candidate_rules(history_values, feature_values, config, name, transform))
    # 去除同指标、变换、模式在不同窗口里生成的相同删号集合，避免虚假"多规则"。
    uniques: list[Rule] = []
    seen: set[tuple] = set()
    for r in discovered:
        key = (r.indicator, r.transform, tuple(r.banned_values))
        if key in seen: continue
        seen.add(key)
        uniques.append(r)
    # 优先应用排除范围窄的规则；相同范围按名称排序，确保重复运行可复现。
    uniques.sort(key=lambda r: (r.raw_removed, r.indicator, r.transform, r.pattern, r.window))
    kept_mask = np.ones(100_000, dtype=bool)
    min_keep = max(config.min_keep, int(np.ceil(100_000*(1 - config.max_total_remove))))
    for i, rule in enumerate(uniques):
        if i >= config.max_rules:
            rule.status, rule.reason = "skipped", "超过每轮最多参与规则数"
            continue
        if rule.raw_removed_rate > config.max_rule_remove:
            rule.status, rule.reason = "skipped", "单规则剔除比例超上限"
            continue
        if optimize_context:
            vals = feature_cache[(rule.indicator,rule.transform)]
        elif rule.indicator in CONTEXT_INDICATORS:
            vals = _transform(_context_values(rule.indicator,past)[1],rule.transform)
        else:
            vals = indicator_values(rule.indicator, rule.transform)
        would_remove = np.isin(vals, rule.banned_values) & kept_mask
        count = int(would_remove.sum())
        if count == 0:
            rule.status, rule.reason = "skipped", "与前面规则完全重叠"
        elif int(kept_mask.sum()) - count < min_keep:
            rule.status, rule.reason = "skipped", "触及最少保留数/总剔除比例保护"
        else:
            kept_mask[would_remove] = False
            rule.status, rule.removed_after_previous = "applied", count
            rule.reason = "按用户设定的启发式规则剔除；不代表概率下降"
    return FilterResult(UNIVERSE[kept_mask].copy(), UNIVERSE[~kept_mask].copy(),
                        uniques, len(discovered), sum(r.status == "skipped" for r in uniques), config)


def historical_indicators(history: list[str], names: tuple[str, ...]) -> list[dict]:
    past = _valid_draw_numbers(history)
    for name in names:
        if name not in indicator_table() and name not in EXTRA_INDICATORS and name not in CONTEXT_INDICATORS:
            raise ValueError(f"未知指标：{name}")
    computed = {}
    for name in names:
        computed[name] = (_context_values(name,past)[0] if name in CONTEXT_INDICATORS
                          else indicator_values(name,'raw')[past])
    rows=[]
    for t,n in enumerate(past):
        row={'number': f'{int(n):05d}'}
        for name in names:
            row[name] = (None if t==0 else int(computed[name][t-1])) if name in CONTEXT_INDICATORS else int(computed[name][t])
        rows.append(row)
    return rows


def rolling_backtest(history: list[str], config: Configuration | None = None, *,
                     warmup: int = 80, max_periods: int = 100) -> dict:
    """逐期前向回测；绝不使用待验证期及未来数据构造其过滤规则。"""
    config = config or Configuration()
    config.validate()
    _valid_draw_numbers(history)
    if warmup < max(config.windows): raise ValueError("warmup不足以建立窗口")
    if max_periods <= 0: raise ValueError("max_periods需要正整数")
    # 只回测最后max_periods期，且为每个t使用history[:t]
    start = max(warmup, len(history) - max_periods)
    if start >= len(history): raise ValueError("历史长度不足，无法滚动回测")
    rows = []
    for t in range(start, len(history)):
        r = filter_next(history[:t], config)
        actual = int(history[t])
        kept = bool(np.searchsorted(r.kept, actual) < len(r.kept) and
                    r.kept[min(np.searchsorted(r.kept, actual), len(r.kept)-1)] == actual)
        s = r.summary()
        rows.append({"index": t, "actual": history[t], "kept": kept,
                     "keep_rate": s["fair_random_coverage"], "rule_count": s["accepted_rules"],
                     "removed_rate": s["removed_rate"]})
    expected = sum(row["keep_rate"] for row in rows)
    observed = sum(row["kept"] for row in rows)
    variance = sum(row["keep_rate"]*(1-row["keep_rate"]) for row in rows)
    return {"periods": len(rows), "observed_keep": observed,
            "observed_keep_rate": float(observed / len(rows)),
            "random_expected_keep": float(expected),
            "random_expected_rate": float(expected / len(rows)),
            "standardized_difference_z": float((observed-expected)/np.sqrt(variance)) if variance else None,
            "note": "z仅用于描述与条件随机基线的差异；未做多重检验校正或独立封存验证，不得据此证明预测优势。",
            "details": rows}
