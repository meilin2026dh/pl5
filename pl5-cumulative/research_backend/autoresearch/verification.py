"""Falsification-first verification for bounded PL5 formula hypotheses.

Engineering replication is distinct from statistical evidence of predictive
advantage. In a fair lottery any pre-draw fixed K-set has hit probability K/100000.
"""
from __future__ import annotations
from dataclasses import asdict
from hashlib import sha256
import json
import math
import numpy as np
from scipy.stats import binomtest
from .formulas import InventedAlgorithm,vector_eval,scalar_eval

N=100_000


def _progression_match(values,pattern):
    vals=np.asarray(values,dtype=np.int64)
    diff=np.diff(vals)
    if pattern=='constant':return bool(np.all(vals==vals[0]))
    if pattern=='arithmetic':return bool(np.all(diff==diff[0]))
    if pattern=='period2':return bool(len(vals)>=4 and np.all(vals[2:]==vals[:-2]))
    if pattern=='strict_up':return bool(np.all(diff>0))
    if pattern=='strict_down':return bool(np.all(diff<0))
    return False


def _extension_mask(values,pattern,seq):
    last=int(seq[-1])
    if pattern=='constant':return values==last
    if pattern=='arithmetic':return values==(last+int(seq[-1]-seq[-2]))
    if pattern=='period2':return values==int(seq[-2])
    if pattern=='strict_up':return values>last
    if pattern=='strict_down':return values<last
    raise ValueError('模式未知')


def choose_candidate_ids(algorithm,history,*,k=100,cache=None):
    algorithm.validate()
    if not 1<=k<=100:raise ValueError('研究候选必须在1..100注')
    if len(history)<algorithm.window:raise ValueError('历史期数不足')
    ids=np.asarray([int(x) for x in history],dtype=np.int64)
    if np.any((ids<0)|(ids>=N)):raise ValueError('开奖号超出00000-99999')
    vals=cache if cache is not None else vector_eval(algorithm.formula)
    trailing=vals[ids[-algorithm.window:]]
    triggered=_progression_match(trailing,algorithm.pattern)
    mask=_extension_mask(vals,algorithm.pattern,trailing) if triggered else np.zeros(N,dtype=bool)
    # Deterministic, period-specific tie-breaker independent of the *next* draw.
    seed=int.from_bytes(sha256((algorithm.fingerprint()+'|'+','.join(str(x) for x in ids[-20:])).encode()).digest()[:8],'big')
    perm=np.random.default_rng(seed).permutation(N)
    choice=np.concatenate((perm[~mask[perm]],perm[mask[perm]]))[:k]
    return choice, {'triggered':bool(triggered),'excluded':int(mask.sum()),
                    'kept':int(k),'fallback_included':int(mask[choice].sum()),
                    'selection_sha256':sha256(choice.tobytes()).hexdigest()}


def replicate_formula(algorithm,*,sample=256):
    algorithm.validate()
    if not 32<=sample<=1024:raise ValueError('复现抽样量异常')
    arr=vector_eval(algorithm.formula)
    seed=int(algorithm.fingerprint()[:12],16)
    ids=np.random.default_rng(seed).choice(N,size=sample,replace=False)
    mismatch=[int(i) for i in ids if int(arr[i])!=scalar_eval(algorithm.formula,int(i))]
    return {'sample':sample,'matches':len(mismatch)==0,'mismatches':mismatch[:5],
            'value_sha256':sha256(arr.tobytes()).hexdigest()}


