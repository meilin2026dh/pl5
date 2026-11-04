"""V0.7 prospective verification. Does not establish true pre-draw timestamps.

A fixed mixture of per-draw Bernoulli likelihood ratios is an e-process under
an iid uniform lottery if all candidate sets were fixed before each draw.
This module treats *local* precommitment as an auditable record, not a trusted
external timestamp. Selective settlement or retrospective entries break claims.
"""
from __future__ import annotations
from hashlib import sha256
import json
import math
import sqlite3
from . import prospective

N=100000
FACTORS=(1.5, 2.0, 5.0, 10.0)


def _canon(data):
    return json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'))


def verify_commitments(db:sqlite3.Connection):
    prospective.initialize(db)
    sql='SELECT target_period,previous_period,created_at,candidates_json,history_sha256,algorithm_sha256,source_description,commitment_sha256 FROM predictions'
    results=[]
    for period,previous,created,items,history,algo,source,hashcode in db.execute(sql):
        try:
            record={'target_period':period,'previous_period':previous,'created_at':created,
                    'candidates':json.loads(items),'history_sha256':history,
                    'algorithm_sha256':algo,'source_description':source}
            expected=sha256(_canon(record).encode()).hexdigest()
            ok=expected==hashcode and 1<=len(set(record['candidates']))<=100 and len(record['candidates'])==len(set(record['candidates']))
        except (ValueError,TypeError):ok=False
        results.append({'period':period,'hash_intact':bool(ok)})
    return {'total':len(results),'all_hashes_intact':all(x['hash_intact'] for x in results),
            'invalid_periods':[x['period'] for x in results if not x['hash_intact']]}


def _poisson_binomial_tail(probabilities:list[float],hits:int):
    # Exact fixed-horizon probability P(S>=hits) for variable predeclared K.
    n=len(probabilities)
    if hits<=0:return 1.0
    if hits>n:return 0.0
    dp=[1.0]+[0.0]*n
    for t,p in enumerate(probabilities,1):
        for j in range(t,0,-1):dp[j]=dp[j]*(1-p)+dp[j-1]*p
        dp[0]*=1-p
    return min(1.0,max(0.0,sum(dp[hits:])))


def _mixture_e_value(rows):
    # Each multiplier's conditional expectation is exactly 1 under the null.
    # No future outcome appears in either q or p selection.
    log_lrs=[0.0]*len(FACTORS)
    for r in rows:
        p=r['k']/N
        h=r['hit']
        for j,factor in enumerate(FACTORS):
            q=min(0.5,factor*p)
            log_lrs[j]+= math.log(q/p) if h else math.log1p(-q)-math.log1p(-p)
    logs=[z-math.log(len(FACTORS)) for z in log_lrs]
    maximum=max(logs,default=0.0)
    log_e=maximum+math.log(sum(math.exp(z-maximum) for z in logs))
    value=math.exp(log_e) if -700 < log_e < 690 else (None if log_e>=690 else 0.0)
    return {'e_value':None if value is None else round(value,8),
            'log_e_value':round(log_e,6),
            'interpretation':'e≥20对应固定单模型零假设下≤5%的随时监控误报上界；多模型/选择性公布需额外修正'}


def forward_report(db:sqlite3.Connection):
    prospective.initialize(db)
    integrity=verify_commitments(db)
    raw=db.execute('''SELECT p.target_period,p.previous_period,p.created_at,p.candidates_json,
       o.result,o.is_hit,o.observed_at FROM predictions p
       LEFT JOIN outcomes o ON p.target_period=o.target_period
       ORDER BY CAST(p.target_period AS INTEGER)''').fetchall()
    entries=[]
    for period,previous,created,items,result,hit,observed in raw:
        entries.append({'period':period,'previous_period':previous,'created':created,
                        'k':len(json.loads(items)),'result':result,'hit':None if hit is None else bool(hit),
                        'observed':observed})
    settled=[x for x in entries if x['hit'] is not None]
    # A pending earlier period blocks a headline e-value; later records must not
    # silently cherry-pick favorable wins from after unresolved predictions.
    prefix=[]
    for item in entries:
        if item['hit'] is None:break
        prefix.append(item)
    probs=[r['k']/N for r in prefix]
    hits=sum(int(r['hit']) for r in prefix)
    missing=len(settled)-len(prefix)
    baseline=sum(probs)
    groups=[]
    for start in range(0,len(prefix)//10*10,10):
        block=prefix[start:start+10]
        miss=math.prod(1-r['k']/N for r in block)
        groups.append({'period_start':block[0]['period'],'period_end':block[-1]['period'],
                       'any_hit':any(r['hit'] for r in block),
                       'fair_baseline_any_hit':round(1-miss,8),
                       'description':'连续10条已封存且按期排序的记录；并非保证覆盖所有实际开奖期'})
    integrity_ok=integrity['all_hashes_intact']
    e=_mixture_e_value(prefix) if integrity_ok and prefix else None
    return {'registered':len(entries),'settled_total':len(settled),'pending':len(entries)-len(settled),
            'auditable_contiguous_prefix':len(prefix),'settled_after_pending_not_counted':missing,
            'observed_hits_in_prefix':hits,'expected_fair_hits_in_prefix':round(baseline,6),
            'baseline_total':round(baseline,6),'nonoverlapping_10_record_blocks':groups,
            'fixed_horizon_p_value_unadjusted':_poisson_binomial_tail(probs,hits) if prefix and integrity_ok else None,
            'anytime_e_evidence':e,'commitment_integrity':integrity,
            'predictive_edge_proven':False,
            'limitations':[
                '本地不可变数据库和SHA256不能单独证明记录早于开奖或官方数据真实性',
                '回测选出的策略若在前向期继续优化，需注册新的独立验证系列',
                '如果有缺失开奖结果，只报告首个缺口之前的连续已结算前缀',
                '未经校正不得跨模型、多策略重复使用e-process证据',
                '每10条已注册预测不一定包含所有相邻实际开奖期，不可声称十期必中'
            ]}


def freeze_checked(db:sqlite3.Connection, *,draws_frame,target_period:str,candidates:list[str],
                   history_sha256:str,algorithm_sha256:str,official_source:str):
    if len(draws_frame)<1:raise ValueError('无历史期开奖数据')
    periods=draws_frame['period'].astype(str).tolist()
    if target_period in set(periods):raise ValueError('目标期号已出现在输入开奖历史中，禁止事后封存')
    prospective.initialize(db)
    latest=db.execute('SELECT MAX(CAST(target_period AS INTEGER)) FROM predictions').fetchone()[0]
    if latest is not None and int(target_period)<=int(latest):
        raise ValueError('预注册必须按目标期号严格递增；不允许回填先前漏登记的期号')
    return prospective.precommit(db,target_period=target_period,previous_period=periods[-1],
        candidates=candidates,history_sha256=history_sha256,
        algorithm_sha256=algorithm_sha256,source_description=official_source)
