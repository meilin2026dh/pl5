"""纯计算层：模型、证据门控和候选集生成。不使用未来开奖结果。"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
import numpy as np
from scipy.stats import chisquare, chi2_contingency

UNIVERSE = np.arange(100_000, dtype=np.int32)
DIGITS = np.stack([(UNIVERSE // (10 ** p)) % 10 for p in (4, 3, 2, 1, 0)], axis=1).astype(np.uint8)
PAIRS = tuple(combinations(range(5), 2))
MODELS = ('positional', 'pairwise', 'ensemble', 'random')
MODEL_LABELS = {'positional':'位置贝叶斯平滑', 'pairwise':'双位置联合关联', 'ensemble':'双模型融合', 'random':'均匀随机对照'}


def _history_array(history: list[str]) -> np.ndarray:
    if not history:
        raise ValueError('训练样本为空。')
    return np.asarray([[int(c) for c in row] for row in history], dtype=np.uint8)


def score_candidates(history: list[str], model: str) -> np.ndarray:
    """输出相对排名分数，不是校准概率。"""
    if model not in MODELS or model == 'random':
        raise ValueError('该模型不需要/不支持分数。')
    arr = _history_array(history)
    n = len(arr)
    pos = np.zeros(100_000, dtype=np.float64)
    for p in range(5):
        counts = np.bincount(arr[:, p], minlength=10)
        logp = np.log((counts + 1.0) / (n + 10.0))
        pos += logp[DIGITS[:, p]] / 5.0
    if model == 'positional':
        return pos
    pair = np.zeros(100_000, dtype=np.float64)
    for p, q in PAIRS:
        counts = np.bincount(arr[:, p].astype(np.int32)*10 + arr[:, q], minlength=100)
        logp = np.log((counts + 1.0) / (n + 100.0))
        pair += logp[DIGITS[:, p].astype(np.int32)*10 + DIGITS[:, q]] / len(PAIRS)
    if model == 'pairwise':
        return pair
    # 标准化后再融合，避免不同模型量纲和尺度影响权重。
    def z(x: np.ndarray) -> np.ndarray:
        scale = x.std()
        return (x - x.mean()) / scale if scale > 1e-12 else np.zeros_like(x)
    return 0.5*z(pos) + 0.5*z(pair)


def evidence_gate(history: list[str], model: str, alpha: float = 0.01) -> dict:
    """检测训练集是否出现基本非均匀性；不是获利或预测优势的证明。

    检验含 5 个位置均匀性、10 个两位置独立性，统一做 Bonferroni 校正。
    两位置卡方检验须所有期望格计数>=5，才纳入，避免小样本失真。
    """
    if model == 'random':
        return {'active':False, 'p_adjusted':None, 'reason':'均匀随机模型无需门控', 'tests':0}
    a = _history_array(history)
    n = len(a)
    tests: list[tuple[str, str, float]] = []
    for j in range(5):
        counts = np.bincount(a[:, j], minlength=10)
        p = float(chisquare(counts).pvalue)
        tests.append(('positional', f'位置{j+1}均匀性', p))
    for j,k in PAIRS:
        if n < 500:
            continue
        counts = np.bincount(a[:, j].astype(np.int32)*10 + a[:, k], minlength=100).reshape((10,10))
        row = counts.sum(axis=1, keepdims=True)
        col = counts.sum(axis=0, keepdims=True)
        expected = row @ col / n
        if expected.min() < 5:
            continue
        p = float(chi2_contingency(counts, correction=False)[1])
        tests.append(('pairwise', f'位置{j+1}-{k+1}独立性', p))
    relevant = {'positional'} if model == 'positional' else ({'pairwise'} if model == 'pairwise' else {'positional','pairwise'})
    selected = [(name,p) for family, name, p in tests if family in relevant]
    if not selected:
        return {'active':False,'p_adjusted':None,'reason':'两位置检验样本量不足，不能启用证据门控','tests':len(tests)}
    label, raw_p = min(selected, key=lambda t:t[1])
    # 按预先约定的15个潜在检验校正，即使部分检验因样本不足未运行也保持保守。
    p_adj = min(1.,raw_p*15)
    active = bool(p_adj < alpha)
    reason = (f'{label}检验经多重比较校正后低于阈值；仅说明训练样本有统计异常，仍需样本外验证'
              if active else '未达到预设异常检测阈值；自动退回随机对照')
    return {'active':active,'p_adjusted':float(p_adj),'reason':reason,'tests':len(tests)}


@dataclass
class Selection:
    numbers: np.ndarray
    model: str
    gate: dict
    gated_fallback: bool


def select_numbers(history: list[str], *, count: int, model: str, seed: int = 42,
                   use_gate: bool = True, alpha: float = 0.01) -> Selection:
    if not 1 <= count <= 100_000:
        raise ValueError('count 必须处于1至100000。')
    if model not in MODELS:
        raise ValueError(f'未知模型：{model}')
    gate = evidence_gate(history, model, alpha) if use_gate else {
        'active': model!='random','p_adjusted':None,'reason':'用户选择关闭证据门控（探索模式）','tests':0}
    fallback = model == 'random' or (use_gate and not gate['active'])
    if fallback:
        picks = np.random.default_rng(seed).choice(100_000, count, replace=False).astype(np.int32)
    else:
        score = score_candidates(history, model)
        # 排名并列时，基于固定种子打散，避免固定偏好较小编号。
        rng = np.random.default_rng(seed)
        score = score + rng.uniform(0, 1e-11, score.size)
        picks = np.argpartition(-score, count - 1)[:count].astype(np.int32)
    return Selection(np.sort(picks), model, gate, fallback)


def formatted_numbers(nums: np.ndarray) -> list[str]:
    return [f'{int(x):05d}' for x in nums]