def walk_forward_falsify(algorithm,draws,*,k=100,eval_size=120,min_train=36,
                         null_sequences=6,null_length=120):
    algorithm.validate()
    if not 1<=k<=100:raise ValueError('K必须1..100')
    if not 20<=eval_size<=600:raise ValueError('回测期数限制20..600')
    if not 0<=null_sequences<=20 or not 30<=null_length<=300:raise ValueError('零假设模拟预算限制')
    seq=list(draws)
    if len(seq)<min_train+20:raise ValueError('至少需要56期按时间排序的历史数据')
    if any(not isinstance(x,str) or len(x)!=5 or not x.isascii() or not x.isdigit() for x in seq):
        raise ValueError('必须使用保留前导零的五位开奖号码')
    data=vector_eval(algorithm.formula)
    start=max(min_train,len(seq)-eval_size)
    predictions=[];hit=0;triggers=0;exclusions=0
    for t in range(start,len(seq)):
        chosen,details=choose_candidate_ids(algorithm,seq[:t],k=k,cache=data)
        target=int(seq[t]);matched=bool(np.any(chosen==target));hit+=int(matched)
        triggers+=int(details['triggered']);exclusions+=details['excluded']
        predictions.append({'position':t,'hit':matched,'candidate_sha256':details['selection_sha256'],
                            'triggered':details['triggered']})
    n=len(predictions);baseline=k/N
    p=float(binomtest(hit,n,p=baseline,alternative='greater').pvalue)
    # Empirical null: the entire pipeline runs on NEW iid fair synthetic draws.
    # Each synthetic run is NOT a proof of calibration, just a falsification check.
    rng=np.random.default_rng(int(algorithm.fingerprint()[:16],16))
    null_hits=[]
    for j in range(null_sequences):
        fake=[f'{int(x):05d}' for x in rng.integers(0,N,size=min_train+null_length)]
        h=0
        for t in range(min_train,len(fake)):
            selected,_=choose_candidate_ids(algorithm,fake[:t],k=k,cache=data)
            h+=int(np.any(selected==int(fake[t])))
        null_hits.append(h)
    # Anti-leakage sanity: exact results reproduce without using the target number.
    last_history=seq[:start]
    p1,_=choose_candidate_ids(algorithm,last_history,k=k,cache=data)
    p2,_=choose_candidate_ids(algorithm,list(last_history),k=k,cache=None)
    replicated=bool(np.array_equal(p1,p2))
    return {
        'algorithm':algorithm.fingerprint(),'phase':'development_only',
        'n':n,'hits':hit,'expected_fair_hits':round(n*baseline,6),
        'baseline_per_period':baseline,'one_sided_unadjusted_p':p,
        'pattern_trigger_count':triggers,'mean_excluded':exclusions/n,
        'null_fair_sequences':null_sequences,'null_periods_per_sequence':null_length,
        'null_hits':null_hits,'reproduced_candidates':replicated,
        'prediction_digest':sha256(json.dumps(predictions,sort_keys=True).encode()).hexdigest(),
        'inference_warning':'开发集反复挑选引起选择偏差；p值未校正搜索历史，不能证明预测优势。'
    }


def full_audit(algorithm,draws,*,k=100,eval_size=80,null_sequences=4,attempts=1):
    replica=replicate_formula(algorithm)
    report=walk_forward_falsify(algorithm,draws,k=k,eval_size=eval_size,null_sequences=null_sequences)
    engineering_ok=bool(replica['matches'] and report['reproduced_candidates'])
    attempts=max(1,int(attempts))
    adjusted_p=min(1.0,attempts*report['one_sided_unadjusted_p'])
    return {'engineering_reproduced':engineering_ok,'independent_scalar_replication':replica,
            'development':report,'all_discovery_attempts_counted':attempts,
            'bonferroni_exploratory_p':adjusted_p,'prediction_validated':False,
            'approved_for_research_registry':False,
            'explanation':'工程复现通过不等于概率提升；正式使用须人工审批和预注册未来开奖验证。'}


def rank_research_approved(algorithms,history,*,k=100):
    """Optional separate research ranking, NOT a calibrated prediction.

    Only explicitly approved formula research can vote; no change to legacy
    active algorithm set, and no auto-promotion from development p-values.
    """
    if not 1<=k<=100:raise ValueError('K必须1..100')
    if not history or any(not isinstance(x,str) or len(x)!=5 or not x.isascii() or not x.isdigit() for x in history):
        raise ValueError('历史开奖格式不合法')
    if len(algorithms)>24:raise ValueError('单次最多允许24条已审批研究公式')
    scores=np.zeros(N,dtype=np.float32)
    evidence=[];seen=set()
    for algorithm in algorithms:
        algorithm.validate()
        if algorithm.fingerprint() in seen:continue
        seen.add(algorithm.fingerprint())
        vals=vector_eval(algorithm.formula)
        ids=np.asarray([int(x) for x in history[-algorithm.window:]],dtype=np.int64)
        if len(ids)<algorithm.window:continue
        recent=vals[ids]
        trigger=_progression_match(recent,algorithm.pattern)
        mask=_extension_mask(vals,algorithm.pattern,recent) if trigger else np.zeros(N,dtype=bool)
        scores+=mask.astype(np.float32)
        evidence.append({'fingerprint':algorithm.fingerprint(),'triggered':bool(trigger),
                         'excluded':int(mask.sum())})
    seed=int.from_bytes(sha256(('V06|'+','.join(history[-20:])).encode()).digest()[:8],'big')
    tie=np.random.default_rng(seed).random(N)
    ordered=np.lexsort((tie,scores))[:k]
    return [f'{int(i):05d}' for i in ordered],{
        'n_algorithms':len(seen),'rules':evidence,'fair_baseline_coverage':k/N,
        'ranking_is_uncalibrated':True,'predicted_success_rate_claimed':False}
