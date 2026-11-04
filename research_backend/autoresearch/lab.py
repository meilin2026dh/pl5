"""Bounded research hypothesis lab. Never treats historical patterns as predictive proof.

No code from papers/LLMs is executed. A hypothesis is a *safe configuration* of the
existing locally trusted indicator and pattern machinery. Any performance measures
are development-only until genuinely new draws prospectively validate the claim.
"""
from __future__ import annotations

from dataclasses import dataclass,asdict
from hashlib import sha256
import json
import math
import re
import numpy as np

from pailie5.pattern_rules import PATTERNS, CONTEXT_INDICATORS, indicator_values, _context_values, _transform
from pailie5.space_mapping import register_space_indicators
from pailie5.engine import UNIVERSE

INDICATOR_THEMES = {
 'sequential': [('sum','arithmetic',3),('digit_1','period2',4)],
 'conformal': [('odd_count','constant',3),('span','arithmetic',3)],
 'distribution': [('span','constant',3),('unique_count','strict_up',3)],
 'description': [('max_frequency','constant',3),('head_sum','arithmetic',3)],
 'randomness': [('sum','constant',3),('digit_5','arithmetic',3)],
 'combinatorial': [('pick23_6__sum','arithmetic',3),('pick41_4__span','constant',3)],
 'graphical': [('mirror_pairs','constant',3),('ternary11__count0','constant',3)],
 'scientific': [], # process improvement, no bogus lottery-rule extraction
}

# Aliases make discovery relevance auditable. None implies statistical evidence.
THEMES = {
 'sequential': ('sequential','online','changepoint','change point','e-value','multiple testing'),
 'conformal': ('conformal','coverage','uncertainty quantification'),
 'distribution': ('distribution shift','drift','anomaly detection'),
 'description': ('minimum description length','compressibility','information theory'),
 'randomness': ('randomness test','random number','prng','entropy'),
 'combinatorial': ('combinatorial','graph coloring','combinadic','permutation'),
 'graphical': ('graphical model','markov random field','bayesian network'),
 'scientific': ('autonomous research','scientific discovery','ai scientist','reproducibility'),
}

@dataclass(frozen=True)
class Hypothesis:
    indicator: str
    pattern: str
    window: int
    transform: str = 'raw'
    rationale: str = ''

    def validate(self):
        register_space_indicators()
        if self.indicator not in available_indicators():
            raise ValueError('尚未在受信任的本地注册表登记的指标')
        if self.pattern not in PATTERNS or self.transform not in ('raw','mod2','mod3','mod5','mod10'):
            raise ValueError('未知模式或转换类型')
        if not 3<=self.window<=12 or self.pattern=='period2' and self.window<4 or self.pattern=='period3' and self.window<6:
            raise ValueError('历史窗口与模式不匹配')

    def as_dict(self):return asdict(self)
    def fingerprint(self):
        self.validate()
        canonical = (self.indicator,self.pattern,self.window,self.transform)
        return sha256(json.dumps(canonical,ensure_ascii=False).encode()).hexdigest()[:20]


def available_indicators():
    from pailie5.pattern_rules import indicator_table, EXTRA_INDICATORS
    return set(indicator_table()) | set(EXTRA_INDICATORS) | set(CONTEXT_INDICATORS)


def relevance_score(paper) -> float:
    """Heuristic triage score, NOT probability of an algorithm succeeding."""
    text=(paper.title+' '+paper.abstract+' '+paper.topic).lower()
    points = 0
    for phrases in THEMES.values():
        points += min(2,sum(1 for x in phrases if x in text))
    if paper.source in ('arxiv','openalex'):points += 1
    if paper.abstract:points += 1
    if paper.source=='github' and len(paper.abstract)<25:points -= 1
    return max(0,float(points))


def propose(paper,*, max_proposals=2):
    """Translate topical leads into bounded experimental *ideas*, not paper claims.
    Designed to test whether a method transfers to PL5, not to assume it does.
    """
    register_space_indicators()
    text=(paper.title+' '+paper.abstract+' '+paper.topic).lower()
    matches=[]
    for theme,phrases in THEMES.items():
        if any(term in text for term in phrases):
            for ind,pattern,w in INDICATOR_THEMES[theme]:
                if ind not in available_indicators():continue
                spec=Hypothesis(ind,pattern,w,'raw',
                    f'源于 {paper.source} 的研究线索，迁移仅为待检验假设；主题={theme}，不能推断中奖概率提高')
                spec.validate()
                if spec.fingerprint() not in {s.fingerprint() for s in matches}:
                    matches.append(spec)
    return matches[:max_proposals]


