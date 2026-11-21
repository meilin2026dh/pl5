"""PL5 V2.5: bounded autonomous representation-space research.

Research-only. Each new representation is a deterministic feature of an existing
five-digit integer; it creates no new information about an independent future
uniform draw. No arbitrary code execution, no network, no automatic promotion.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from functools import lru_cache
from typing import Sequence
import hashlib
import json
import math

import numpy as np

from .engine import DIGITS
from .nine_spaces_v24 import Spaces
from .space_mapping import mapping_array

N = 100000
OPERATORS = ('weighted_mod', 'pair_sum_mod', 'signed_difference',
             'cross_term_mod', 'combination_mod', 'affine_relabel')
STATIC_BASELINES = (
    ('attributes', 'odd_count'), ('attributes', 'unique_type_count'),
    ('sum_span', 'sum'), ('sum_span', 'sum_tail'), ('sum_span', 'span'),
    ('mod3', 'road_key'), ('steps', 'abs_sum'), ('steps', 'abs_signature'),
    ('symmetric', 'outer_pair_key'), ('combination', 'pick23_sum'),
)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                    separators=(',', ':')).encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class Representation:
    operator: str
    positions: tuple[int, ...] = (0, 1)
    weights: tuple[int, ...] = (1, 1)
    modulus: int = 7
    offset: int = 0

    def __post_init__(self):
        if self.operator not in OPERATORS:
            raise ValueError('不支持的空间算子')
        if not (2 <= len(self.positions) <= 5 and all(type(x) is int and 0 <= x < 5 for x in self.positions)
                and len(set(self.positions)) == len(self.positions)):
            raise ValueError('位置为两个到五个不同的0..4整数')
        if not (len(self.weights) == len(self.positions) and all(type(w) is int and -9 <= w <= 9 for w in self.weights)):
            raise ValueError('权重长度须与位置一致且在-9..9')
        if type(self.modulus) is not int or not 2 <= self.modulus <= 31:
            raise ValueError('模数必须是2..31的整数')
        if type(self.offset) is not int or not 0 <= self.offset <= 99999:
            raise ValueError('偏移量必须为0..99999')
        if self.operator in ('pair_sum_mod', 'signed_difference') and len(self.positions) != 2:
            raise ValueError('位对算子必须使用两个位置')
        if self.operator == 'cross_term_mod' and len(self.positions) != 3:
            raise ValueError('交互算子必须使用三个位置')
        if self.operator == 'affine_relabel' and (math.gcd(abs(self.weights[0]), N) != 1):
            raise ValueError('仿射重标记需要与100000互质的乘数')

    @property
    def id(self) -> str:
        return 'pl5.representation.' + _digest(asdict(self))[:16]

    def capability(self) -> dict:
        return {
            'id': self.id, 'version': '2.5.0', 'kind': 'discrete_representation',
            'spec': asdict(self), 'inputs': ['canonical_five_digits'],
            'outputs': ['feature_values[100000]', 'candidate_rule_mask[100000]', 'audit'],
            'depends_on': ['pl5.canonical_universe'], 'deterministic': True,
            'code_execution': 'bounded_numpy_operations_only', 'registration': 'research_candidate',
            'predictive_advantage': 'unverified',
            'notes': '整数编码/特征变换，不会因改变表示空间而产生未来预测信息',
        }


def vector(spec: Representation) -> np.ndarray:
    """Values indexed exactly by decimal id 00000..99999 (no history)."""
    pos = spec.positions
    digits = DIGITS.astype(np.int64, copy=False)
    if spec.operator == 'weighted_mod':
        v = sum(spec.weights[j] * digits[:, k] for j, k in enumerate(pos)) + spec.offset
        a = v % spec.modulus
    elif spec.operator == 'pair_sum_mod':
        a = (digits[:, pos[0]] + digits[:, pos[1]] + spec.offset) % spec.modulus
    elif spec.operator == 'signed_difference':
        a = digits[:, pos[0]] - digits[:, pos[1]]  # -9..9; sign preserved
    elif spec.operator == 'cross_term_mod':
        a = (digits[:, pos[0]] * digits[:, pos[1]] + digits[:, pos[2]] + spec.offset) % spec.modulus
    elif spec.operator == 'combination_mod':
        a = (mapping_array('pick23_6')[:, list(pos)].astype(np.int64) @ np.asarray(spec.weights, dtype=np.int64)
             + spec.offset) % spec.modulus
    elif spec.operator == 'affine_relabel':
        a = ((np.arange(N, dtype=np.int64) * spec.weights[0]) + spec.offset) % N
    else:
        raise AssertionError('operator not handled')
    out = np.asarray(a, dtype=np.int64)
    if out.shape != (N,) or not np.all(np.isfinite(out)):
        raise AssertionError('表示空间必须对齐全部10万注')
    out.flags.writeable = False
    return out


def _distribution(values: np.ndarray):
    distinct, inverse, counts = np.unique(values, return_inverse=True, return_counts=True)
    p = counts / N
    entropy = float(-np.dot(p, np.log2(p)))
    # A canonical relabel-invariant partition: group by first occurrence.
    # Distinct numeric labels alone do not imply a different partition.
    first_indices = np.full(len(distinct), N, dtype=np.int32)
    np.minimum.at(first_indices, inverse, np.arange(N, dtype=np.int32))
    order = np.argsort(first_indices)
    canonical_labels = np.empty(len(distinct), dtype=np.int32)
    canonical_labels[order] = np.arange(len(distinct), dtype=np.int32)
    canonical_ids = canonical_labels[inverse]
    partition_digest = hashlib.sha256(canonical_ids.tobytes()).hexdigest()
    return distinct, counts, entropy, partition_digest, inverse


def _baseline_profiles() -> list[dict]:
    s = Spaces()
    out=[]
    for family, metric in STATIC_BASELINES:
        v=s.get(family)[metric]
        _, _, entropy, partition_sha, _ = _distribution(v)
        out.append({'name': f'{family}.{metric}', 'partition_sha256':partition_sha,
                    'entropy_bits':entropy})
    return out


@lru_cache(maxsize=1)
def baseline_profiles() -> tuple[tuple[str, str], ...]:
    return tuple((x['name'], x['partition_sha256']) for x in _baseline_profiles())


@lru_cache(maxsize=1)
def _near_baselines() -> tuple:
    # Restricted, explicitly named comparisons. These are NOT independent sources.
    static=Spaces()
    pool=(('attributes','odd_count'),('sum_span','sum_tail'),
          ('sum_span','span'),('steps','abs_sum'),('combination','pick23_sum'))
    return tuple((f'{family}.{metric}', *_near_encoding(static.get(family)[metric]))
                 for family,metric in pool)


def _near_encoding(values: np.ndarray) -> tuple[np.ndarray,float,int]:
    _, inverse, sizes=np.unique(values,return_inverse=True,return_counts=True)
    p=sizes/N
    return inverse.astype(np.int32),float(-np.dot(p,np.log2(p))),len(sizes)


def _conditional_entropy(feature:np.ndarray, feature_H:float, baseline:np.ndarray,
                         baseline_H:float, baseline_states:int) -> tuple[float,float]:
    if feature_H<=0:return 0.,1.
    count_a=int(feature.max())+1
    # This unique encoding avoids constructing a gigantic contingency table.
    joint=feature.astype(np.int64)*baseline_states+baseline.astype(np.int64)
    _,cnt=np.unique(joint,return_counts=True)
    p=cnt/N
    joint_entropy=float(-np.dot(p,np.log2(p)))
    conditional=max(0.,joint_entropy-baseline_H)
    fraction=float(np.clip((feature_H-conditional)/feature_H,0.,1.))
    return conditional,fraction


def propose(seed: int = 20261102, count: int = 24) -> list[Representation]:
    if type(seed) is not int or not 0 <= seed < 2**32 or type(count) is not int or not 1 <= count <= 60:
        raise ValueError('seed为32位非负整数，count为1..60')
    rng=np.random.default_rng(seed)
    results=[]
    seen=set()
    attempts=0
    while len(results)<count and attempts < count * 100:
        attempts+=1
        op=OPERATORS[int(rng.integers(len(OPERATORS)))]
        length = 2 if op in ('pair_sum_mod','signed_difference') else 3 if op=='cross_term_mod' else int(rng.integers(2,6))
        positions=tuple(int(x) for x in rng.choice(5,size=length,replace=False))
        weights=tuple(int(x) for x in rng.integers(1,10,size=length))
        if op=='affine_relabel':
            # Multipliers relatively prime to 10 are also relatively prime to 100000.
            w0=([1,3,7,9][int(rng.integers(4))])
            weights=(w0,)+weights[1:]
        modulus=int(rng.choice([3,4,5,7,9,11,13,17]))
        offset=int(rng.integers(0,97))
        item=Representation(op,positions,weights,modulus,offset)
        if item.id not in seen:
            seen.add(item.id);results.append(item)
    return results


def audit(specs: Sequence[Representation], *, max_keep: int = 24) -> dict:
    """Exact canonical 100k-vector redundancy audit; deterministic search order.

    Accepts features for engineering research, not as predictive eligibility.
    Structural diversity is not new random information.
    """
    if not 1 <= max_keep <= 60 or len(specs)>60:
        raise ValueError('至多60个候选，保留数量1..60')
    baselines=dict((part,name) for name, part in baseline_profiles())
    partitions=dict(baselines)
    reviewed=[]; accepted=[]
    for s in specs:
        v=vector(s)
        distinct, counts, entropy, part, inverse = _distribution(v)
        baseline=partitions.get(part)
        redundancy=[]
        for base_name,base_inv,base_H,base_states in _near_baselines():
            conditional,explained=_conditional_entropy(inverse,entropy,base_inv,base_H,base_states)
            redundancy.append((base_name,conditional,explained))
        best=max(redundancy,key=lambda x:x[2])
        # A one-to-one relabeling is an information-equivalent representation,
        # not a new compressible feature. Keep its descriptor but do not promote.
        full_relabel=len(distinct)==N
        if full_relabel: status='invertible_relabel_only'
        elif baseline: status='redundant_partition'
        elif len(accepted)>=max_keep: status='quota_exceeded'
        else: status='engineering_candidate'
        if status=='engineering_candidate':
            partitions[part]=s.id; accepted.append(s)
        reviewed.append({'id':s.id,'spec':asdict(s),'capability':s.capability(),
            'status':status,'equivalent_to':baseline,
            'bucket_count':len(distinct),'entropy_bits':round(entropy,8),
            'largest_bucket':int(counts.max()),'smallest_bucket':int(counts.min()),
            'nearest_baseline':best[0], 'baseline_explains_fraction':round(best[2],6),
            'conditional_entropy_bits':round(best[1],6),
            'partition_sha256':part,'value_sha256':hashlib.sha256(v.tobytes()).hexdigest()})
    return {'version':'representation-v25','baseline_feature_count':len(baselines),
            'reviewed':reviewed,'accepted':len(accepted),'rejected':len(reviewed)-len(accepted),
            'warning':'新特征/新分桶不代表新开奖信息，且不自动进入正式过滤。'}


def _historical_values(spec: Representation, history: Sequence[str]) -> np.ndarray:
    if any(not isinstance(n,str) or len(n)!=5 or not n.isascii() or not n.isdigit() for n in history):
        raise ValueError('历史必须为五位号码字符串，不能丢掉前导0')
    if len(history)>20000:raise ValueError('历史最多20000期')
    return vector(spec)[np.fromiter((int(x) for x in history), dtype=np.int64)]


def _frozen_gain(spec: Representation, train: Sequence[str], evaluation: Sequence[str], alpha: float = 100.) -> dict:
    """Freeze a bucket model before seeing evaluation. Exact probability normalization.

    Smoothed category P(v)=(observed(v)+alpha*q(v))/(Ntrain+alpha);
    ticket P(x)=P(v(x))/bucket_size(v). q is exact structural zero-hypothesis mass.
    """
    if not train or not evaluation or not math.isfinite(alpha) or alpha<=0:
        raise ValueError('训练和检验不能为空，alpha必须正数')
    full=vector(spec)
    _, inverse, sizes = np.unique(full, return_inverse=True, return_counts=True)
    bucket_count=np.bincount(inverse[_historical_ids(train)], minlength=len(sizes)).astype(np.float64)
    q=sizes/N
    mass=(bucket_count+alpha*q)/(len(train)+alpha)
    p=mass[inverse[_historical_ids(evaluation)]]/sizes[inverse[_historical_ids(evaluation)]]
    gain=np.log(p*N)
    return {'periods':len(evaluation),'avg_log_gain_nats':float(np.mean(gain)),
            'cumulative_log_gain_nats':float(np.sum(gain)),
            'min_model_probability':float(np.min(p)),'null_avg_log_loss_nats':float(np.log(N)),
            'model_avg_log_loss_nats':float(-np.mean(np.log(p)))}


def _historical_ids(history: Sequence[str]) -> np.ndarray:
    if any(not isinstance(x,str) or len(x)!=5 or not x.isascii() or not x.isdigit() for x in history):
        raise ValueError('历史期号必须是恰好五位号码，含前导0')
    return np.fromiter((int(x) for x in history), dtype=np.int32)


def study(history: Sequence[str], *, seed: int=20261102, count: int=24,
          test_periods: int=30, alpha: float=100.) -> dict:
    """Generate using mathematics only, select on development, audit one frozen holdout.

    The holdout is historical and may have been seen in earlier external research;
    repeated reruns never turn it into independent prospective validation.
    """
    _historical_ids(history)
    if len(history)<90 or not 20<=test_periods<=min(200,len(history)//3):
        raise ValueError('需要>=90期历史；封存历史测试20..200且不超过历史的1/3')
    proposals=propose(seed,count)
    screening=audit(proposals)
    accepted=[Representation(**item['spec']) for item in screening['reviewed'] if item['status']=='engineering_candidate']
    cut=len(history)-test_periods
    dev=history[:cut]
    train=dev[:max(30,len(dev)*2//3)]
    validation=dev[len(train):]
    if not validation or not accepted:
        return {'version':'representation-v25','selected':None,'audit':screening,'status':'no_eligible_research_candidate'}
    contenders=[]
    for spec in accepted:
        v=_frozen_gain(spec,train,validation,alpha)
        contenders.append({'id':spec.id,**v})
    # Selection is deterministic, and entirely from the development portion.
    contenders.sort(key=lambda x:(-x['avg_log_gain_nats'],x['id']))
    winner=next(s for s in accepted if s.id==contenders[0]['id'])
    test=_frozen_gain(winner,dev,history[cut:],alpha)
    full_values=vector(winner)
    continuation=None
    recent=_historical_values(winner,history[-3:])
    if len(set(recent.tolist()))==1:
        size=int(np.count_nonzero(full_values==recent[-1]))
        continuation={'bucket_value':int(recent[-1]),'excluded_count':size,'fair_mass':size/N,
                      'rule':'exclude_if_equal_recent_three','automatic_enable':False}
    identifier=_digest({'seed':seed,'count':count,'alpha':alpha,'history':list(history),'test':test_periods})
    # An explicitly exploratory next-draw nomination. Never evaluate these
    # numbers on the historical holdout that was used to report the study.
    observed=_historical_ids(history)
    unique, inverse, sizes=np.unique(full_values,return_inverse=True,return_counts=True)
    freq=np.bincount(inverse[observed],minlength=len(sizes))
    q=sizes/N
    masses=(freq+alpha*q)/(len(history)+alpha)
    nominal=(masses/sizes)[inverse]
    next_rank=np.lexsort((np.arange(N),-nominal))[:100]
    control=np.random.default_rng(seed ^ 0xA25A).choice(N,100,replace=False)
    return {'version':'representation-v25','experiment_id':identifier,'status':'research_only',
        'splits':{'development_train':len(train),'development_validation':len(validation),
                  'historical_holdout':test_periods,'selection_policy':'only development validation'},
        'candidate_audit':screening,'development_leaderboard':contenders,
        'selected_capability':winner.capability(),'historical_holdout':test,
        'baseline_probability_per_ticket':1/N,'temporal_experiment':continuation,
        'next_draw_exploratory_top100':[f'{int(n):05d}' for n in next_rank],
        'next_draw_random_control_100':[f'{int(n):05d}' for n in control],
        'next_draw_model_probabilities':[float(nominal[n]) for n in next_rank],
        'next_draw_fair_coverage':100/N,
        'recommendation':'No auto-promotion; future pre-registered forward trials needed.',
        'warning':'历史留出不能证明未来预测优势；重复试验/重复查看导致测试污染。\n'
                  '不存在不损失信息的升维过滤捷径，所有变换均由原五位数字确定。'}
