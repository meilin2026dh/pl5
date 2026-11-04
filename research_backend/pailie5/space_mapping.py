"""PL5 跨空间特征引擎：单射、可逆、可审计的表示变换。

⚠ 本模块不提高公平独立开奖的真实中奖概率。
映射的空间规模与PL5不同：仅将其中恰好100000个元素作为合法映射像。
所有基线、覆盖率、统计分布必须基于这100000个合法像计算。
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import comb, gcd
import numpy as np

from .pattern_rules import (EXTRA_INDICATORS, CONTEXT_INDICATORS,
                            register_indicator, register_context_indicator)

N_PL5 = 100_000
_ID_WEIGHTS = np.array([10000,1000,100,10,1],dtype=np.int64)

@dataclass(frozen=True)
class Space:
    key: str
    label: str
    kind: str
    size: int
    alphabet: int
    positions: int
    multiplier: int = 37
    offset: int = 541

    def __post_init__(self):
        if self.size < N_PL5:
            raise ValueError('严格一一映射必须至少覆盖100000个状态；较小空间需要残差子空间')
        if gcd(self.multiplier,self.size)!=1:
            raise ValueError('映射乘数与模数必须互质，才能保证不发生碰撞')

SPACES = {
    'pick23_6': Space('pick23_6','23选6组合空间','combination',comb(23,6),23,6),
    'pick41_4': Space('pick41_4','41选4组合空间','combination',comb(41,4),41,4),
    'ternary11': Space('ternary11','11位310三态空间','ternary',3**11,3,11),
}


def _validated_id(number: int | str) -> int:
    if isinstance(number,str):
        if len(number)!=5 or not number.isascii() or not number.isdigit():
            raise ValueError('排列五号码必须是5位字符串，如00128')
        v=int(number)
    elif isinstance(number,(int,np.integer)):
        v=int(number)
    else:
        raise TypeError('只支持5位字符串或号码索引')
    if not 0 <= v < N_PL5:
        raise ValueError('号码超出00000..99999')
    return v


def mapped_rank(number: int | str, space: str = 'pick23_6') -> int:
    """排列五索引映射到目标空间中的唯一rank。映射版本由Space常量控制。"""
    sp=SPACES[space]
    return (sp.multiplier*_validated_id(number)+sp.offset)%sp.size


def inverse_rank(rank: int, space: str = 'pick23_6') -> str | None:
    """目标rank逆回PL5，未被使用的rank返回None，不错误映射到其他号码。"""
    sp=SPACES[space]
    r=int(rank)
    if not 0<=r<sp.size:
        raise ValueError('rank超出目标空间')
    candidate=(pow(sp.multiplier,-1,sp.size)*(r-sp.offset))%sp.size
    return f'{candidate:05d}' if candidate<N_PL5 else None


def _combinadic_unrank(ranks: np.ndarray, n: int, k: int) -> np.ndarray:
    """向量化colex unrank，返回0-index升序元素。"""
    rem=np.asarray(ranks,dtype=np.int64).copy()
    out=np.zeros((len(rem),k),dtype=np.int16)
    for j in range(k,0,-1):
        choose=np.asarray([comb(x,j) if x>=j else 0 for x in range(n)],dtype=np.int64)
        c=np.searchsorted(choose,rem,side='right')-1
        if (c<j-1).any() or (c>=n).any():
            raise AssertionError('组合序号越界')
        out[:,j-1]=c.astype(np.int16)
        rem-=choose[c]
    if np.any(rem!=0) or np.any(np.diff(out,axis=1)<=0):
        raise AssertionError('组合逆序失败')
    return out


def _combinadic_rank(combo: tuple[int,...] | list[int], n: int,k: int) -> int:
    vals=tuple(int(x) for x in combo)
    if len(vals)!=k or any(v<0 or v>=n for v in vals) or tuple(sorted(set(vals)))!=vals:
        raise ValueError('组合必须是严格递增、不能重复的0-index位置')
    return sum(comb(v,j+1) for j,v in enumerate(vals))


@lru_cache(maxsize=4)
def mapping_array(space: str) -> np.ndarray:
    """每个PL5号码在目标空间中的表示，行索引就是PL5整数。只计算一次。"""
    sp=SPACES[space]
    ids=np.arange(N_PL5,dtype=np.int64)
    ranks=(sp.multiplier*ids+sp.offset)%sp.size
    if sp.kind=='combination':
        # 1..n 人类可读，编码算法仍使用0-index
        values=_combinadic_unrank(ranks,sp.alphabet,sp.positions)+1
    else:
        values=np.empty((N_PL5,sp.positions),dtype=np.int16)
        temp=ranks.copy()
        for j in range(sp.positions-1,-1,-1):
            values[:,j]=temp%3
            temp//=3
    values.flags.writeable=False
    return values


def _encode_ternary(vec: list[int]|tuple[int,...],length:int) -> int:
    if len(vec)!=length or any(x not in (0,1,2) for x in vec):
        raise ValueError('三态组合必须由0,1,2组成且长度固定')
    rank=0
    for x in vec:
        rank=rank*3+int(x)
    return rank


def encoding_of(number: int|str, space:str='pick23_6') -> str:
    v=mapping_array(space)[_validated_id(number)]
    if SPACES[space].kind=='combination':
        return ' '.join(f'{x:02d}' for x in v)
    # 内部0,1,2对应足彩标签0,1,3，只是编码标签，不是实际足球赛果
    return ''.join('013'[int(x)] for x in v)


def inverse_encoding(encoding: str,space:str='pick23_6') -> str|None:
    sp=SPACES[space]
    if sp.kind=='combination':
        parts=tuple(int(s)-1 for s in encoding.strip().split())
        rank=_combinadic_rank(parts,sp.alphabet,sp.positions)
    else:
        cleaned=encoding.strip()
        if len(cleaned)!=sp.positions or any(x not in '013' for x in cleaned):
            raise ValueError('三态编码必须为11位310字符')
        rank=_encode_ternary([{'0':0,'1':1,'3':2}[c] for c in cleaned],sp.positions)
    return inverse_rank(rank,space)


def _longest_run(a:np.ndarray) -> np.ndarray:
    longest=np.ones(len(a),dtype=np.int16)
    current=np.ones(len(a),dtype=np.int16)
    for col in range(1,a.shape[1]):
        current=np.where(a[:,col]==a[:,col-1],current+1,1)
        np.maximum(longest,current,out=longest)
    return longest


@lru_cache(maxsize=4)
def _indicators(space: str) -> dict[str,np.ndarray]:
    sp=SPACES[space]
    a=mapping_array(space)
    if sp.kind=='combination':
        diff=np.diff(a,axis=1)
        # 跨组合值、间距和相邻数特征
        return {
          'sum':a.sum(axis=1),
          'span':a[:,-1]-a[:,0],
          'odd_count':(a%2==1).sum(axis=1),
          'lower_half_count':(a<=(sp.alphabet//2)).sum(axis=1),
          'consecutive_pairs':(diff==1).sum(axis=1),
          'max_gap':diff.max(axis=1),
          'min_gap':diff.min(axis=1),
          'first':a[:,0],
          'last':a[:,-1],
        }
    return {
       'three_count':(a==2).sum(axis=1),
       'one_count':(a==1).sum(axis=1),
       'zero_count':(a==0).sum(axis=1),
       'same_adjacent':(np.diff(a,axis=1)==0).sum(axis=1),
       'switch_count':(np.diff(a,axis=1)!=0).sum(axis=1),
       'longest_run':_longest_run(a),
       'first_last_same':(a[:,0]==a[:,-1]).astype(np.int16),
       'weighted_sum':(a==2).sum(axis=1)*3+(a==1).sum(axis=1),
       'three_first_half':(a[:,:5]==2).sum(axis=1),
    }


def _numbers_from_digits(digits:np.ndarray) -> np.ndarray:
    if digits.ndim!=2 or digits.shape[1]!=5:
        raise ValueError('需要五列数字编码')
    return np.asarray(digits,dtype=np.int64)@_ID_WEIGHTS


def _context_feature(space: str,metric:str,now:np.ndarray,prev:np.ndarray)->np.ndarray:
    a=mapping_array(space)[_numbers_from_digits(now)]
    b=mapping_array(space)[_numbers_from_digits(prev)]
    if metric=='overlap':
        return np.sum((a[:,:,None]==b[:,None,:]).any(axis=2),axis=1).astype(np.int16)
    if metric=='same_positions':
        return np.sum(a==b,axis=1).astype(np.int16)
    if metric=='sum_delta':
        return (a.astype(np.int32).sum(axis=1)-b.astype(np.int32).sum(axis=1)).astype(np.int32)
    raise KeyError(metric)


def register_space_indicators(spaces: tuple[str,...]=('pick23_6','pick41_4','ternary11')) -> dict[str,str]:
    """注册指标到现有时序模式与排序引擎（幂等）。"""
    labels={}
    for space in spaces:
        sp=SPACES[space]
        for label,arr in _indicators(space).items():
            name=f'{space}__{label}'
            if name not in EXTRA_INDICATORS:
                register_indicator(name, lambda _digits, v=arr: v)
            labels[name]=f'{sp.label} · {label}'
        for label in ('same_positions','sum_delta')+ (('overlap',) if sp.kind=='combination' else ()):
            name=f'{space}__{label}_prev'
            if name not in CONTEXT_INDICATORS:
                register_context_indicator(name,lambda a,b,s=space,m=label:_context_feature(s,m,a,b))
            labels[name]=f'{sp.label} · 与上期{label}'
    return labels


def mapping_coverage(space:str)->dict:
    sp=SPACES[space]
    return {'space':space,'target_size':sp.size,'mapped':N_PL5,
            'unmapped':sp.size-N_PL5,
            'mapping_type':'one-to-one into subset',
            'mapping_version':f'a={sp.multiplier},b={sp.offset},mod={sp.size}',
            'fair_each_number_probability':1/N_PL5}