def rule_mask(history:list[str], spec:Hypothesis, base_values=None):
    """Mask that would extend the latest historical pattern. False everywhere if no trigger.
    Works with all original and mapped registered indicators. History contains only PAST draws.
    """
    spec.validate()
    if any(len(x)!=5 or not x.isascii() or not x.isdigit() for x in history):
        raise ValueError('开奖必须是五位数字；不得使用未核验的数据')
    ids=np.fromiter((int(s) for s in history),dtype=np.int32,count=len(history))
    if len(history)<max(spec.window,3): return np.zeros(100_000,dtype=bool),False
    if spec.indicator in CONTEXT_INDICATORS:
        history_vals,candidate_vals=_context_values(spec.indicator,ids)
    else:
        if base_values is None: base_values=indicator_values(spec.indicator,'raw')
        history_vals=base_values[ids]
        candidate_vals=base_values
    seq=_transform(np.asarray(history_vals,dtype=np.int32),spec.transform)
    candidate_vals=_transform(np.asarray(candidate_vals,dtype=np.int32),spec.transform)
    recent=seq[-spec.window:]
    detector=PATTERNS[spec.pattern]
    if len(recent)<spec.window or not detector(recent):
        return np.zeros(100_000,dtype=bool),False
    domain=np.unique(candidate_vals)
    banned=[int(v) for v in domain if detector(np.r_[recent,v])]
    return np.isin(candidate_vals,banned),True


def rank_100(history:list[str], hypotheses:list[Hypothesis], *, k:int=100, salt:str='pl5-v05'):
    """Always returns exactly K distinct names; tie breaking is a fair random-like permutation.

    Unlike original V0.4's order=00000..99999 on identical penalties, avoids selecting
    lowest-number entries by accident. No claim of calibrated win probabilities.
    """
    if not 1<=k<=100:raise ValueError('本阶段目标候选集规模为1至100注')
    if not history:raise ValueError('历史数据为空')
    if any(len(s)!=5 or not s.isascii() or not s.isdigit() for s in history):raise ValueError('开奖格式错误')
    score=np.zeros(100_000,dtype=np.float32)
    evidence=[]
    seen=set()
    for spec in hypotheses[:24]:
        if spec.fingerprint() in seen:continue
        seen.add(spec.fingerprint())
        mask,trigger=rule_mask(history,spec)
        if trigger:
            # One rule, one vote. Correlations among rules are NOT independent evidence.
            score += mask.astype(np.float32) / max(1,len(hypotheses))
        evidence.append({'hypothesis':spec.fingerprint(),'triggered':bool(trigger),
                         'excluded':int(mask.sum()),'metric':spec.indicator})
    seed=int.from_bytes(sha256((salt+'|'+','.join(history[-25:])).encode()).digest()[:8],'big')
    tie=np.random.default_rng(seed).random(100_000)
    order=np.lexsort((tie,score))[:k]
    return [f'{int(v):05d}' for v in UNIVERSE[order]], evidence


def walk_forward(numbers:list[str], spec:Hypothesis, *, k:int=100,
                 min_train:int=50, eval_size:int=80):
    """Exploratory walk-forward only, always ranks before seeing target draw.

    This is NOT an independent sealed test; re-running it over the same data to select
    models leads to overfitting. Save independent future prospective holdout separately.
    """
    spec.validate()
    if any(len(n)!=5 or not n.isascii() or not n.isdigit() for n in numbers):
        raise ValueError('历史号码必须严格5位，不能缺失前导零')
    if len(numbers)<min_train+5:raise ValueError('数据太短，至少需要训练历史及5个测试期')
    start=max(min_train,len(numbers)-eval_size)
    hits=0; triggered=0; actual=[]
    for idx in range(start,len(numbers)):
        selected,ev=rank_100(numbers[:idx],[spec],k=k)
        hit=numbers[idx] in set(selected)
        hits+=bool(hit)
        triggered+=int(ev[0]['triggered'])
        actual.append({'index':idx,'hit':bool(hit),'triggered':ev[0]['triggered']})
    n=len(actual)
    p=k/100_000
    # exact >= hits one-sided binomial tail; no multi-testing correction here
    # output descriptive only, never automatic evidence for prediction advantage.
    tail=sum(math.comb(n,j)*(p**j)*((1-p)**(n-j)) for j in range(hits,n+1))
    return {'phase':'development_only','n':n,'hits':int(hits),
            'expected_hits':n*p,'base_hit_probability':p,
            'p_value_unadjusted':float(tail),'triggered_periods':int(triggered),
            'last_10_hits':sum(x['hit'] for x in actual[-10:]),
            'ten_period_baseline':1-(1-p)**10,
            'guarantee':False,'validated_predictive_advantage':False,
            'future_prospective_test_required':True}
