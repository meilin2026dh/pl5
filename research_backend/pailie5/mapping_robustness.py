"""固定映射及置换安慰剂对照的时序反延续稳健性检验。

一组预先固定的不同仿射映射（每组保持PL5->目标空间单射）使用相同算法、
相同历史窗口、相同待测期，比较：模式检出次数、规则涉及的号码集合和未来样本排序。
它是探索性检查，不可把多个对照里最佳的一个当作未经选择的证据。
"""
from __future__ import annotations

from functools import lru_cache
from dataclasses import dataclass
import hashlib
from math import comb, gcd, log

import numpy as np
import pandas as pd

from .space_mapping import SPACES, N_PL5, _combinadic_unrank
from .pattern_rules import PATTERNS, _valid_draw_numbers


BASE_METRICS = {
    'combination': ('sum','span','odd_count','consecutive_pairs','max_gap','min_gap','first','last'),
    'ternary': ('three_count','one_count','zero_count','same_adjacent','switch_count','longest_run','weighted_sum')
}


@lru_cache(maxsize=18)
def variant_arrays(space: str, multiplier: int, offset: int) -> np.ndarray:
    """不同映射版本的完整10万状态，既不改动现有Space定义也不污染全局指标表。"""
    sp = SPACES[space]
    if gcd(int(multiplier), sp.size) != 1 or not 0 <= offset < sp.size:
        raise ValueError('非法的可逆映射参数')
    ranks=(int(multiplier)*np.arange(N_PL5,dtype=np.int64)+int(offset))%sp.size
    if sp.kind=='combination':
        a=_combinadic_unrank(ranks,sp.alphabet,sp.positions).astype(np.int16)+1
    else:
        a=np.empty((N_PL5,sp.positions),dtype=np.int16)
        x=ranks.copy()
        for p in range(sp.positions-1,-1,-1):
            a[:,p]=x%3
            x//=3
    a.flags.writeable=False
    return a


@lru_cache(maxsize=18)
def variant_features(space: str, multiplier: int, offset: int) -> dict[str,np.ndarray]:
    sp=SPACES[space]
    a=variant_arrays(space,multiplier,offset)
    diff=np.diff(a,axis=1)
    if sp.kind=='combination':
        out={
          'sum':a.sum(axis=1), 'span':a[:,-1]-a[:,0],
          'odd_count':(a%2==1).sum(axis=1),
          'consecutive_pairs':(diff==1).sum(axis=1),
          'max_gap':diff.max(axis=1), 'min_gap':diff.min(axis=1),
          'first':a[:,0], 'last':a[:,-1],
        }
    else:
        longest=np.ones(N_PL5,dtype=np.int16)
        current=np.ones(N_PL5,dtype=np.int16)
        for p in range(1,sp.positions):
            current=np.where(a[:,p]==a[:,p-1],current+1,1)
            np.maximum(longest,current,out=longest)
        out={
          'three_count':(a==2).sum(axis=1),
          'one_count':(a==1).sum(axis=1),
          'zero_count':(a==0).sum(axis=1),
          'same_adjacent':(diff==0).sum(axis=1),
          'switch_count':(diff!=0).sum(axis=1),
          'longest_run':longest,
          'weighted_sum':(a==2).sum(axis=1)*3+(a==1).sum(axis=1),
        }
    for v in out.values(): v.flags.writeable=False
    return out


def fixed_variants(space: str, count: int = 5, seed: str = 'pl5-v04-fixed-baseline') -> list[dict]:
    """默认首个为正式映射，其余用哈希派生固定对照；seed预先登记不可事后调整。"""
    if not 2 <= count <= 12:
        raise ValueError('映射总数必须为2..12（含正式映射）')
    sp=SPACES[space]
    result=[{'variant':'canonical','multiplier':sp.multiplier,'offset':sp.offset,'role':'candidate'}]
    visited={(sp.multiplier,sp.offset)}
    for i in range(1,count):
        nonce=0
        while True:
            raw=hashlib.sha256(f'{seed}|{space}|{i}|{nonce}'.encode()).digest()
            multiplier=1+int.from_bytes(raw[:8],'big')%(sp.size-1)
            offset=int.from_bytes(raw[8:16],'big')%sp.size
            if gcd(multiplier,sp.size)==1 and (multiplier,offset) not in visited:
                break
            nonce+=1
        visited.add((multiplier,offset))
        result.append({'variant':f'placebo_{i:02d}', 'multiplier':multiplier,'offset':offset,'role':'placebo'})
    return result


def _pattern_mask(history_ids: np.ndarray, features: dict[str,np.ndarray],
                  metrics: tuple[str,...], window:int, patterns:tuple[str,...],
                  transform: str) -> tuple[np.ndarray, int, int]:
    """所有特征按相同参数生成反延续规则，单指标多模式取并集，空间等权。"""
    penalty=np.zeros(N_PL5,dtype=np.float32)
    count=0
    for name in metrics:
        arr=features[name]
        vals=arr if transform=='raw' else arr%int(transform[3:])
        observed=vals[history_ids[-window:]]
        options=np.unique(vals)
        flagged=np.zeros(N_PL5,dtype=bool)
        for pattern in patterns:
            det=PATTERNS[pattern]
            if pattern=='period2' and window<4: continue
            if pattern=='period3' and window<6: continue
            if not det(observed):continue
            ending=[v for v in options if det(np.r_[observed,v])]
            if ending:
                flagged |= np.isin(vals,ending)
                count+=1
        penalty+=flagged.astype(np.float32)
    return penalty/max(1,len(metrics)), count, int(np.count_nonzero(penalty))


