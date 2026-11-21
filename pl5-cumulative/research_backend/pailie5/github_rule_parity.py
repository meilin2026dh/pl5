"""Independent Python implementations of 12 canonical 五序 (GitHub) basic rules.

All 100000 five-digit values are checked, rather than just a sparse sample.
This verifies *known simple rules* only. The advanced TS-only methods remain unverified.
"""
from __future__ import annotations
from functools import lru_cache
from typing import Any
import numpy as np

N = 100_000
SUPPORTED = frozenset({
    "sum", "tail", "span", "odd", "big", "prime", "distinct",
    "repeat", "consecutive", "sumMod3", "dan", "kill",
})

@lru_cache(maxsize=1)
def digits_table() -> np.ndarray:
    ids = np.arange(N, dtype=np.int32)
    return ((ids[:, None] // np.array([10000,1000,100,10,1])) % 10).astype(np.uint8)

@lru_cache(maxsize=None)
def metric_values(kind: str) -> np.ndarray:
    if kind not in SUPPORTED - {"dan", "kill"}:
        raise ValueError("未实现该基础指标")
    d = digits_table()
    sums = d.sum(axis=1)
    if kind == "sum": return sums
    if kind == "tail": return sums % 10
    if kind == "sumMod3": return sums % 3
    if kind == "span": return d.max(axis=1) - d.min(axis=1)
    if kind == "odd": return (d % 2 == 1).sum(axis=1)
    if kind == "big": return (d >= 5).sum(axis=1)
    # Crucial difference: the GitHub lottery category calls 1 a "prime-class" digit.
    if kind == "prime": return np.isin(d, [1, 2, 3, 5, 7]).sum(axis=1)
    present = np.stack([(d == i).any(axis=1) for i in range(10)], axis=1)
    if kind == "distinct": return present.sum(axis=1)
    if kind == "consecutive": return (present[:,1:] & present[:,:-1]).sum(axis=1)
    if kind == "repeat":
        counts = np.stack([(d == i).sum(axis=1) for i in range(10)], axis=1)
        counts = -np.sort(-counts, axis=1)
        return np.array(["".join(map(str, row[row > 0])) for row in counts])
    raise AssertionError(kind)

def _number_values(values: Any, kind: str) -> list[int]:
    if not isinstance(values, list) or not values:
        raise ValueError(f"{kind}必须传入非空取值数组")
    if any(type(v) is not int for v in values):
        raise ValueError(f"{kind}只允许整数值")
    return values

def evaluate_basic(rule: dict[str, Any]) -> np.ndarray | None:
    """Return a 100000-element boolean keep mask; None for unsupported TS rules."""
    if not isinstance(rule, dict):
        raise ValueError("rule_spec必须是对象")
    kind = rule.get("kind")
    if kind not in SUPPORTED:
        return None
    mode = rule.get("mode")
    if mode not in ("include", "exclude"):
        raise ValueError("rule_spec.mode非法")
    values = rule.get("values")
    if kind == "repeat":
        if not isinstance(values, list) or not values or any(type(v) is not str for v in values):
            raise ValueError("repeat规则值必须是字符串数组")
        result = np.isin(metric_values(kind), values)
    elif kind == "dan":
        selected = set(_number_values(values,kind))
        if any(v < 0 or v > 9 for v in selected): raise ValueError("胆码取值超出0—9")
        params = rule.get("params") or {}
        if not isinstance(params, dict): raise ValueError("胆码参数不合法")
        low, high = params.get("countMin",1),params.get("countMax",5)
        if type(low) is not int or type(high) is not int or not (0 <= low <= high <= 5):
            raise ValueError("胆码命中种数范围非法")
        hit = np.zeros(N, dtype=np.int8)
        d = digits_table()
        for value in selected: hit += (d == value).any(axis=1).astype(np.int8)
        result = (hit >= low) & (hit <= high)
    elif kind == "kill":
        selected = _number_values(values,kind)
        if any(v < 0 or v > 9 for v in selected): raise ValueError("杀号超出0—9")
        result = ~np.isin(digits_table(), selected).any(axis=1)
    else:
        result = np.isin(metric_values(kind), _number_values(values,kind))
    return np.logical_not(result) if mode == "exclude" else result
