"""PL5 V2.7 BCSE: Bayesian finite-model soft constraints on 100,000 candidates.

This is a *research posterior over a specified model catalog*, not a guarantee
about the physical draw, and not a probability that a deterministic violation
occurred. Posterior credible intervals are conditional on this model catalog.

Protocol: 60 initial draws fit a frozen positional Dirichlet baseline;
remaining training draws update the Bayesian posterior over fixed models;
validation chooses whether to activate the model; holdout is never used to
choose a model or tune a threshold. The next-draw report uses the locked
training posterior. All dynamic masks use only already published prefixes.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from collections import Counter
import hashlib
import json
import math

import numpy as np
from .engine import DIGITS

N=100_000
LOG_N=math.log(N)
WARMUP=60
KIND_LIST=('step_large','route_zero_absent','parity_extreme',
           'sum_tail_repeat','sum_arithmetic','position_repeat')

@dataclass(frozen=True)
class Constraint:
    id: str
    kind: str
    threshold: int=7
    def __post_init__(self):
        if not isinstance(self.id,str) or not self.id or len(self.id)>64 or not all(c.isascii() and (c.isalnum() or c in '-_.') for c in self.id):
            raise ValueError('约束ID必须为1—64位ASCII字母/数字/._-')
        if self.kind not in KIND_LIST:raise ValueError('不支持的约束类型')
        if type(self.threshold) is not int or (self.kind=='step_large' and not 1<=self.threshold<=9) or (self.kind!='step_large' and self.threshold!=7):
            raise ValueError('步长阈值必须为1—9，其他约束不得设置虚假参数')
    def card(self):
        return {'id':self.id,'version':'2.7.0','kind':'boolean_soft_constraint',
            'type':self.kind,'parameters':{'threshold':self.threshold} if self.kind=='step_large' else {},
            'inputs':['five_digit_universe','history_prefix_before_target'],
            'outputs':['violation_mask[100000]','violation_reason'],
            'assumptions':['historical information only','the violation is deterministic'],
            'predictive_advantage':'unverified','permission':'research_only',
            'description':'统计约束的数学定义和统计可信性是两件不同的事情'}

DEFAULT_CONSTRAINTS=tuple(Constraint(k,k) for k in KIND_LIST)


def constraints_from_json(rows=None)->tuple[Constraint,...]:
    if rows is None:return DEFAULT_CONSTRAINTS
    if not isinstance(rows,list) or not 1<=len(rows)<=8:raise ValueError('约束应为1—8条列表')
    out=[]
    for r in rows:
        if not isinstance(r,dict) or not {'id','kind'}<=set(r) or set(r)-{'id','kind','threshold'}:
            raise ValueError('约束参数不合法')
        out.append(Constraint(**r))
    if len(set(x.id for x in out))!=len(out):raise ValueError('约束ID重复')
    return tuple(out)


def validate_history(history):
    if not isinstance(history,(list,tuple)) or not 150<=len(history)<=10000:
        raise ValueError('历史记录必须按时间从早到晚排列，至少150期、最多10000期')
    if any(not isinstance(x,str) or len(x)!=5 or not x.isascii() or not x.isdecimal() for x in history):
        raise ValueError('历史号码必须是五位ASCII数字字符串并保留前导零')
    return np.fromiter((int(x) for x in history),dtype=np.int32,count=len(history))


def constraint_masks(prefix_ids, constraints=DEFAULT_CONSTRAINTS):
    """Deterministic mask of violations evaluated *before* the target draw."""
    if not isinstance(prefix_ids,np.ndarray):prefix_ids=np.asarray(prefix_ids,dtype=np.int32)
    if len(prefix_ids)<3:raise ValueError('至少需要前三期作为历史上下文')
    if prefix_ids.min()<0 or prefix_ids.max()>=N:raise ValueError('历史号码超出范围')
    last=DIGITS[prefix_ids[-3:]].astype(np.int16)
    sums=last.sum(axis=1)
    D=DIGITS.astype(np.int16)
    result=[]
    for c in constraints:
        if c.kind=='step_large':mask=(np.abs(np.diff(D,axis=1))>=c.threshold).any(axis=1)
        elif c.kind=='route_zero_absent':mask=(D%3!=0).all(axis=1)
        elif c.kind=='parity_extreme':mask=((D%2).sum(axis=1)==0)|((D%2).sum(axis=1)==5)
        elif c.kind=='sum_tail_repeat':
            mask=(D.sum(axis=1)%10==int(sums[-1]%10)) if (sums[0]%10==sums[1]%10==sums[2]%10) else np.zeros(N,dtype=bool)
        elif c.kind=='sum_arithmetic':
            delta=int(sums[2]-sums[1]); next_sum=int(sums[2]+delta)
            mask=(D.sum(axis=1)==next_sum) if delta!=0 and sums[1]-sums[0]==delta and 0<=next_sum<=45 else np.zeros(N,dtype=bool)
        else: # position_repeat
            repeated=(last[0]==last[1])&(last[1]==last[2])
            mask=np.any(D[:,repeated]==last[2,repeated],axis=1) if repeated.any() else np.zeros(N,dtype=bool)
        result.append(mask)
    return np.asarray(result,dtype=np.bool_)


def group_redundancy(masks, specs, limit=.97):
    """Only exact/high-phi positive correlation; never treat independent evidence as a given."""
    out=[]
    for i,a in enumerate(masks):
        if not a.any() or a.all():continue
        for j in range(i):
            b=masks[j]
            if not b.any() or b.all():continue
            m=float(np.mean(a));n=float(np.mean(b));cross=float(np.mean(a&b))
            phi=(cross-m*n)/math.sqrt(max(1e-300,m*(1-m)*n*(1-n)))
            if phi>=limit:out.append({'id':specs[i].id,'against':specs[j].id,'phi':float(phi)})
    return out


def models_for(specs, redundant):
    ids=[c.id for c in specs if c.id not in {r['id'] for r in redundant}]
    ix={c.id:i for i,c in enumerate(specs)}
    # The prior is fixed BEFORE observing validation/holdout. Baselines take 80%.
    raw=[('uniform','uniform',{} ,0.75),('dirichlet','dirichlet',{},0.05)]
    levels=(-0.8,0.6,1.4)
    for base in ('uniform','dirichlet'):
        for label in ids:
            for lam in levels:
                raw.append((f'{base}:single:{label}:{lam:+g}',base,{ix[label]:lam},0.15/(max(1,len(ids))*len(levels)*2)))
    for i in range(len(ids)):
        for j in range(i+1,len(ids)):
            raw.append((f'pair:{ids[i]}+{ids[j]}','uniform',{ix[ids[i]]:0.6,ix[ids[j]]:0.6},
                        0.05/max(1,len(ids)*(len(ids)-1)//2)))
    if len(ids)<2:raw=[(a,b,c,d) for a,b,c,d in raw if not a.startswith('pair:')]
    priors=np.asarray([item[3] for item in raw],dtype=np.float64)
    priors/=priors.sum()
    return raw,priors


def positional_baseline(draws: np.ndarray, alpha:float=30.)->np.ndarray:
    """Frozen 5x10 positional Dirichlet mean learned ONLY from first WARMUP draws."""
    if not isinstance(alpha,(float,int)) or not 10<=alpha<=1000:raise ValueError('Dirichlet先验强度应为10—1000')
    p=np.ones(N,dtype=np.float64)
    for i in range(5):
        counts=np.bincount(DIGITS[draws,i],minlength=10)
        q=(counts+alpha/10)/(len(draws)+alpha)
        p*=q[DIGITS[:,i]]
    return p/p.sum()


def _energies(models, k):
    combos=np.arange(1<<k,dtype=np.int32)
    flags=((combos[:,None] >> np.arange(k)) & 1).astype(np.float64)
    weights=np.zeros((len(models),k),dtype=np.float64)
    for j,(_name,_base,w,_prior) in enumerate(models):
        for ix,weight in w.items():weights[j,ix]=weight
    energy=weights@flags.T
    # ensure numerical stability even with 8 constraints
    return energy,np.exp(-energy),flags


def _coding(masks):
    return np.sum(masks.astype(np.uint16)*(1<<np.arange(len(masks),dtype=np.uint16))[:,None],axis=0,dtype=np.uint16)


def _state(prefix, specs, model_bases, expenergy):
    masks=constraint_masks(prefix,specs)
    codes=_coding(masks)
    nbin=expenergy.shape[1]
    masses=np.stack([np.bincount(codes,weights=base,minlength=nbin) for base in model_bases],axis=0)
    return masks,codes,masses


def _denominators(masses, expenergy, base_indicator):
    # each model's base-normalizing Z = sum_x base(x)*exp(-penalty)
    return np.sum(masses[base_indicator]*expenergy,axis=1)


def _log_model_prob(actual, codes, energies, normalizers, bases, base_indicator):
    return np.log(np.maximum(bases[base_indicator,actual],1e-300))-energies[:,int(codes[actual])]-np.log(normalizers)


def _posterior(models,priors,ids,tr_end,specs,bases,expenergy,energies,base_indicator):
    logw=np.log(priors)
    curve=[]
    for t in range(WARMUP,tr_end):
        masks,codes,mass=_state(ids[:t],specs,bases,expenergy)
        z=_denominators(mass,expenergy,base_indicator)
        ll=_log_model_prob(int(ids[t]),codes,energies,z,bases,base_indicator)
        logw+=ll  # sequential conditional likelihood; all target dates processed once
        if (t-WARMUP+1)%25==0:curve.append({'seen':t+1,'null_mass':float(np.exp(logw[0]-np.logaddexp.reduce(logw)))})
    prob=np.exp(logw-np.logaddexp.reduce(logw))
    return prob,curve


def evaluate(ids,start,end,specs,posterior,bases,expenergy,energies,base_indicator):
    gains=[]
    for t in range(start,end):
        _masks,codes,mass=_state(ids[:t],specs,bases,expenergy)
        z=_denominators(mass,expenergy,base_indicator)
        ll=_log_model_prob(int(ids[t]),codes,energies,z,bases,base_indicator)
        # True model average at locked model weights, not averaging log scores
        p=float(np.dot(posterior,np.exp(ll)))
        gains.append(math.log(max(p,1e-300))+LOG_N)
    gains=np.asarray(gains,dtype=np.float64)
    gains[np.abs(gains)<1e-10]=0.
    n=len(gains)
    mean=float(gains.mean())
    se=float(gains.std(ddof=1)/np.sqrt(n)) if n>1 else 0.
    return {'periods':n,'mean_log_gain':mean,'mean_log_loss':LOG_N-mean,
            'mean_gain_se':se,'gain_95pct_normal_approx':[mean-1.96*se,mean+1.96*se],
            'first_half_gain':float(gains[:n//2].mean()),'second_half_gain':float(gains[n//2:].mean()),
            'positive_periods':int(np.count_nonzero(gains>0))}


def _weighted_quantile(vals,weights,q):
    idx=np.argsort(vals,kind='stable')
    return float(vals[idx[min(int(np.searchsorted(np.cumsum(weights[idx]),q,side='left')),len(idx)-1)]])


def _group_table(codes,masses,posterior,bases,energies,expenergy,bi):
    z=_denominators(masses,expenergy,bi)
    group_p=[]
    # Only 2^k possible violation signatures. No need to hold 100k x #models matrix.
    for pattern in range(expenergy.shape[1]):
        indexes=np.flatnonzero(codes==pattern)
        if not len(indexes):continue
        # q_m(x) includes the Dirichlet base's different per-number values;
        # group-only PMF is insufficient for full posterior credible intervals.
        group_p.append({'signature':int(pattern),'size':int(len(indexes)),
                        'posterior_penalty_mean':float(np.dot(posterior,energies[:,pattern])),
                        'penalty_95pct_credible_interval':[
                            _weighted_quantile(energies[:,pattern],posterior,.025),
                            _weighted_quantile(energies[:,pattern],posterior,.975)]})
    return z,group_p


def _candidate_rows(codes, bases, z, posterior, energies, expenergy, bi, specs, budget, seed, top_details=30):
    # Weighted BMA posterior predictive PMF over all 100,000 candidates.
    allp=np.zeros(N,dtype=np.float64)
    for j in range(len(posterior)):
        allp+=posterior[j]*bases[bi[j]]*expenergy[j,codes]/z[j]
    allp/=allp.sum()
    if not np.isfinite(allp).all() or not np.isclose(allp.sum(),1):raise RuntimeError('模型归一化失败')
    rng=np.random.default_rng(seed ^ 0x27BC5E)
    # Under identical scores, break ties with a precommitted seed, not an implicit "best" number.
    shuffle=rng.permutation(N)
    rank=shuffle[np.argsort(-allp[shuffle],kind="stable")]
    control=rng.choice(N,budget,replace=False)
    top=rank[:budget]
    rows=[]
    for n in rank[:top_details]:
        vals=bases[bi,n]*expenergy[:,int(codes[n])]/z
        penalties=energies[:,int(codes[n])]
        rows.append({'number':f'{int(n):05d}','model_probability_mean':float(allp[n]),
                    'model_probability_95pct_credible_interval':[_weighted_quantile(vals,posterior,.025),_weighted_quantile(vals,posterior,.975)],
                    'penalty_mean':float(np.dot(posterior,penalties)),
                    'penalty_95pct_credible_interval':[_weighted_quantile(penalties,posterior,.025),_weighted_quantile(penalties,posterior,.975)],
                    'posterior_mass_models_below_uniform':float(posterior[vals<1/N].sum()),
                    'violated_rules':[c.id for j,c in enumerate(specs) if int(codes[n])&(1<<j)]})
    return rank,allp,top,control,rows


def study(history,*,constraints=None,seed=20261102,test_periods=30,
          validation_periods=35,budget=100,dirichlet_alpha=30.,null_trials=0):
    ids=validate_history(history)
    specs=constraints_from_json(constraints)
    for name,val,lo,hi in (('seed',seed,0,2**32-1),('test_periods',test_periods,20,200),
                           ('validation_periods',validation_periods,20,200),('budget',budget,1,100),
                           ('null_trials',null_trials,0,4)):
        if type(val) is not int or not lo<=val<=hi:raise ValueError(f'{name}范围不合法')
    tr_end=len(ids)-test_periods-validation_periods
    if tr_end-WARMUP<40:raise ValueError('训练区间不足：需要初始60期+至少40期证据训练')
    warm=ids[:WARMUP]
    base_dir=positional_baseline(warm,dirichlet_alpha)
    bases=np.stack([np.full(N,1/N,dtype=np.float64),base_dir])
    initmask=constraint_masks(warm,specs)
    redund=group_redundancy(initmask,specs)
    models,priors=models_for(specs,redund)
    energies,ee,flags=_energies(models,len(specs))
    bi=np.fromiter((0 if m[1]=='uniform' else 1 for m in models),dtype=np.intp)
    post,curve=_posterior(models,priors,ids,tr_end,specs,bases,ee,energies,bi)
    validation=evaluate(ids,tr_end,tr_end+validation_periods,specs,post,bases,ee,energies,bi)
    # No holdout is read to make this decision. Balanced halves + prior null mass.
    activated=(validation['mean_log_gain']>0.01 and validation['first_half_gain']>0 and
               validation['second_half_gain']>0 and post[0]<.5)
    locked=post if activated else np.eye(1,len(models),0,dtype=np.float64)[0]
    holdout=evaluate(ids,tr_end+validation_periods,len(ids),specs,locked,bases,ee,energies,bi)
    masks,codes,masses=_state(ids,specs,bases,ee)
    z,groups=_group_table(codes,masses,locked,bases,energies,ee,bi)
    rank,p,top,control,rows=_candidate_rows(codes,bases,z,locked,energies,ee,bi,specs,budget,seed)
    # Bound the size: external caller may request a full 100k ranking separately.
    data={'version':'bcse-v27','status':'research_only','mode':'validated_model' if activated else 'uniform_fallback',
          'predictive_advantage':'UNVERIFIED','posterior_interpretation':'指定离散算法模型和固定先验条件下的后验；不是物理开奖概率的保证',
          'history_sha256':hashlib.sha256('\n'.join(history).encode()).hexdigest(),
          'constraints':[c.card() for c in specs],
          'redundant_constraints':redund,
          'prior_model_weights':{m[0]:float(v) for m,v in zip(models,priors)},
          'posterior_model_weights_training':{m[0]:float(v) for m,v in zip(models,post)},
          'gate':{'passed':bool(activated),'reason':'训练后验+独立验证两个半区均为正增益' if activated else '未满足开发验证门槛，回退均匀分布',
                  'posterior_uniform_mass':float(post[0]),'minimum_mean_log_gain':0.01},
          'splits':{'warmup':WARMUP,'evidence_training':tr_end-WARMUP,'validation':validation_periods,
                    'holdout':test_periods,'training_end_exclusive_index':tr_end,
                    'holdout_start_index':tr_end+validation_periods},
          'validation':validation,'holdout':holdout,'posterior_progress':curve,
          'next_draw_rule_flags': [{'id':c.id,'count':int(mask.sum()),'fraction':float(mask.mean())}
                                   for c,mask in zip(specs,masks)],
          'signature_groups':groups,
          'candidate_details':rows,
          'experimental_top_k':[f'{int(n):05d}' for n in top],
          'equal_budget_random_control':[f'{int(n):05d}' for n in control],
          'budget':budget,'fair_hit_probability':budget/N,
          'posterior_model_mass_top_k':float(p[top].sum()),
          'baseline_log_loss':LOG_N,'dirichlet_alpha':float(dirichlet_alpha),
          'ranking_tie_seed':int(seed),'prediction_warning':
            '公平独立开奖下固定或历史自适应的K注集合仍只有K/100000命中概率。模型违例不等于实际抽奖概率下降。',
          'independence_warning':'模型家族之间共享数据，不能将规则似然当独立概率相乘；本版对联合违反型精确归一化。',
          'test_reuse_warning':'历史最终留出已经被查看；更改模型或阈值后须用新未来期验证。'}
    if null_trials:
        rng=np.random.default_rng(seed^0xBC270)
        trial=[]
        for i in range(null_trials):
            fake=[f'{n:05d}' for n in rng.integers(N,size=len(history))]
            r=study(fake,constraints=[asdict(x) for x in specs],seed=(seed+i+1)%2**32,
                    test_periods=test_periods,validation_periods=validation_periods,
                    budget=budget,dirichlet_alpha=dirichlet_alpha,null_trials=0)
            trial.append({'activated':r['gate']['passed'],'holdout_gain':r['holdout']['mean_log_gain']})
        data['iid_null_simulations']=trial
    return data


def full_ranking(history, report, constraints=None):
    """Recompute exact next-draw BMA. Input hash prevents mismatch."""
    ids=validate_history(history)
    if report.get('version')!='bcse-v27' or report.get('history_sha256')!=hashlib.sha256('\n'.join(history).encode()).hexdigest():
        raise ValueError('历史与已封存研究报告不一致')
    specs=constraints_from_json(constraints)
    if [(c.id,c.kind,c.threshold) for c in specs] != [
        (x['id'],x['type'],x['parameters'].get('threshold',7)) for x in report['constraints']]:
        raise ValueError('约束配置不匹配')
    tr_end=report['splits']['training_end_exclusive_index']
    bases=np.stack([np.full(N,1/N),positional_baseline(ids[:WARMUP],report.get('dirichlet_alpha',30.))])
    models,prior=models_for(specs,report['redundant_constraints'])
    energy,ee,_=_energies(models,len(specs))
    bi=np.array([0 if m[1]=='uniform' else 1 for m in models],dtype=int)
    post=np.array([report['posterior_model_weights_training'][m[0]] for m in models])
    if report['mode']=='uniform_fallback':post=np.eye(1,len(models),0)[0]
    masks,codes,masses=_state(ids,specs,bases,ee)
    z=_denominators(masses,ee,bi)
    p=np.zeros(N)
    for j in range(len(models)):
        p+=post[j]*bases[bi[j]]*ee[j,codes]/z[j]
    p/=p.sum()
    permutation=np.random.default_rng(int(report['ranking_tie_seed'])^0x27BC5E).permutation(N)
    rank=permutation[np.argsort(-p[permutation],kind='stable')]
    return rank,p


def capabilities():return [c.card() for c in DEFAULT_CONSTRAINTS]


def full_diagnostics(history, report, constraints=None, batch_size=2048):
    """Optional complete 100k audit: per-number posterior and credible interval.

    Returns numeric arrays in original number order; CI is *model-conditional*,
    NOT a frequentist coverage guarantee. Uses batches to bound peak memory.
    """
    rank, p=full_ranking(history,report,constraints)
    ids=validate_history(history);specs=constraints_from_json(constraints)
    models,_=models_for(specs,report['redundant_constraints'])
    _,e,_=_energies(models,len(specs)); exp_e=np.exp(-e)
    bases=np.stack([np.full(N,1/N),positional_baseline(ids[:WARMUP],report['dirichlet_alpha'])])
    bi=np.asarray([0 if m[1]=='uniform' else 1 for m in models],dtype=np.intp)
    weights=np.asarray([report['posterior_model_weights_training'][m[0]] for m in models])
    if report['mode']=='uniform_fallback':weights=np.eye(1,len(models),0)[0]
    masks,codes,mass=_state(ids,specs,bases,exp_e)
    z=_denominators(mass,exp_e,bi)
    p_lo=np.zeros(N);p_hi=np.zeros(N); pen_mean=np.zeros(N)
    pen_lo=np.zeros(N);pen_hi=np.zeros(N); p_supp=np.zeros(N)
    for begin in range(0,N,batch_size):
        end=min(N,begin+batch_size)
        ix=np.arange(begin,end,dtype=np.intp)
        vals=bases[bi[:,None],ix]*exp_e[:,codes[ix]]/z[:,None]
        penalties=e[:,codes[ix]]
        pen_mean[ix]=weights@penalties
        p_supp[ix]=weights@(vals<1/N)
        for matrix,low,high in ((vals,p_lo,p_hi),(penalties,pen_lo,pen_hi)):
            idx=np.argsort(matrix,axis=0,kind='stable')
            cumulative=np.cumsum(weights[idx],axis=0)
            sorted_matrix=np.take_along_axis(matrix,idx,axis=0)
            cols=np.arange(len(ix))
            low[ix]=sorted_matrix[np.argmax(cumulative>=.025,axis=0),cols]
            high[ix]=sorted_matrix[np.argmax(cumulative>=.975,axis=0),cols]
    return rank,{'model_probability_mean':p,'model_probability_ci_low':p_lo,
        'model_probability_ci_high':p_hi,'penalty_mean':pen_mean,
        'penalty_ci_low':pen_lo,'penalty_ci_high':pen_hi,
        'posterior_mass_below_uniform':p_supp,'signature':codes}
