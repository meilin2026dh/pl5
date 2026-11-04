"""V0.7: Structural novelty is NOT predictive power.

All novelty decisions use the entire predeclared 100,000-number space, never the
next draw; any approved algorithm still needs genuinely prospective evidence.
"""
from __future__ import annotations
from hashlib import sha256
import numpy as np
from .formulas import InventedAlgorithm, invent_from_text, vector_eval

N=100000


def signature(algorithm:InventedAlgorithm):
    algorithm.validate()
    vals=vector_eval(algorithm.formula)
    unique,counts=np.unique(vals,return_counts=True)
    probs=counts.astype(float)/N
    entropy=float(-(probs*np.log2(probs)).sum())
    return {'formula_signature':sha256(vals.astype('<i8').tobytes()).hexdigest(),
            'unique_states':len(unique),'entropy_bits':round(entropy,6),
            'largest_state_share':round(float(probs.max()),6)}, vals


def _correlation(a,b):
    x=np.asarray(a,dtype=float);y=np.asarray(b,dtype=float)
    x-=x.mean();y-=y.mean()
    norm=float(np.linalg.norm(x)*np.linalg.norm(y))
    return 1.0 if norm==0 else abs(float(np.dot(x,y)/norm))


def assess_novelty(candidate:InventedAlgorithm, existing:list[InventedAlgorithm],
                   *,min_entropy_bits=.5,max_abs_correlation=.995):
    if len(existing)>80:raise ValueError('单次最多比较80种候选公式')
    sig,arr=signature(candidate)
    most=None;max_corr=0.;exact=False
    for old in existing:
        old_sig,b=signature(old)
        if sig['formula_signature']==old_sig['formula_signature']:
            exact=True;most=old.fingerprint();max_corr=1.;break
        corr=_correlation(arr,b)
        if corr>max_corr:most=old.fingerprint();max_corr=corr
    reasons=[]
    if exact:reasons.append('与已存在指标的十万号码输出逐项相同')
    if sig['entropy_bits']<min_entropy_bits:reasons.append('指标信息熵过低，接近常量')
    if existing and max_corr>=max_abs_correlation:reasons.append('与现有指标高度线性相关')
    return {**sig,'candidate':candidate.fingerprint(),'most_similar':most,
            'max_abs_pearson':round(max_corr,6),'is_novel_by_heuristic':not bool(reasons),
            'rejection_reasons':reasons,
            'caution':'仅是特征冗余与研究资源筛选，不代表预测优势或彩票概率变化'}


def invent_diverse(text:str,source_key:str,*,limit=4,
                   already:list[InventedAlgorithm]|None=None,search_budget=24):
    if not 1<=limit<=12 or not limit<=search_budget<=24:
        raise ValueError('每轮限制1..12个新假设，最多24次公式搜索')
    chosen=[];logs=[]
    candidates=invent_from_text(text,source_key,limit=search_budget)
    pool=list(already or [])
    for a in candidates:
        report=assess_novelty(a,pool)
        logs.append(report)
        if report['is_novel_by_heuristic']:
            chosen.append(a);pool.append(a)
        if len(chosen)>=limit:break
    return chosen,{'evaluated':len(logs),'accepted':len(chosen),
                   'rejected':sum(not x['is_novel_by_heuristic'] for x in logs),
                   'records':logs,
                   'warning':'新颖度门槛本身需要模拟数据审计；不会因此自动进入选号库'}