def _rank_of(actual: int, penalty: np.ndarray) -> int:
    # 相同惩罚的号码索引小的排名靠前，与multi_space_study完全一致。
    return int(np.count_nonzero(penalty < penalty[actual]) +
               np.count_nonzero((penalty == penalty[actual]) & (np.arange(N_PL5)<=actual)))


def _mapped_score(history: np.ndarray, features:dict[str,np.ndarray],metrics:tuple[str,...],
                  window:int,patterns:tuple[str,...],transform:str) -> tuple[np.ndarray,int,int]:
    return _pattern_mask(history,features,metrics,window,patterns,transform)


def robustness_study(
    history: list[str], space:str, metrics: tuple[str,...], *,
    window:int=4,patterns:tuple[str,...]=('constant','strict_up','strict_down','arithmetic'),
    transform:str='raw',variant_count:int=5,seed:str='pl5-v04-fixed-baseline',
    warmup:int=40, holdout:int=30, top_k:int=1000, strength:float=1.0,
) -> dict:
    """所有映射在相同、时间上滞后的滚动预测窗口比较。

    不能在这里根据结果改变映射；后续重复检验须另留独立未来样本。
    """
    if space not in SPACES: raise ValueError('未知映射空间')
    if not metrics or any(m not in BASE_METRICS[SPACES[space].kind] for m in metrics):
        raise ValueError('选用了当前空间不支持的指标')
    if not 3<=window<=12: raise ValueError('窗口限制3至12')
    if not patterns or any(p not in PATTERNS for p in patterns):
        raise ValueError('模式类型错误')
    if transform not in ('raw','mod2','mod3','mod5','mod10'):
        raise ValueError('未知指标变换')
    if not 1 <= top_k <= N_PL5 or not 0 <= strength <= 8:
        raise ValueError('top_k/strength超出范围')
    if warmup < window or holdout < 1:
        raise ValueError('warmup必须不小于窗口，holdout必须>=1')
    draws=_valid_draw_numbers(history)
    start=max(warmup,len(draws)-holdout)
    if start>=len(draws): raise ValueError('数据不足，无法执行滚动回测')
    variants=fixed_variants(space,variant_count,seed)
    results=[]
    details=[]
    last_masks={}
    for var in variants:
        name=var['variant']
        arr=variant_features(space,var['multiplier'],var['offset'])
        hits=0
        total_loss=0.
        triggered=0
        rows=[]
        for t in range(start,len(draws)):
            penalty,nrules,_=_mapped_score(draws[:t],arr,metrics,window,patterns,transform)
            actual=int(draws[t])
            rank=_rank_of(actual,penalty)
            logits=-strength*penalty.astype(np.float64)
            normalized=np.exp(logits-logits.max())
            prob=float(normalized[actual]/normalized.sum())
            loss=-log(prob)
            hit=rank<=top_k
            hits+=hit
            total_loss+=loss
            triggered+=nrules
            rows.append({'variant':name,'index':t,'actual':f'{actual:05d}',
                         'rank':rank,'top_k_hit':bool(hit), 'model_weight':prob,
                         'active_patterns':nrules})
        # 末尾历史仅用于当下剔除集合重合度，而非用于过去样本的预测。
        current, current_count,_ =_mapped_score(draws,arr,metrics,window,patterns,transform)
        last_masks[name]=current>0
        n=len(rows)
        results.append({'variant':name,'role':var['role'],
                        'multiplier':var['multiplier'],'offset':var['offset'],
                        'periods':n,'top_k_hits':int(hits),
                        'observed_hit_rate':hits/n,'fair_expected_hits':n*top_k/N_PL5,
                        'average_log_loss':total_loss/n,
                        'logloss_improvement_vs_fair':log(N_PL5)-total_loss/n,
                        'total_active_patterns':triggered,
                        'current_active_patterns':current_count,
                        'current_flagged_coverage':float(last_masks[name].mean())})
        details.extend(rows)
    original=last_masks['canonical']
    similarities=[]
    for var in variants[1:]:
        compare=last_masks[var['variant']]
        intersection=int((original & compare).sum())
        union=int((original | compare).sum())
        similarities.append({'variant':var['variant'],
                            'jaccard_with_canonical':intersection/union if union else None,
                            'overlap_count':intersection,
                            'canonical_exclusions':int(original.sum()),
                            'placebo_exclusions':int(compare.sum()),
                            'note':'双方均未触发规则，不可据此判断稳健' if not union else ''})
    canonical=results[0]
    # 非统计显著性：仅记录固定对照里排列位置，拒绝用胜出当作真实优势证据。
    better_or_equal=sum(p['average_log_loss']<=canonical['average_log_loss']
                        for p in results[1:])
    signature=hashlib.sha256(repr((space,metrics,window,patterns,transform,variant_count,
                                   seed,warmup,holdout,top_k,strength,start)).encode()).hexdigest()
    return {'space':space,'metrics':list(metrics),'model_type':'noncalibrated_heuristic',
            'config_sha256':signature,'variant_seed':seed,'top_k':top_k,
            'history_length':len(history),'test_start_index':start,
            'fair_expected_per_period':top_k/N_PL5,
            'canonical':canonical,'variants':results,'current_set_overlap':similarities,
            'placebos_not_worse_logloss':better_or_equal,
            'note':'所有对照使用同一过去信息和同一期样本。结果仅为探索性，不是独立封存验证；'
                   '相似度低表示结论依赖映射选择，不能挑表现最好的映射作为有效预测。'
                   '公平独立开奖下10万号码真实概率均相等。',
            'details':details}
