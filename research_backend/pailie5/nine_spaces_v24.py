"""Nine feature representations for five-digit sequences; exploratory filters only.

All arrays are indexed by the canonical 00000..99999 universe. No feature's
rarity or visual clustering is evidence of lowered next-draw probability.
History-conditioned features only consume draws supplied BEFORE the target.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from functools import lru_cache
from collections import Counter
from typing import Any, Sequence
import hashlib
import json
import math

import numpy as np

from .engine import DIGITS, UNIVERSE
from .space_mapping import mapping_array, encoding_of, inverse_encoding

N = 100_000
WEIGHTS = np.array([10_000, 1_000, 100, 10, 1], dtype=np.int64)
FAMILIES = {
    'attributes': '15位奇偶/大小/数学质性布尔特征与五位型码',
    'sum_span': '和值尾、跨度及相容约束的联合状态',
    'mod3': '012路型与历史逐位置状态转移',
    'steps': '相邻绝对差、带符号差和步长轮廓',
    'symmetric': '对称两端和/差与中心位',
    'hot50': '随历史变化的50维位置数字热度与PCA残差',
    'markov2': '逐位置两期上下文的一步转移后验',
    'combination': '23选6可逆映射与四类分布',
    'intersection': '多空间条件并行、集合交并与可逆审计',
}


def _history(history: Sequence[str]) -> tuple[str, ...]:
    rows = tuple(history)
    if any(not isinstance(s, str) or len(s) != 5 or not s.isascii() or not s.isdigit() for s in rows):
        raise ValueError('历史号码必须是五位字符串；00001不得写成1')
    return rows


def features_15bit(digits: np.ndarray = DIGITS) -> tuple[np.ndarray, np.ndarray]:
    """5x3 Booleans; mathematical primes = {2,3,5,7}, 0/1 neither prime."""
    odd = digits % 2 == 1
    big = digits >= 5
    prime = np.isin(digits, (2, 3, 5, 7))
    bit = np.stack((odd, big, prime), axis=2).reshape((-1, 15))
    codes = (odd.astype(np.uint8) * 4 + big.astype(np.uint8) * 2 + prime.astype(np.uint8))
    return bit, codes


def reconstruct_signed(first: int, signed_steps: Sequence[int]) -> str:
    if not 0 <= first <= 9 or len(signed_steps) != 4:
        raise ValueError('必须给出首位0..9及四项带符号差')
    out = [first]
    for diff in signed_steps:
        if not isinstance(diff, (int, np.integer)) or not -9 <= diff <= 9:
            raise ValueError('位差必须是-9..9整数')
        out.append(out[-1] + int(diff))
        if not 0 <= out[-1] <= 9:
            raise ValueError('位差在当前首位下不能构成合法号码')
    return ''.join(map(str, out))


@dataclass(frozen=True)
class Rule:
    name: str
    family: str
    metric: str
    op: str
    value: Any
    # "exclude" denotes conditions for removal, "retain" conditions for retention.
    action: str = 'exclude'

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip() or self.family not in FAMILIES or self.family == 'intersection':
            raise ValueError('规则ID非空；必须指向可计算的特征家族')
        if self.op not in ('eq','ne','gt','ge','lt','le','between','in','not_in'):
            raise ValueError('不支持的比较运算')
        if self.action not in ('exclude','retain'):
            raise ValueError('action只能是exclude或retain')


def comparison(a: np.ndarray, op: str, v: Any) -> np.ndarray:
    if op == 'eq': return a == v
    if op == 'ne': return a != v
    if op == 'gt': return a > v
    if op == 'ge': return a >= v
    if op == 'lt': return a < v
    if op == 'le': return a <= v
    if op == 'between':
        if not isinstance(v, (list, tuple)) or len(v)!=2 or v[0]>v[1]:
            raise ValueError('between必须提供有效的上下界')
        return (a >= v[0]) & (a <= v[1])
    if op in ('in','not_in'):
        if not isinstance(v,(list,tuple)):
            raise ValueError('in/not_in必须传递列表')
        result = np.isin(a, v)
        return result if op=='in' else ~result
    raise ValueError('运算符无效')


class Spaces:
    """Cross-space feature interpreter over the complete 100k canonical order."""
    def __init__(self, history: Sequence[str] = ()):
        self.history = _history(history)
        self.history_ids = np.fromiter((int(x) for x in self.history), dtype=np.int32)
        self.hist = DIGITS[self.history_ids] if len(self.history_ids) else np.empty((0,5), dtype=np.uint8)
        self._cache: dict[str, dict[str, np.ndarray]] = {}

    def get(self, family: str) -> dict[str, np.ndarray]:
        if family not in FAMILIES or family == 'intersection':
            raise ValueError('未知或非特征空间')
        if family not in self._cache:
            self._cache[family] = getattr(self, '_'+family)()
            for k, a in self._cache[family].items():
                if np.shape(a) != (N,):
                    raise AssertionError(f'{family}.{k}没有全10万注对齐：{np.shape(a)}')
                a.flags.writeable = False
        return self._cache[family]

    def _attributes(self):
        bit, codes = features_15bit()
        return {
            'odd_count':bit[:,0::3].sum(axis=1),
            'big_count':bit[:,1::3].sum(axis=1),
            'prime_count':bit[:,2::3].sum(axis=1),
            'code_signature':np.sum(codes.astype(np.int32)*np.array([4096,512,64,8,1]),axis=1),
            'unique_type_count':np.array([len(set(row)) for row in codes],dtype=np.int8),
        }

    def _sum_span(self):
        ds = DIGITS.astype(np.int16)
        sums = ds.sum(axis=1)
        return {
            'sum':sums,
            'sum_tail':sums%10,
            'span':ds.max(axis=1)-ds.min(axis=1),
            'sum_bin':np.minimum(sums//5,9),
            'odd_count':(ds%2==1).sum(axis=1),
            'tail_span_key':(sums%10)*10+(ds.max(axis=1)-ds.min(axis=1)),
        }

    def _mod3(self):
        road = DIGITS % 3
        # Coerce to signed to avoid 8-bit overflow when constructing 0..242
        road = road.astype(np.int16)
        code = (((road[:,0]*3+road[:,1])*3+road[:,2])*3+road[:,3])*3+road[:,4]
        out = {'road_key':code, 'zero_count':(road==0).sum(axis=1),
               'all_same':np.all(road==road[:,0:1],axis=1).astype(np.int8),
               'switches':(road[:,1:]!=road[:,:-1]).sum(axis=1)}
        if len(self.hist)>=2:
            # Smoothed per-position 3x3 transitions, fixed observed last road.
            trans=np.zeros((5,3,3),dtype=np.int32)
            old=(self.hist[:-1]%3).astype(np.int32)
            new=(self.hist[1:]%3).astype(np.int32)
            for p in range(5): np.add.at(trans[p],(old[:,p],new[:,p]),1)
            prev=self.hist[-1]%3
            logs=np.zeros(N,dtype=np.float64)
            for p in range(5):
                c=trans[p,int(prev[p])]
                probs=(c+1)/(c.sum()+3)
                logs += np.log(probs)[road[:,p]]
            out['transition_log_score']=logs
        return out

    def _steps(self):
        signed=np.diff(DIGITS.astype(np.int16),axis=1)
        absolute=np.abs(signed)
        return {'abs_sum':absolute.sum(axis=1),'abs_max':absolute.max(axis=1),
                'abs_zero_count':(absolute==0).sum(axis=1),
                'abs_ge7_count':(absolute>=7).sum(axis=1),
                'signed_sum':signed.sum(axis=1),
                'abs_signature':(absolute.astype(np.int32)*np.array([1000,100,10,1])).sum(axis=1),
                'signed_signature':((signed+9).astype(np.int32)*np.array([19**3,19**2,19,1])).sum(axis=1)}

    def _symmetric(self):
        d=DIGITS.astype(np.int16)
        d1=np.abs(d[:,0]-d[:,4]); d2=np.abs(d[:,1]-d[:,3])
        s1=d[:,0]+d[:,4]; s2=d[:,1]+d[:,3]
        return {'outer_sum':s1,'inner_sum':s2,'outer_absdiff':d1,'inner_absdiff':d2,
                'center':d[:,2], 'outer_pair_key':s1*10+d1, 'inner_pair_key':s2*10+d2,
                'symmetric_signature':((s1.astype(np.int32)*10+d1)*190+(s2.astype(np.int32)*10+d2))*10+d[:,2]}

    def _hot50(self):
        if len(self.hist)<30: raise ValueError('hot50需要至少30期历史样本；不自动缩短窗口')
        # Candidate-conditioned 50D sparse, observed-frequency weighted one-hot.
        n=len(self.hist)
        weights=np.zeros((5,10),dtype=np.float64)
        for p in range(5):
            c=np.bincount(self.hist[:,p],minlength=10)
            weights[p]=(c+1)/(n+10)
        positions=np.arange(5)
        training=np.zeros((n,50),dtype=np.float64)
        training[np.arange(n)[:,None], positions[None,:]*10+self.hist]=weights[positions[None,:],self.hist]
        center=training.mean(axis=0)
        _,_,vt=np.linalg.svd(training-center,full_matrices=False)
        loadings=vt[:min(3,len(vt))]
        # Build 100k 50-d coordinates without materializing a giant distance matrix.
        candidate=np.zeros((N,50),dtype=np.float32)
        candidate[np.arange(N)[:,None],positions[None,:]*10+DIGITS]=weights[positions[None,:],DIGITS]
        centered=candidate-center
        residual=np.sum(centered**2,axis=1)-np.sum((centered@loadings.T)**2,axis=1)
        residual=np.maximum(residual,0)
        return {'pca_reconstruction_error':residual,
                'sum_negative_log_hotness':-np.log(weights[positions[None,:],DIGITS]).sum(axis=1),
                'min_position_frequency':weights[positions[None,:],DIGITS].min(axis=1)}

    def _markov2(self):
        if len(self.hist)<3: raise ValueError('markov2需要至少3期历史（两个前置状态和一个结果）')
        # 5 positions × 100 possible 2-draw contexts × 10 outcomes.
        counts=np.zeros((5,100,10),dtype=np.int32)
        for p in range(5):
            a=self.hist[:-2,p].astype(np.int32)*10+self.hist[1:-1,p]
            b=self.hist[2:,p]
            np.add.at(counts[p],(a,b),1)
        logscore=np.zeros(N,dtype=np.float64)
        support=np.zeros(N,dtype=np.int32)
        for p in range(5):
            k=int(self.hist[-2,p])*10+int(self.hist[-1,p]); c=counts[p,k]
            logscore+=np.log((c+1)/(c.sum()+10))[DIGITS[:,p]]
            support+=c[DIGITS[:,p]]
        return {'log_score':logscore,'transition_support':support,
                'surprisal':-logscore}

    def _combination(self):
        a=mapping_array('pick23_6').astype(np.int16)
        gap=np.diff(a,axis=1)
        # 4 independent digit categories; histogram has C(5+4-1,3) = 56 states.
        d=DIGITS
        group=(d>=5).astype(np.int16)*2+(d%2==1).astype(np.int16)
        counts=np.stack([(group==j).sum(axis=1) for j in range(4)],axis=1)
        group_sig=(((counts[:,0]*6+counts[:,1])*6+counts[:,2])*6+counts[:,3])
        return {'pick23_sum':a.sum(axis=1), 'pick23_span':a[:,-1]-a[:,0],
                'pick23_max_gap':gap.max(axis=1), 'pick23_adjacent_pairs':(gap==1).sum(axis=1),
                'group_distribution_key':group_sig,'group0_count':counts[:,0],
                'group1_count':counts[:,1],'group2_count':counts[:,2],'group3_count':counts[:,3]}

    def mask(self, rule: Rule) -> np.ndarray:
        values=self.get(rule.family)
        if rule.metric not in values:
            raise ValueError(f'{rule.family}未提供指标{rule.metric}；可能需要更多历史')
        tested=np.asarray(comparison(values[rule.metric],rule.op,rule.value),dtype=bool)
        if tested.shape!=(N,): raise ValueError('规则条件必须返回10万位布尔结果')
        return tested if rule.action=='exclude' else ~tested


def compose(history: Sequence[str], rules: Sequence[Rule], *, budget: int = 100,
            seed: int = 42, base_numbers: Sequence[str] | None = None) -> dict[str,Any]:
    """Union of exclusion masks, with exact marginal/overlap audit; NOT calibrated ranking."""
    if not 1<=budget<=100_000: raise ValueError('budget必须为1..100000')
    ids=[r.name for r in rules]
    if len(ids)!=len(set(ids)): raise ValueError('规则名称重复')
    space=Spaces(history)
    if base_numbers is None:
        base=np.ones(N,dtype=bool)
    else:
        base=np.zeros(N,dtype=bool)
        for s in base_numbers:
            if not isinstance(s,str) or len(s)!=5 or not s.isdigit() or not s.isascii():
                raise ValueError('外部大底包含非五位号码')
            base[int(s)]=True
    removed=np.zeros(N,dtype=bool)
    masks=[]; audit=[]
    for r in rules:
        cut=space.mask(r) & base
        new=cut & ~removed
        overlap=cut & removed
        removed |= cut
        masks.append(cut)
        audit.append({'rule':r.name,'family':r.family,'metric':r.metric,
                      'raw_excluded':int(cut.sum()),'marginal_excluded':int(new.sum()),
                      'overlap_prior':int(overlap.sum()),
                      'fair_mass_excluded_by_step':round(int(new.sum())/N,10)})
    remaining=base & ~removed
    rng=np.random.default_rng(seed)
    # Exploration-only tie break: fewer violated rules first; deterministic seed for ties.
    bad=np.zeros(N,dtype=np.uint16)
    for m in masks: bad+=m.astype(np.uint16)
    # Consider all base numbers for reversible best-effort budget output; deleted not gone.
    eligible=np.flatnonzero(base)
    jitter=rng.random(len(eligible))
    order=np.lexsort((jitter,bad[eligible]))
    ranked=eligible[order]
    selected=ranked[:budget]
    # Hard-constraint output never silently restores removed items to reach the budget.
    hard_eligible=np.flatnonzero(remaining)
    hard_selected=hard_eligible[np.argsort(rng.random(len(hard_eligible)))[:budget]]
    pairwise=[]
    for i in range(len(masks)):
        for j in range(i+1,len(masks)):
            intersection=int((masks[i]&masks[j]).sum())
            union=int((masks[i]|masks[j]).sum())
            pairwise.append({'a':rules[i].name,'b':rules[j].name,'jaccard':intersection/union if union else 1.,
                             'intersection':intersection})
    token=hashlib.sha256(json.dumps({'history':space.history,'rules':[asdict(r) for r in rules],
                                     'seed':seed,'budget':budget,'base_hash':hashlib.sha256(base.tobytes()).hexdigest()},
                                    ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    return {'version':'nine-spaces-v24','input_sha256':token,
            'base':int(base.sum()),'strict_remaining':int(remaining.sum()),
            'strict_numbers':[f'{int(x):05d}' for x in hard_selected],
            'ranked_numbers':[f'{int(x):05d}' for x in selected],
            'ranked_experimental_violations':[int(bad[x]) for x in selected],
            'strict_exact_random_coverage':int(len(hard_selected))/N,
            'ranked_exact_random_coverage':len(selected)/N,
            'fair_each_probability':1/N,'audit':audit,'overlaps':pairwise,
            'note':'非校准研究排序；在公平独立开奖下，任何K个不同号码的中奖概率都是K/100000。'}


def walk_forward(history: Sequence[str], rules: Sequence[Rule], *, min_train: int=30,
                 last_n: int=15, budget: int=100, seed: int=42) -> dict[str,Any]:
    """History prefix only. User-chosen rules may still be selected post-hoc."""
    rows=_history(history)
    if min_train<3 or last_n<1 or len(rows)<=min_train:
        raise ValueError('需要充分的历史前缀以及至少一期样本外观察')
    start=max(min_train,len(rows)-last_n)
    out=[]
    for t in range(start,len(rows)):
        r=compose(rows[:t],rules,budget=budget,seed=seed+t)
        target=rows[t]
        out.append({'index':t,'training_count':t,'draw':target,'strict_size':r['strict_remaining'],
                    'strict_hit':target in r['strict_numbers'],
                    'ranked_hit':target in r['ranked_numbers'],
                    'fair_baseline':len(r['ranked_numbers'])/N,
                    'rules_removed_draw':[a['rule'] for a,rule in zip(r['audit'],rules) if Spaces(rows[:t]).mask(rule)[int(target)]]})
    return {'periods':len(out),'topk_hits':sum(x['ranked_hit'] for x in out),
            'strict_selected_hits':sum(x['strict_hit'] for x in out),
            'strict_hits':sum(x['strict_hit'] for x in out),
            'expected_random_hits':sum(x['fair_baseline'] for x in out),
            'rows':out,'warning':'历史样本外仅指每一期不读取未来；若规则从这些期的结果中挑选，仍存在选择偏差。'}


def capability_cards() -> list[dict[str,Any]]:
    return [{'id':'pl5.space.'+key,'version':'2.4.0','name':name,
             'inputs':['five_digit_number','history_prefix','rule_config'],
             'outputs':['feature_vector_100000','optional_binary_mask','audit'],
             'status':'exploratory','predictive_advantage':'unverified',
             'depends_on':['pl5.canonical_universe'],
             'safe_execution':'deterministic_local_only'}
            for key,name in FAMILIES.items()]


def predefined_exploratory_rules() -> list[Rule]:
    """Five illustrative layers from the user. Deliberately NOT active by default."""
    return [
        Rule('step_ge7','steps','abs_ge7_count','ge',1),
        Rule('all_012_same','mod3','all_same','eq',1),
        Rule('zero_road_absent','mod3','zero_count','eq',0),
        Rule('all_odd_or_even','attributes','odd_count','in',[0,5]),
        Rule('sum_tail_and_low_span','sum_span','tail_span_key','in',
             [tail*10+span for tail in (0,5) for span in range(3)]),
    ]


# Temporal pattern recognition is restricted to history-invariant features.
# Historical hotness and Markov scores must be fitted prefix by prefix, and
# must not be retroactively evaluated with a model fitted on future outcomes.
TEMPORAL_FAMILIES = ('attributes', 'sum_span', 'mod3', 'steps', 'symmetric', 'combination')


@dataclass(frozen=True)
class TemporalSpec:
    name: str
    family: str
    metric: str
    window: int = 4
    pattern: str = 'repeat'  # repeat, arithmetic, alternating, periodic
    period: int = 2

    def __post_init__(self):
        if not isinstance(self.name,str) or not self.name.strip():
            raise ValueError('时序规则需要名称')
        if self.family not in TEMPORAL_FAMILIES:
            raise ValueError('时序模式仅适用于历史不变的指标；动态概率必须按期训练')
        if not isinstance(self.window,int) or not 2<=self.window<=30:
            raise ValueError('时序窗口为2..30')
        if self.pattern not in ('repeat','arithmetic','alternating','periodic'):
            raise ValueError('未知的时序模式')
        if not isinstance(self.period,int) or not 2<=self.period<=10:
            raise ValueError('周期为2..10')


def temporal_proposal(history: Sequence[str], spec: TemporalSpec) -> dict[str, Any]:
    """Discover a possible extension using only history before the next draw.

    Frequency equals the exact number of canonical candidates that would
    continue the pattern, NOT the probability that the pattern breaks next.
    """
    rows=_history(history)
    if len(rows)<spec.window:
        return {'name':spec.name,'status':'insufficient_history','required':spec.window,
                'available':len(rows),'proposal':None}
    space=Spaces()
    measures=space.get(spec.family)
    if spec.metric not in measures:
        raise ValueError(f'未知指标 {spec.family}.{spec.metric}')
    metric=measures[spec.metric]
    if not np.issubdtype(metric.dtype,np.integer) and metric.dtype != np.dtype('bool'):
        raise ValueError('自动模式仅支持离散整数指标；连续指标需预先定义离散化/容差')
    seq=[int(x) for x in metric[[int(i) for i in rows[-spec.window:]]]]
    follow=None
    if spec.pattern=='repeat':
        if len(set(seq))==1: follow=seq[-1]
    elif spec.pattern=='arithmetic':
        if spec.window>=3:
            delta=seq[1]-seq[0]
            if delta!=0 and all(seq[i]-seq[i-1]==delta for i in range(2,len(seq))):
                follow=seq[-1]+delta
    elif spec.pattern=='alternating':
        if spec.window>=4 and seq[-1]!=seq[-2] and all(seq[i]==seq[i-2] for i in range(2,len(seq))):
            follow=seq[-2]
    elif spec.pattern=='periodic':
        period=spec.period
        if len(seq)>=2*period and len(set(seq))>1 and all(seq[i]==seq[i-period] for i in range(period,len(seq))):
            follow=seq[-period]
    if follow is None:
        return {'name':spec.name,'status':'no_pattern','values':seq,'proposal':None}
    count=int(np.count_nonzero(metric==follow))
    # A continuation value can be outside the feature's attainable support.
    if count==0:
        return {'name':spec.name,'status':'impossible_extension','values':seq,
                'next_value':follow,'null_mass':0.0,'proposal':None}
    r=Rule(spec.name,spec.family,spec.metric,'eq',follow,'exclude')
    return {'name':spec.name,'status':'candidate','values':seq,'next_value':follow,
            'affected_count':count,'null_mass':count/N,'proposal':asdict(r),
            'warning':'随机序列也可能延续；此值是无条件随机基线，不是下一期概率下降的证据。'}


def compose_temporal(history: Sequence[str], rules: Sequence[Rule],
                     specs: Sequence[TemporalSpec], *, budget: int=100, seed: int=42,
                     base_numbers: Sequence[str] | None=None) -> dict[str,Any]:
    """Generate activated temporal rule candidates from strictly past observations."""
    proposed=[temporal_proposal(history,s) for s in specs]
    active=[Rule(**p['proposal']) for p in proposed if p.get('proposal')]
    all_names=[r.name for r in rules]+[r.name for r in active]
    if len(all_names)!=len(set(all_names)):
        raise ValueError('静态规则与自动时序规则ID重复')
    out=compose(history,list(rules)+active,budget=budget,seed=seed,base_numbers=base_numbers)
    out['temporal_proposals']=proposed
    out['active_temporal_rules']=len(active)
    return out


def walk_forward_temporal(history: Sequence[str], rules: Sequence[Rule],
                          specs: Sequence[TemporalSpec], *, min_train: int=30,
                          last_n: int=15, budget: int=100, seed: int=42) -> dict[str,Any]:
    """Recreate temporal rule activation separately for each historical target."""
    rows=_history(history)
    if min_train<3 or last_n<1 or len(rows)<=min_train:
        raise ValueError('需要历史训练前缀和测试期')
    start=max(min_train,len(rows)-last_n)
    out=[]
    for t in range(start,len(rows)):
        r=compose_temporal(rows[:t],rules,specs,budget=budget,seed=seed+t)
        target=rows[t]
        n=int(target)
        m=Spaces(rows[:t])
        actual_rules=list(rules)+[Rule(**p['proposal']) for p in r['temporal_proposals'] if p.get('proposal')]
        out.append({'index':t,'training_count':t,'draw':target,
                    'active_temporal_rules':r['active_temporal_rules'],
                    'ranked_hit':target in r['ranked_numbers'],
                    'strict_selected_hit':target in r['strict_numbers'],
                    'strict_pool_contains_draw':not any(bool(m.mask(x)[n]) for x in actual_rules),
                    'strict_remaining':r['strict_remaining'],
                    'ranked_budget':len(r['ranked_numbers']),
                    'fair_baseline':len(r['ranked_numbers'])/N,
                    'rules_removed_draw':[x.name for x in actual_rules if m.mask(x)[n]]})
    return {'periods':len(out), 'topk_hits':sum(v['ranked_hit'] for v in out),
            'strict_selected_hits':sum(v['strict_selected_hit'] for v in out),
            'strict_pool_hits':sum(v['strict_pool_contains_draw'] for v in out),
            'expected_random_hits':sum(v['fair_baseline'] for v in out),
            'rows':out,'warning':'所有规则在目标期之前生成；但人工根据回测选参数仍会造成事后选择偏差。'}


def describe_metric(family: str, metric: str, *, history: Sequence[str]=(), top: int=8) -> dict[str,Any]:
    """Exact whole-universe bucket distribution; interpret as a *null baseline*."""
    if not 1<=top<=100: raise ValueError('top必须为1..100')
    data=Spaces(history).get(family)
    if metric not in data: raise ValueError('指标不存在')
    a=data[metric]
    states,count=np.unique(a,return_counts=True)
    probabilities=count/N
    entropy=float(-np.sum(probabilities*np.log2(probabilities)))
    order=np.argsort(-count,kind='stable')[:top]
    return {'family':family,'metric':metric,'universe':N,
            'different_values':int(len(states)),
            'min_bucket_count':int(count.min()),'max_bucket_count':int(count.max()),
            'entropy_bits':entropy,
            'top_buckets':[{'value':float(states[i]) if np.issubdtype(a.dtype,np.floating) else int(states[i]),
                            'count':int(count[i]),'random_null_mass':float(probabilities[i])}
                           for i in order],
            'interpretation':'所有统计都基于10万注等权全集；不是预测下一期开奖偏离均匀的证据。'}
