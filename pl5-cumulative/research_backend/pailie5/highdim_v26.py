"""PL5 V2.6: high-dimensional structure research on a *finite* 10^5 alphabet.

Three explicit lifts: sparse tensor interactions (up to order 3), conditioned
history states (up to two lags), and low-order Z_10^5 Fourier characters.
Only bounded NumPy code executes. Historical validation is chronological; final
holdout is *not* used to choose the model or its mixing weight.

A lift of previous draws cannot predict a future independent uniform draw.
All outputs are research PMFs/experimental candidates, not calibrated odds.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from itertools import combinations
import hashlib
import json
import math

import numpy as np
from .engine import DIGITS

N = 100_000
LOG_NULL = math.log(N)
LAMBDAS = (0.0, 0.10, 0.25, 0.50, 1.0)


def history_ids(history: list[str]) -> np.ndarray:
    if not isinstance(history, (list, tuple)) or not 120 <= len(history) <= 12000:
        raise ValueError('历史样本须为120—12000期，按时间从早到晚排列')
    if any(not isinstance(n, str) or len(n) != 5 or not n.isascii() or not n.isdecimal() for n in history):
        raise ValueError('号码须为保留前导零的五位ASCII数字')
    return np.fromiter((int(v) for v in history), dtype=np.int32, count=len(history))


def _pmf_from_energy(energy: np.ndarray) -> np.ndarray:
    energy = np.asarray(energy, dtype=np.float64)
    if energy.shape != (N,) or not np.all(np.isfinite(energy)):
        raise ValueError('模型未产生有限的10万注评分')
    z = np.exp(np.clip(energy - np.max(energy), -700, 0))
    z /= z.sum()
    if not np.all(np.isfinite(z)):
        raise ValueError('概率正规化失败')
    return z


@dataclass(frozen=True)
class LiftSpec:
    family: str
    order: int = 2
    harmonics: int = 8
    alpha: float = 100.0

    def __post_init__(self):
        if self.family not in ('tensor', 'temporal', 'spectral'):
            raise ValueError('不支持的高维表示族')
        if type(self.order) is not int or self.order not in (1, 2, 3):
            raise ValueError('order必须为1/2/3')
        if self.family == 'temporal' and self.order not in (1, 2):
            raise ValueError('时序滞后仅支持1或2')
        if type(self.harmonics) is not int or not 1 <= self.harmonics <= 32:
            raise ValueError('harmonics必须为1—32')
        if type(self.alpha) not in (float, int) or not 5 <= self.alpha <= 2000:
            raise ValueError('alpha必须在5—2000')
        if self.family != 'spectral' and self.harmonics != 8:
            raise ValueError('非谱模型的harmonics必须使用标准值8，避免伪参数创新')
        if self.family == 'spectral' and self.alpha != 100:
            raise ValueError('谱模型未使用Dirichlet先验，alpha应固定100，避免伪创新')

    @property
    def id(self) -> str:
        s=json.dumps(asdict(self),sort_keys=True,separators=(',',':'))
        return 'pl5.hdse.'+hashlib.sha256(s.encode()).hexdigest()[:16]

    def capability(self) -> dict:
        d=asdict(self)
        dim=(sum(math.comb(5,k)*10**k for k in range(1,self.order+1))
             if self.family=='tensor' else
             5*(sum(10**k for k in range(1,self.order+2)))
             if self.family=='temporal' else
             sum(math.comb(5,k)*9**k for k in range(1,self.order+1)))
        return {'id':self.id,'version':'2.6.0','kind':'high_dimensional_research_distribution',
                'spec':d,'declared_feature_coordinates':dim,
                'inputs':['five_digit_history_before_cutoff','five_digit_candidates'],
                'outputs':['normalized_pmf[100000]','prequential_loss','research_report'],
                'requires':['pl5.canonical_universe','pl5.official_history_snapshot'],
                'assumptions':['chronological observations','chosen smoothing prior',
                               'finite discrete domain'],
                'status':'experimental','prediction_advantage':'unverified',
                'notes':'坐标数不是独立预测信息；自动归一化也不等于真实校准。'}


def proposals(seed: int = 20261102, maximum: int = 7) -> list[LiftSpec]:
    if type(seed) is not int or not 0 <= seed < 2**32 or type(maximum) is not int or not 1 <= maximum <= 12:
        raise ValueError('seed为32位整数、maximum为1—12')
    rng = np.random.default_rng(seed)
    # New cycles explore genuinely distinct parameterized implementations.
    pool = ([LiftSpec('tensor',order,8,alpha) for order in (1,2,3)
             for alpha in (25,100,250,500,1000)] +
            [LiftSpec('temporal',order,8,alpha) for order in (1,2)
             for alpha in (25,100,350,800)] +
            [LiftSpec('spectral',order,k,100) for order in (1,2,3)
             for k in (2,4,8,12,16,24,32)])
    mandatory=[LiftSpec('tensor',3,8,250),LiftSpec('temporal',2,8,350),
               LiftSpec('spectral',3,12,100)]
    chosen=mandatory[:maximum]
    chosen_ids={item.id for item in chosen}
    for ix in rng.permutation(len(pool)):
        item=pool[int(ix)]
        if item.id in chosen_ids:continue
        chosen.append(item)
        chosen_ids.add(item.id)
        if len(chosen)>=maximum:break
    return chosen


class TensorLift:
    def __init__(self, spec: LiftSpec, train: np.ndarray):
        tr=DIGITS[train].astype(np.int32)
        energy=np.zeros(N, dtype=np.float64)
        # Features are sparse categorical interactions: never allocate 100k x 11050.
        for order in range(1,spec.order+1):
            terms=list(combinations(range(5),order))
            part=np.zeros(N, dtype=np.float64)
            power=(10**np.arange(order-1,-1,-1,dtype=np.int32))
            bins=10**order
            for pos in terms:
                key=tr[:,pos] @ power
                counts=np.bincount(key,minlength=bins)
                empirical=(counts+spec.alpha/bins)/(len(train)+spec.alpha)
                candidate_key=DIGITS[:,pos].astype(np.int32) @ power
                part += np.log(np.maximum(empirical[candidate_key]*bins,1e-300))
            energy += (part/len(terms)) / spec.order
        self.pmf=_pmf_from_energy(energy)

    def values(self, digits: np.ndarray, prev1=None, prev2=None):
        return self.pmf[digits]
    def all_values(self, prev1=None, prev2=None):
        return self.pmf


class TemporalLift:
    def __init__(self,spec: LiftSpec,train:np.ndarray):
        d=DIGITS[train].astype(np.int32)
        self.spec=spec
        self.marginal=np.zeros((5,10),dtype=np.float64)
        self.lag1=np.zeros((5,10,10),dtype=np.float64)
        self.lag2=np.zeros((5,10,10,10),dtype=np.float64)
        for p in range(5):
            self.marginal[p]=np.bincount(d[2:,p],minlength=10)
            np.add.at(self.lag1[p],(d[1:-1,p],d[2:,p]),1)
            np.add.at(self.lag2[p],(d[:-2,p],d[1:-1,p],d[2:,p]),1)

    def _conditional(self, p: int,prev1: int,prev2: int) -> np.ndarray:
        a=self.spec.alpha
        counts0=self.marginal[p]
        p0=(counts0+a/10)/(counts0.sum()+a)
        count1=self.lag1[p,prev1]
        p1=(count1+a*p0)/(count1.sum()+a)
        if self.spec.order==1:return p1
        count2=self.lag2[p,prev2,prev1]
        return (count2+a*p1)/(count2.sum()+a)

    def all_values(self, prev1=None,prev2=None):
        if prev1 is None or prev2 is None:raise ValueError('时序模型需要两个已知的上一期开奖结果')
        a=DIGITS[prev1];b=DIGITS[prev2]
        pmf=np.ones(N,dtype=np.float64)
        for p in range(5):
            pmf *= self._conditional(p,int(a[p]),int(b[p]))[DIGITS[:,p]]
        return pmf

    def values(self, digits: np.ndarray,prev1=None,prev2=None):
        if prev1 is None or prev2 is None:raise ValueError('缺少时序上下文')
        d=DIGITS[digits]
        a=DIGITS[prev1];b=DIGITS[prev2]
        pmf=np.ones(len(digits),dtype=np.float64)
        for p in range(5):
            pmf *= self._conditional(p,int(a[p]),int(b[p]))[d[:,p]]
        return pmf


class SpectralLift:
    def __init__(self,spec: LiftSpec, train:np.ndarray):
        histogram=np.bincount(train,minlength=N).reshape((10,)*5)/len(train)
        fft=np.fft.fftn(histogram)
        coords=np.indices((10,)*5).reshape((5,-1)).T
        order=np.count_nonzero(coords,axis=1)
        permitted=(order>=1)&(order<=spec.order)
        # Conjugate pairs are one real feature each.
        reverse=(-coords)%10
        canonical=np.all(coords==reverse,axis=1)
        for p in range(5):
            mask=(coords[:,p]!=reverse[:,p]) & np.all(coords[:,:p]==reverse[:,:p],axis=1)
            canonical |= mask & (coords[:,p]<reverse[:,p])
        indices=np.flatnonzero(permitted & canonical)
        coeff=fft.reshape(-1)[indices]
        best=np.argsort(-np.abs(coeff),kind='stable')[:spec.harmonics]
        self.freq=coords[indices[best]].astype(np.int16)
        self.coeff=coeff[best]
        # FFT coefficients are obtained only from training; selected peaks can be noise.
        angles=2*math.pi*((DIGITS.astype(np.int32)@self.freq.T)%10)/10
        energy=2*np.real((np.exp(1j*angles)*self.coeff).sum(axis=1))
        self.pmf=_pmf_from_energy(energy)
        self.peaks=[{'frequency':v.tolist(),'amplitude':float(abs(c))}
                    for v,c in zip(self.freq,self.coeff)]

    def values(self,digits:np.ndarray,prev1=None,prev2=None):return self.pmf[digits]
    def all_values(self,prev1=None,prev2=None):return self.pmf


def fit(spec:LiftSpec,train:np.ndarray):
    if len(train)<60:raise ValueError('训练样本不足60期')
    if spec.family=='tensor':return TensorLift(spec,train)
    if spec.family=='temporal':return TemporalLift(spec,train)
    return SpectralLift(spec,train)


def eval_rows(model,history:np.ndarray,start:int,end:int,lam:float)->dict:
    if start<2 or end<=start:raise ValueError('无效的时间评估区间')
    if not 0<=lam<=1:raise ValueError('混合系数错误')
    actual=history[start:end]
    if isinstance(model,TemporalLift):
        probs=np.asarray([model.values(history[t:t+1],int(history[t-1]),int(history[t-2]))[0]
                          for t in range(start,end)],dtype=np.float64)
    else:
        probs=model.values(actual)
    mixture=(1-lam)/N+lam*probs
    loss=-np.log(np.maximum(mixture,1e-300))
    gains=LOG_NULL-loss
    return {'periods':len(actual),'mean_log_loss':float(loss.mean()),
            'mean_log_gain':float(gains.mean()),
            'mean_gain_se':float(gains.std(ddof=1)/np.sqrt(len(gains))) if len(gains)>1 else 0.,
            'gain_95pct_normal_approx':[float(gains.mean()-1.96*gains.std(ddof=1)/np.sqrt(len(gains))),
                                         float(gains.mean()+1.96*gains.std(ddof=1)/np.sqrt(len(gains)))] if len(gains)>1 else [None,None]}


def _splits(n:int,test_periods:int):
    if type(test_periods) is not int or not 20<=test_periods<=200 or n-test_periods<100:
        raise ValueError('需要20—200期封存留出，且此前不少于100期')
    dev=n-test_periods
    val=max(30,dev//5)
    if dev-val<60:raise ValueError('训练历史不足')
    return dev-val,dev


def study(history:list[str],*,seed:int=20261102,maximum:int=7,
          test_periods:int=30, budget:int=100, null_trials:int=0)->dict:
    """Frozen chronological selection and once-only historical holdout evaluation.

    Calling this repeatedly on the same holdout does NOT create new validation evidence.
    """
    ids=history_ids(history)
    if type(budget) is not int or not 1<=budget<=100:raise ValueError('预算必须为1—100注')
    if type(null_trials) is not int or not 0<=null_trials<=10:raise ValueError('随机对照次数0—10')
    tr_end,val_end=_splits(len(ids),test_periods)
    tested=[]
    for spec in proposals(seed,maximum):
        model=fit(spec,ids[:tr_end])
        val=[(lam,eval_rows(model,ids,tr_end,val_end,lam)['mean_log_gain']) for lam in LAMBDAS]
        chosen=max(val,key=lambda pair:(pair[1],-pair[0]))
        tested.append({'spec':spec,'lambda':chosen[0],'validation_gain':chosen[1],
                       'validation_curve':[[float(a),float(b)] for a,b in val]})
    # A uniform baseline is always a possible action.
    winner=max(tested,key=lambda r:(r['validation_gain'],-r['lambda']))
    null_better=winner['validation_gain']<=1e-12 or winner['lambda']==0.
    selected_spec=None if null_better else winner['spec']
    chosen_lambda=0. if null_better else winner['lambda']
    if selected_spec is None:
        holdout={'periods':test_periods,'mean_log_loss':LOG_NULL,'mean_log_gain':0.,
                 'mean_gain_se':0.,'gain_95pct_normal_approx':[0.,0.]}
        nominal=np.full(N,1/N)
    else:
        frozen=fit(selected_spec,ids[:tr_end])
        holdout=eval_rows(frozen,ids,val_end,len(ids),chosen_lambda)
        # After evaluation, refit on all *published* history for next-draw research
        # prediction without using the test outcomes to pick the method or lambda.
        final=fit(selected_spec,ids)
        nominal=(1-chosen_lambda)/N+chosen_lambda*final.all_values(int(ids[-1]),int(ids[-2]))
        nominal=nominal/nominal.sum()
    random=np.random.default_rng(seed ^ 0x72A51)
    if selected_spec is None:
        ranked=random.permutation(N)[:budget]
    else:
        ranked=np.lexsort((np.arange(N),-nominal))[:budget]
    control=random.choice(N,budget,replace=False)
    report={'version':'hdse-v26','status':'research_only','source':'caller_supplied_history',
            'history_sha256':hashlib.sha256('\n'.join(history).encode()).hexdigest(),
            'experiment_sha256':hashlib.sha256(json.dumps({'history':history,'seed':seed,'maximum':maximum,
             'test_periods':test_periods,'budget':budget,'null_trials':null_trials},sort_keys=True).encode()).hexdigest(),
            'splits':{'training':tr_end,'validation':val_end-tr_end,'holdout':test_periods,
                      'training_last_index':tr_end-1,'validation_last_index':val_end-1},
            'hypotheses':[{'spec':asdict(r['spec']),'capability_id':r['spec'].id,
                           'chosen_lambda':r['lambda'],'validation_gain':r['validation_gain'],
                           'validation_curve':r['validation_curve']} for r in tested],
            'selected':None if selected_spec is None else selected_spec.capability(),
            'uniform_fallback':bool(selected_spec is None),'lambda':float(chosen_lambda),
            'holdout':holdout,'train_only_structure':None if selected_spec is None else structural_diagnostics(history[:tr_end],selected_spec),
            'baseline_log_loss':LOG_NULL,
            'sample_size':len(ids),'budget':budget,
            'experimental_top_k':[f'{int(n):05d}' for n in ranked],
            'equal_budget_random_control':[f'{int(n):05d}' for n in control],
            'fair_probability_exact':budget/N,'candidate_model_probability_sum':float(nominal[ranked].sum()),
            'warning':'高维坐标不产生新预测信息；历史留出不可重复调参。'
                      '模型概率仅为研究性假设，100注的公平覆盖率严格为0.1%（预算为100时）。'}
    if null_trials:
        trials=[]
        for i in range(null_trials):
            # Re-run the whole search on independent simulated IID histories.
            null_history=[f'{int(n):05d}' for n in random.integers(N,size=len(ids))]
            sim=study(null_history,seed=(seed+i+17)%(2**32),maximum=maximum,
                      test_periods=test_periods,budget=budget,null_trials=0)
            trials.append({'uniform_fallback':sim['uniform_fallback'],
                           'holdout_gain':sim['holdout']['mean_log_gain']})
        report['null_controls']={'simulations':null_trials,'full_selection_repeated':True,
                                 'positive_validation_selections':sum(not t['uniform_fallback'] for t in trials),
                                 'holdout_gain': [x['holdout_gain'] for x in trials],
                                 'warning':'蒙特卡洛仅作为算法误报压力测试，不能保证预测有效。'}
    return report



def structural_diagnostics(history: list[str],spec: LiftSpec) -> dict:
    """Train-only descriptive structure; no predictive claims."""
    ids=np.asarray([int(n) for n in history],dtype=np.int32)  # prefix already validated by study()
    digits=DIGITS[ids].astype(np.int32)
    pairs=[]
    for a,b in combinations(range(5),2):
        tab=np.bincount(10*digits[:,a]+digits[:,b],minlength=100).reshape(10,10)/len(ids)
        residual=tab-np.outer(tab.sum(axis=1),tab.sum(axis=0))
        singular=np.linalg.svd(residual,compute_uv=False)
        pairs.append({'positions':[a,b], 'top_singular_value':float(singular[0]),
                      'frobenius_residual':float(np.linalg.norm(residual))})
    pairs.sort(key=lambda v:-v['frobenius_residual'])
    info={'train_periods':len(ids),'largest_pair_residuals':pairs[:3],
          'interpretation':'有限样本频率残差；不等同未来可预测性或显著性。',
          'feature_coordinates':spec.capability()['declared_feature_coordinates'],
          'training_to_dimension_ratio':len(ids)/spec.capability()['declared_feature_coordinates']}
    if spec.family=='spectral':
        m=fit(spec,ids)
        info['selected_fourier_peaks']=m.peaks
        info['selection_bias_warning']='从大量频率中挑最高峰，随机数据也会出现噪声峰。'
    elif spec.family=='temporal':
        info['transition_samples']=max(0,len(ids)-2)
        info['sparsity_warning']='五位×1000个二滞后上下文单元通常远多于开奖样本；必须平滑。'
    return info



def full_ranking(history: list[str], report: dict) -> tuple[np.ndarray,np.ndarray]:
    """Recompute all 100k scores after the preselected model/weight are frozen.

    An exploratory ranking; not validated winning probabilities.
    """
    ids=history_ids(history)
    if (report.get('version')!='hdse-v26' or report.get('sample_size')!=len(ids) or
        report.get('history_sha256')!=hashlib.sha256('\n'.join(history).encode()).hexdigest()):
        raise ValueError('报告与历史样本不匹配')
    if report.get('uniform_fallback'):
        # The generated research shortlist goes first, followed by the remaining full universe.
        leading=[int(x) for x in report.get('experimental_top_k',[])]
        others=np.arange(N,dtype=np.int32)
        prefix=np.zeros(N,dtype=bool);prefix[leading]=True
        rest=others[~prefix]
        return np.asarray(leading+rest.tolist(),dtype=np.int32),np.full(N,1/N)
    selected=report['selected']
    spec=LiftSpec(**selected['spec'])
    lam=float(report['lambda'])
    m=fit(spec,ids)
    pmf=(1-lam)/N+lam*m.all_values(int(ids[-1]),int(ids[-2]))
    pmf/=pmf.sum()
    ranked=np.lexsort((np.arange(N),-pmf))
    return ranked,pmf


def capabilities()->list[dict]:
    return [LiftSpec('tensor',1).capability(),LiftSpec('tensor',2).capability(),
            LiftSpec('tensor',3).capability(),LiftSpec('temporal',1).capability(),
            LiftSpec('temporal',2).capability(),LiftSpec('spectral',2).capability(),
            LiftSpec('spectral',3).capability()]
