"""严格逐期开奖预测未来一期，且保留可解释的随机基线。"""
from __future__ import annotations
from dataclasses import dataclass
import math
import pandas as pd
from scipy.stats import binomtest
from .engine import select_numbers, MODELS
from .data import Draws

@dataclass
class Backtest:
    rows: pd.DataFrame
    summary: pd.DataFrame
    n_test: int
    count: int
    warnings: list[str]


def _wilson(hits: int, n: int, z: float = 1.9599639845) -> tuple[float, float]:
    p = hits / n
    d = 1 + z*z/n
    c = (p + z*z/(2*n))/d
    h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return max(0,c-h), min(1,c+h)


def run_backtest(draws: Draws, *, count: int = 1000, test_size: int = 100,
                 window: int = 500, min_train: int = 100, models: tuple[str, ...] = ('positional','pairwise','ensemble'),
                 seed: int = 42, use_gate: bool = True, alpha: float = 0.01) -> Backtest:
    if not all(m in MODELS for m in models) or not models:
        raise ValueError('模型列表无效。')
    if test_size < 1 or min_train < 20 or window < 20:
        raise ValueError('回测期数至少1期、训练样本及窗口至少20期。')
    if not 1 <= count <= 100_000:
        raise ValueError('候选注数范围错误。')
    frame = draws.frame
    n = len(frame)
    if n < min_train + 1:
        raise ValueError(f'至少需要 {min_train+1} 期数据（包含至少{min_train}期历史及1期测试）。当前只有{n}期。')
    start = max(min_train, n - test_size)
    out = []
    all_models = list(dict.fromkeys([*models, 'random']))
    for i in range(start,n):
        h = frame['number'].iloc[max(0, i-window):i].tolist()
        actual = int(frame['number'].iat[i])
        period = str(frame['period'].iat[i])
        for index, name in enumerate(all_models):
            chosen = select_numbers(h, count=count, model=name,
                                    seed=seed + i*101 + index*17, use_gate=use_gate, alpha=alpha)
            hit = bool((chosen.numbers == actual).any())
            out.append({'period':period, 'actual':f'{actual:05d}', 'model':name,
                        'hit':int(hit), 'fallback':int(chosen.gated_fallback),
                        'gate_p_adjusted':chosen.gate['p_adjusted']})
    rows = pd.DataFrame(out)
    baseline = count / 100_000
    summary = []
    hypothesis_count = max(1, len(set(models) - {'random'}))
    for name in all_models:
        r = rows.loc[rows['model']==name]
        ntest = len(r)
        hits = int(r['hit'].sum())
        low,high = _wilson(hits, ntest)
        pval = float(binomtest(hits, ntest, p=baseline, alternative='greater').pvalue)
        summary.append({'模型':name, '测试期数':ntest, '命中期数':hits,
                        '命中率':hits/ntest, '随机期望命中期数':baseline*ntest,
                        '95%置信区间下界':low, '95%置信区间上界':high,
                        '单模型单侧p值':pval,
                        'Bonferroni校正p值':min(1.,pval*hypothesis_count) if name!='random' else None,
                        '退回随机比例':float(r['fallback'].mean())})
    warnings = [
        '每期仅根据该期之前的数据构建候选集；没有使用未来开奖结果。',
        'p值是假定开奖独立均匀、且模型/参数未在测试集上反复挑选时的探索性结果；若多次调参，显著性会失真。',
        '当测试期数少、候选比例低时，命中率置信区间可能非常宽，不能凭少数命中证明预测优势。',
    ]
    if draws.is_demo:
        warnings.insert(0, '演示数据是伪随机的，不是真实开奖；结果没有实际预测意义。')
    return Backtest(rows, pd.DataFrame(summary), n-start, count, warnings)
