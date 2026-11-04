"""V2.8 AAN/HDSE/BCSE autonomous *bounded* lift discovery and sparse distillation.

All candidate transforms are data-independent, bounded declarative ASTs (never eval).
Training estimates Dirichlet-smoothed feature ratios; a predeclared validation split
selects a small explainable set; a last holdout is consumed *once* for reporting.
This is a research score and NOT a certified lottery posterior or winning edge.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import json
import math
import sqlite3
import numpy as np
from scipy.special import logsumexp
from scipy.stats import beta, t as student_t
from .engine import DIGITS

SIZE=100_000
OPS={'add','sub','mul','absdiff','xor'}
LEAVES={'digit','lag','sum','step'}


def validate_expr(x:dict, depth:int=0)->None:
    if not isinstance(x,dict) or depth>4:raise ValueError('非法或过深的表达式')
    op=x.get('op')
    if op=='digit' and set(x)=={'op','pos'} and type(x['pos'])==int and 0<=x['pos']<=4:return
    if op=='lag' and set(x)=={'op','pos','back'} and type(x['pos'])==int and 0<=x['pos']<=4 and type(x['back'])==int and 1<=x['back']<=3:return
    if op=='sum' and set(x)=={'op'}:return
    if op=='step' and set(x)=={'op','pos'} and type(x['pos'])==int and 0<=x['pos']<=3:return
    if op in OPS and set(x)=={'op','left','right'}:
        validate_expr(x['left'],depth+1);validate_expr(x['right'],depth+1);return
    raise ValueError('表达式只允许安全的有界整数算子和指定参数')


def calc_expr(tree:dict,digits:np.ndarray,history:np.ndarray)->np.ndarray:
    """Return signed int vector; history is published draws *before* target."""
    op=tree['op']
    if op=='digit':return digits[:,tree['pos']].astype(np.int32)
    if op=='lag':
        if len(history)<tree['back']:raise ValueError('没有足够的已知历史')
        return np.full(len(digits),int(DIGITS[int(history[-tree['back']]),tree['pos']]),dtype=np.int32)
    if op=='sum':return digits.sum(axis=1,dtype=np.int32)
    if op=='step':return np.abs(digits[:,tree['pos']].astype(np.int32)-digits[:,tree['pos']+1].astype(np.int32))
    a=calc_expr(tree['left'],digits,history);b=calc_expr(tree['right'],digits,history)
    if op=='add':return a+b
    if op=='sub':return a-b
    if op=='mul':return a*b
    if op=='xor':return np.bitwise_xor(a,b)
    return np.abs(a-b)

@dataclass(frozen=True)
class Lift:
    first:dict
    second:dict
    mod_first:int
    mod_second:int
    def __post_init__(self):
        validate_expr(self.first);validate_expr(self.second)
        if type(self.mod_first)!=int or type(self.mod_second)!=int or not (2<=self.mod_first<=11 and 2<=self.mod_second<=11):
            raise ValueError('每条特征维度应为2—11')
    @property
    def id(self):
        return 'pl5.lift.'+hashlib.sha256(json.dumps(asdict(self),sort_keys=True,ensure_ascii=True).encode()).hexdigest()[:16]
    @property
    def bins(self):return self.mod_first*self.mod_second
    def codes(self,history:np.ndarray, candidates:np.ndarray|None=None)->np.ndarray:
        digits=DIGITS if candidates is None else DIGITS[candidates]
        a=calc_expr(self.first,digits,history)%self.mod_first
        b=calc_expr(self.second,digits,history)%self.mod_second
        return (a*self.mod_second+b).astype(np.int16)
    def card(self):
        return {'id':self.id,'version':'2.8.0','kind':'composed_sparse_high_dimensional_lift',
                'algorithm':asdict(self),'input':['five_digit_candidate','published_history_prefix'],
                'outputs':[f'one_hot[{self.bins}]','sparse_soft_constraint_mask[100000]'],
                'dependencies':['pl5.canonical_universe','pl5.bcse_v27','pl5.esse'],
                'execution':'safe_declarative_AST_no_python_eval','status':'research_only',
                'prediction_advantage':'unverified'}


def scalar_expr(tree:dict,digits:tuple[int,...],history:np.ndarray)->int:
    """Independent integer reference interpreter; does not invoke vector calc_expr."""
    op=tree['op']
    if op=='digit':return digits[tree['pos']]
    if op=='lag':
        prev=f'{int(history[-tree["back"]]):05d}'
        return int(prev[tree['pos']])
    if op=='sum':return sum(digits)
    if op=='step':return abs(digits[tree['pos']]-digits[tree['pos']+1])
    a=scalar_expr(tree['left'],digits,history)
    b=scalar_expr(tree['right'],digits,history)
    if op=='add':return a+b
    if op=='sub':return a-b
    if op=='mul':return a*b
    if op=='xor':return a^b
    return abs(a-b)


def scalar_codes(spec:Lift, history:np.ndarray, numbers:list[int])->np.ndarray:
    out=np.empty(len(numbers),dtype=np.int16)
    for i,num in enumerate(numbers):
        digits=tuple(int(v) for v in f'{num:05d}')
        a=scalar_expr(spec.first,digits,history)%spec.mod_first
        b=scalar_expr(spec.second,digits,history)%spec.mod_second
        out[i]=a*spec.mod_second+b
    return out


def crosscheck_full(spec:Lift,history:np.ndarray)->dict:
    vector=spec.codes(history)
    independent=scalar_codes(spec,history,list(range(SIZE)))
    if not np.array_equal(vector,independent):
        wrong=np.flatnonzero(vector!=independent)
        raise ValueError(f'高维算子独立实现不一致：号码{wrong[0]:05d}')
    return {'algorithm':spec.id,'checked':SIZE,'pass':True,
            'vector_sha256':hashlib.sha256(vector.tobytes()).hexdigest()}


def _leaf(rng:np.random.Generator)->dict:
    kind=str(rng.choice(['digit']*5+['lag']*2+['sum','step']))
    if kind=='sum':return {'op':'sum'}
    if kind=='step':return {'op':'step','pos':int(rng.integers(4))}
    if kind=='lag':return {'op':'lag','pos':int(rng.integers(5)),'back':int(rng.integers(1,4))}
    return {'op':'digit','pos':int(rng.integers(5))}


def _expr(rng:np.random.Generator)->dict:
    x={'op':str(rng.choice(sorted(OPS))),'left':_leaf(rng),'right':_leaf(rng)}
    if rng.random()<.24:
        x={'op':str(rng.choice(sorted(OPS))),'left':x,'right':_leaf(rng)}
    return x


def invent(seed:int=20261102, maximum:int=14)->list[Lift]:
    if type(seed)!=int or not 0<=seed<2**32 or type(maximum)!=int or not 2<=maximum<=24:raise ValueError('seed或maximum越界')
    rng=np.random.default_rng(seed)
    mandatory=[
      Lift({'op':'digit','pos':0},{'op':'digit','pos':1},10,10),
      Lift({'op':'digit','pos':1},{'op':'digit','pos':2},10,10),
      Lift({'op':'sub','left':{'op':'digit','pos':0},'right':{'op':'lag','pos':0,'back':1}},
           {'op':'digit','pos':4},10,10),
      Lift({'op':'sum'},{'op':'step','pos':0},9,10),
    ]
    result=mandatory[:maximum];seen={x.id for x in result}
    while len(result)<maximum:
        obj=Lift(_expr(rng),_expr(rng),int(rng.integers(3,12)),int(rng.integers(3,12)))
        if obj.id not in seen:result.append(obj);seen.add(obj.id)
    return result


def validated_history(history:list[str])->np.ndarray:
    if not isinstance(history,list) or not 150<=len(history)<=5000:raise ValueError('历史期数要求150—5000')
    if any(not isinstance(n,str) or not len(n)==5 or not n.isascii() or not n.isdecimal() for n in history):raise ValueError('号码必须为五位ASCII数字')
    return np.array([int(n) for n in history],dtype=np.int32)


def _canonical_partition(codes:np.ndarray)->str:
    # Relabeling of buckets does not create a new partition/algorithm.
    _, first, inverse = np.unique(codes, return_index=True, return_inverse=True)
    # Canonicalize *by first occurrence* so a permutation of bin labels compares equal.
    reindex = np.empty(len(first), dtype=np.uint16)
    reindex[np.argsort(first)] = np.arange(len(first),dtype=np.uint16)
    return hashlib.sha256(reindex[inverse].tobytes()).hexdigest()


def unique_lifts(specs:list[Lift], history:np.ndarray) -> tuple[list[Lift],list[dict]]:
    contexts=[history[:max(3,len(history)//2)],history]
    found=set();unique=[];duplicates=[]
    for s in specs:
        sig=':'.join(_canonical_partition(s.codes(prefix)) for prefix in contexts)
        if sig in found:duplicates.append({'id':s.id,'reason':'两个历史上下文下相同的全集分区'})
        else:unique.append(s);found.add(sig)
    return unique,duplicates


def fit_lift(spec:Lift,history:np.ndarray, train_end:int, alpha:float=120.):
    if not (3<train_end<=len(history)):raise ValueError('错误训练截止期')
    if not 20<=alpha<=5000:raise ValueError('先验强度超限')
    observed=np.zeros(spec.bins,np.float64);expected=np.zeros(spec.bins,np.float64)
    for i in range(3,train_end):
        prefix=history[:i]
        codes=spec.codes(prefix)
        expected+=np.bincount(codes,minlength=spec.bins)/SIZE
        actual=int(spec.codes(prefix,history[i:i+1])[0])
        observed[actual]+=1
    n=train_end-3
    base=expected/n
    posterior=(observed+alpha*base)/(n+alpha)
    logratio=np.log(np.maximum(posterior,1e-12)/np.maximum(base,1e-12))
    # Limit single-bin leverage and require expected count for an interpretable negative rule.
    logratio=np.clip(logratio,-2.0,2.0)
    eligible=np.flatnonzero((expected>=1.0)&(base>1e-9))
    ordered=sorted(eligible,key=lambda k:(-abs(logratio[k])*math.sqrt(expected[k]),int(k)))
    # True high-to-low distillation: 2--121 possible lifted states -> <=4 clauses.
    active=np.array([int(k) for k in ordered[:4] if abs(logratio[k])>=0.02],dtype=np.int32)
    sparse=np.zeros_like(logratio)
    sparse[active]=logratio[active]
    return {'observed':observed,'expected':expected,'baseline':base,
            'logratio':logratio,'sparse_logratio':sparse,'active':active,
            'n':n,'alpha':alpha}


def distill(spec:Lift,fit:dict,maximum=4)->list[dict]:
    observed=fit['observed'];expected=fit['expected'];base=fit['baseline']
    alpha=fit['alpha'];n=fit['n'];posterior=observed+alpha*base
    eligible=fit['active'][:maximum]
    out=[]
    for k in eligible:
        lo=float(beta.ppf(.025,posterior[k],n+alpha-posterior[k])) if posterior[k]>0 and n+alpha-posterior[k]>0 else 0
        hi=float(beta.ppf(.975,posterior[k],n+alpha-posterior[k])) if posterior[k]>0 and n+alpha-posterior[k]>0 else 1
        out.append({'bin_id':int(k),'first_value':int(k//spec.mod_second),
                    'second_value':int(k%spec.mod_second),'observed':int(observed[k]),
                    'uniform_expected':round(float(expected[k]),3),
                    'ratio_posterior_mean':round(float((observed[k]+alpha*base[k])/(n+alpha)/base[k]),5),
                    'ratio_model_95pct_credible':[float(round(lo/max(base[k],1e-12),5)),float(round(hi/max(base[k],1e-12),5))],
                    'signed_soft_penalty':round(float(-fit['sparse_logratio'][k]),5)})
    return out


def pmf(spec:Lift,fit:dict, prefix:np.ndarray, eta:float=.5)->np.ndarray:
    code=spec.codes(prefix)
    z=eta*fit['sparse_logratio'][code]
    z-=logsumexp(z)
    return np.exp(z)


def evaluate(spec:Lift,fit:dict,history:np.ndarray,start:int,end:int,eta:float)->dict:
    gains=np.empty(end-start,dtype=np.float64)
    for i in range(start,end):
        p=pmf(spec,fit,history[:i],eta)
        gains[i-start]=math.log(max(float(p[history[i]]),1e-300))+math.log(SIZE)
    mean=float(np.mean(gains))
    se=float(np.std(gains,ddof=1)/np.sqrt(len(gains))) if len(gains)>1 else math.inf
    if abs(mean)<1e-12:mean=0.
    tscore=mean/se if se and np.isfinite(se) else 0
    pvalue=float(student_t.sf(tscore,len(gains)-1)) if len(gains)>1 and se>0 else 1.
    return {'periods':len(gains),'mean_log_gain':mean,'mean_log_loss':math.log(SIZE)-mean,
            'normal_95pct_interval':[mean-1.96*se,mean+1.96*se],
            'one_sided_t_approx_p':pvalue,
            'first_half_gain':float(np.mean(gains[:len(gains)//2])),
            'second_half_gain':float(np.mean(gains[len(gains)//2:]))}


def _select(scored:list[dict],m:int,alpha:float):
    # Fixed prior on models not used to make claims of posterior odds: this is
    # a conservative *selection gate* over a searched catalog.
    eligible=[r for r in scored if r['validation']['one_sided_t_approx_p']<alpha/max(1,m)
              and r['validation']['first_half_gain']>0 and r['validation']['second_half_gain']>0]
    return max(eligible,key=lambda x:(x['validation']['mean_log_gain'],-x['index'])) if eligible else None


def study(history:list[str],*,seed:int=20261102,maximum:int=12,validation_periods:int=35,
          test_periods:int=30,budget:int=100,alpha:float=120.,gate_alpha:float=.01, register_path=None)->dict:
    ids=validated_history(history)
    if not 20<=validation_periods<=100 or not 20<=test_periods<=100 or not 1<=budget<=100:
        raise ValueError('验证/封存期或候选注数超范围')
    train_end=len(ids)-validation_periods-test_periods
    if train_end<85:raise ValueError('独立训练期至少85期')
    specs,duplicates=unique_lifts(invent(seed,maximum),ids[:train_end])
    rows=[];fits=[]
    for j,spec in enumerate(specs):
        fit=fit_lift(spec,ids,train_end,alpha)
        vals=[]
        for eta in (.5,1.):
            v=evaluate(spec,fit,ids,train_end,train_end+validation_periods,eta)
            vals.append((v['mean_log_gain'],eta,v))
        _,eta,v=max(vals,key=lambda q:q[0])
        rows.append({'id':spec.id,'index':j,'spec':asdict(spec),'feature_dimension':spec.bins,
                     'eta':eta,'validation':v,'distilled_relations':distill(spec,fit),
                     'train_count':fit['n'],'nonzero_distilled_clauses':len(fit['active'])})
        fits.append(fit)
    # Both eta choices were tested on validation, so account for BOTH in the search multiplicity.
    selected=_select(rows,2*len(rows),gate_alpha)
    holdout_start=train_end+validation_periods
    holdout=(evaluate(specs[selected['index']],fits[selected['index']],ids,holdout_start,len(ids),selected['eta'])
             if selected else {'periods':test_periods,'mean_log_gain':0.,'mean_log_loss':math.log(SIZE),
                'note':'验证未通过；最终封存期采用均匀基线'})
    if selected:
        probs=pmf(specs[selected['index']],fits[selected['index']],ids,selected['eta'])
        rng=np.random.default_rng(seed);tie=rng.random(SIZE)
        order=np.lexsort((tie,-probs))
        chosen=order[:budget]
        next_relations=distill(specs[selected['index']],fits[selected['index']])
    else:
        probs=np.full(SIZE,1/SIZE)
        chosen=np.random.default_rng(seed).choice(SIZE,size=budget,replace=False)
        next_relations=[]
    control=np.random.default_rng(seed^0xC0FFEE).choice(SIZE,size=budget,replace=False)
    candidates=[f'{int(n):05d}' for n in chosen]
    cards=[s.card() for s in specs]
    report={'version':'pl5-v28-autolift','status':'research_only','seed':seed,
       'source':'provided_history_unverified','history_sha256':hashlib.sha256('|'.join(history).encode()).hexdigest(),
       'splits':{'train_count':train_end,'validation_periods':validation_periods,'sealed_holdout_periods':test_periods},
       'generated':len(invent(seed,maximum)),'unique':len(specs),'duplicates':duplicates,
       'search_multiplicity':2*len(rows),'selection_alpha':gate_alpha,
       'operator_cards':cards,'experiments':rows,
       'selected_operator':selected['id'] if selected else None,
       'selected_eta':selected['eta'] if selected else 0.,
       'holdout':holdout,'gate':{'passed':bool(selected),'reason':'仅在开发验证通过Bonferroni近似门槛；非未来预测证明' if selected else '开发验证未达到多重检验门槛；均匀回退'},
       'next_draw_distilled_soft_constraints':next_relations,
       'independent_operator_crosscheck':crosscheck_full(specs[selected['index']] if selected else specs[0],ids),
       'next_draw_prob_sum':float(probs.sum()),
       'experimental_top_k':candidates,'equal_budget_random_control':[f'{int(n):05d}' for n in control],
       'fair_independent_hit_probability':budget/SIZE,
       'next_draw_score_notes':'模型分配概率只在所拟合的高维特征族下成立；不等于真实中奖概率',
       'future_work':[{'candidate':r['id'],'reason':'未满足证据门槛，优先检验结构是否为随机噪声'} for r in sorted(rows,key=lambda x:-x['validation']['mean_log_gain'])[:3] if not selected or r['id']!=selected['id']],
       'algorithm_promotion':'FORBIDDEN_WITHOUT_APPROVAL_AND_PROSPECTIVE_EVIDENCE'}
    if register_path is not None:register(report,register_path)
    return report


def register(report:dict,path:str|Path)->int:
    """Append-only research capability cards; never edits production ESSE rules."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS v28_algorithms(id TEXT PRIMARY KEY, card_json TEXT NOT NULL, registered_at TEXT DEFAULT CURRENT_TIMESTAMP, status TEXT NOT NULL CHECK(status="research_only"))')
        db.execute('CREATE TABLE IF NOT EXISTS v28_runs(run_hash TEXT PRIMARY KEY, report_json TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
        count=0
        for card in report['operator_cards']:
            cur=db.execute('INSERT OR IGNORE INTO v28_algorithms(id,card_json,status) VALUES(?,?,"research_only")',(card['id'],json.dumps(card,sort_keys=True)))
            count+=cur.rowcount
        payload=json.dumps(report,sort_keys=True,ensure_ascii=False,allow_nan=False)
        digest=hashlib.sha256(payload.encode()).hexdigest()
        db.execute('INSERT OR IGNORE INTO v28_runs(run_hash,report_json) VALUES(?,?)',(digest,payload))
    return count
