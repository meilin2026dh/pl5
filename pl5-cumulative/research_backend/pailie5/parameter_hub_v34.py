"""V3.4 governed parameter hub with *real* finite training adapters.

Training/evidence are separate: no lottery edge is asserted, no rule is
activated in the production filter. All chronology is fixed by indices.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib, json, math, sqlite3
from pathlib import Path
import numpy as np
from .engine import DIGITS
from .autolift_v28 import Lift, validate_expr

VERSION='v34-parameter-hub-1'
N=100_000

@dataclass(frozen=True)
class Parameter:
    component:str
    name:str
    domain:str
    optimizer:str
    state:str
    evidence:str
    def to_dict(self):return asdict(self)

# Honest inventory. 'learned_legacy' is documented behavior in that module;
# 'trained_v34' has a callable, tested adapter in this module.
DEFINITIONS=(
    Parameter('V2.4 temporal','window','int 2..16','none','search_only','TemporalSpec window is user-set, not auto-fit'),
    Parameter('V2.4 temporal','period','int 2..8','none','search_only','TemporalSpec period is user-set, not auto-fit'),
    Parameter('V2.7 BCSE','step_large.threshold','int 1..9','regularized_beta_grid','trained_v34','fit_step_constraint'),
    Parameter('V2.7 BCSE','model posterior weights','finite model catalogue','Bayesian update','learned_legacy','bcse_v27.models_for'),
    Parameter('V2.8 lift','mod_first','int 2..11','chronological_grid','trained_v34','fit_lift_moduli'),
    Parameter('V2.8 lift','mod_second','int 2..11','chronological_grid','trained_v34','fit_lift_moduli'),
    Parameter('V2.8 lift','expression AST','bounded tree','random proposal','search_only','autolift_v28.invent'),
    Parameter('V2.9 primitive','10x10 table cells','100 integer outputs','SVD/relational smoothing','learned_legacy','primitive_invention_v29'),
    Parameter('V3.0 symbolic','formula AST','bounded syntax','symbolic search','learned_legacy','symbolic_operators_v30'),
    Parameter('V3.1 categories','algebraic type','3 predefined categories','exact discovery','learned_legacy','primitive_categories_v31'),
    Parameter('V3.2 hypotheses','class / orbit / exceptions','bounded categories','category induction','learned_legacy','category_hypotheses_v32'),
    Parameter('V3.3 affine','u,v,orbit','u/v 1..9; table 10xk','enumeration + majority','learned_legacy','operator_metalearning_v33'),
    Parameter('V3.3 piecewise','direction,classes,orbits','<=3 row classes','clustered categorical fit','learned_legacy','operator_metalearning_v33'),
    Parameter('V3.3 sparse','exceptions','<=6 points','residual repair','learned_legacy','operator_metalearning_v33'),
    Parameter('V3.3 tree','splits,leaves','depth<=3','greedy supervised tree','learned_legacy','operator_metalearning_v33'),
    Parameter('V3.3 linear','coefficients','four real coefficients','linear program + calibration','learned_legacy','operator_metalearning_v33'),
    Parameter('V3.4 transfer','exception locations / outputs','<=6 points','certified warm start','trained_v34','transfer_evolution_v34'),
)

def inventory():
    return {'version':VERSION,'parameters':[p.to_dict() for p in DEFINITIONS],
            'counts':{s:sum(p.state==s for p in DEFINITIONS) for s in
                      ('trained_v34','learned_legacy','search_only','fixed')},
            'claim':'NOT ALL historical parameters are learnable; registry is an inventory, not a completion claim'}

def _history(draws,min_length=180):
    if not isinstance(draws,(tuple,list,np.ndarray)) or not min_length<=len(draws)<=10000:
        raise ValueError(f'需要{min_length}..10000期历史')
    if any(type(x) not in (int,np.int32,np.int64) or not 0<=int(x)<N for x in draws):
        raise ValueError('输入必须是0..99999的整数，严格按时间顺序排列')
    return np.asarray(draws,dtype=np.int32)

def _splits(n):
    # Chronological train/dev/test, at least 90/45/45 for n>=180.
    a=int(n*0.55);b=int(n*0.8)
    if a<90 or b-a<35 or n-b<35:raise ValueError('数据不足以建立训练/验证/封存测试三段')
    return a,b

def _gain_stats(gains):
    if len(gains)==0:raise ValueError('空验证区间')
    x=np.asarray(gains,dtype=np.float64)
    return {'count':len(x),'mean_nats':float(x.mean()),'sum_nats':float(x.sum()),
            'standard_error_nats':float(x.std(ddof=1)/np.sqrt(len(x))) if len(x)>1 else 0.}

def fit_step_constraint(draws,*,alpha=150.0):
    """Learn threshold from TRAIN only, model gate DEV, sealed TEST once.

    Probability family: p_lam(x) ∝ uniform(x)*exp(-lam*V(x)).
    The Beta posterior estimates Bernoulli event frequency with a prior
    centered at its exact uniform frequency, and translates that q into lam.
    """
    ids=_history(draws);a,b=_splits(len(ids))
    if not isinstance(alpha,(int,float)) or type(alpha) is bool or not math.isfinite(alpha) or alpha<30 or alpha>10000:raise ValueError('alpha out of bounds')
    records=[]
    for threshold in range(1,10):
        flags=(np.abs(np.diff(DIGITS.astype(np.int16),axis=1))>=threshold).any(axis=1)
        p0=float(flags.mean())
        observed=flags[ids[:a]]
        q=(float(observed.sum())+alpha*p0)/(len(observed)+alpha)
        # clamp only for numeric safety, not to fabricate evidence
        q=float(np.clip(q,1e-10,1-1e-10));p0=float(np.clip(p0,1e-10,1-1e-10))
        lam=math.log(p0/(1-p0))-math.log(q/(1-q))
        z=(1-p0)+p0*math.exp(-lam)
        gains=-lam*flags[ids[:b]]-math.log(z)
        # Selection on TRAIN only, complexity penalty favors null.
        tr=_gain_stats(gains[:a]);dev=_gain_stats(gains[a:b])
        records.append({'threshold':threshold,'weight':lam,'uniform_mask_fraction':p0,
                        'training':tr,'dev':dev})
    # Train evidence ranking, not validation ranking.
    best=max(records,key=lambda r:(r['training']['sum_nats']-math.log(len(ids))*.5,-abs(r['weight']),-r['threshold']))
    # One-sided conservative gate, DEV is not tuned after selection.
    gate=(best['dev']['mean_nats']>0 and best['dev']['mean_nats']>
          2.5*best['dev']['standard_error_nats'])
    # Evaluate the chosen model on sealed future only AFTER training and gate.
    flags=(np.abs(np.diff(DIGITS.astype(np.int16),axis=1))>=best['threshold']).any(axis=1)
    p0=best['uniform_mask_fraction'];lam=best['weight']
    z=(1-p0)+p0*math.exp(-lam)
    test=_gain_stats(-lam*flags[ids[b:]]-math.log(z))
    return {'version':VERSION,'method':'beta_shrunk_bernoulli_soft_constraint','selected_threshold':best['threshold'],
            'learned_weight':best['weight'],'gate':'research_pass' if gate else 'uniform_fallback',
            'active_weight':best['weight'] if gate else 0.,
            'dev':best['dev'],'sealed_test_research_only':test,
            'threshold_candidates':records,'split':{'train':[0,a],'dev':[a,b],'sealed_test':[b,len(ids)]},
            'predictive_advantage':'NOT_ESTABLISHED',
            'limitations':'Gate is not formal familywise proof; test must not inform model selection'}

def _expr_without_lag(tree):
    validate_expr(tree)
    if tree['op']=='lag':return False
    if tree['op'] in ('digit','sum','step'):return True
    return _expr_without_lag(tree['left']) and _expr_without_lag(tree['right'])

def fit_lift_moduli(draws, first, second, *, alpha=200., mod_min=2, mod_max=11):
    """Fit V2.8 moduli on fixed *non-temporal* AST expressions.

    Train: smoothed multinomial over one-hot cells, divided by EXACT domain
    bucket size to yield a proper probability over all 100000 candidate numbers.
    DEV selects moduli; sealed TEST is evaluated once without retuning.
    """
    ids=_history(draws);a,b=_splits(len(ids))
    if not (_expr_without_lag(first) and _expr_without_lag(second)):
        raise ValueError('动态lag表达式当前不可训练：逐期上下文变化会破坏静态概率表')
    if (type(mod_min) is not int or type(mod_max) is not int or
        not 2<=mod_min<=mod_max<=11):raise ValueError('模参数范围应为2..11')
    if not isinstance(alpha,(int,float)) or type(alpha) is bool or not math.isfinite(alpha) or not 20<=alpha<=10000:
        raise ValueError('alpha范围错误')
    records=[]
    for m in range(mod_min,mod_max+1):
        for n in range(mod_min,mod_max+1):
            spec=Lift(first,second,m,n)
            codes=spec.codes(np.empty(0,dtype=np.int32))
            bucket=np.bincount(codes,minlength=m*n)
            seen=np.bincount(codes[ids[:a]],minlength=m*n)
            # Dirichlet prior centered on true uniform bucket masses.
            q=(seen+alpha*bucket/N)/(a+alpha)
            assigned=q[codes[ids[a:b]]] /bucket[codes[ids[a:b]]]
            gain=np.log(assigned*N)
            dev=_gain_stats(gain)
            records.append({'mod_first':m,'mod_second':n,'feature_bins':m*n,'dev':dev})
    best=max(records,key=lambda r:(r['dev']['sum_nats']-2.*math.log(len(records)),
                                   -r['feature_bins'],-r['mod_first'],-r['mod_second']))
    # Because multiple moduli were evaluated on DEV, require a larger penalty.
    gate=(best['dev']['mean_nats']>0 and best['dev']['mean_nats']>
          3.8*best['dev']['standard_error_nats'] and
          best['dev']['sum_nats']>2*math.log(len(records)))
    # Select and gate on DEV only. No other candidate reads sealed TEST.
    mm,nn=best['mod_first'],best['mod_second']
    chosen_codes=Lift(first,second,mm,nn).codes(np.empty(0,dtype=np.int32))
    bucket=np.bincount(chosen_codes,minlength=mm*nn)
    seen=np.bincount(chosen_codes[ids[:a]],minlength=mm*nn)
    q=(seen+alpha*bucket/N)/(a+alpha)
    test=_gain_stats(np.log(N*q[chosen_codes[ids[b:]]] / bucket[chosen_codes[ids[b:]]]))
    return {'version':VERSION,'method':'dirichlet_lift_moduli_grid','status':'research_pass' if gate else 'uniform_fallback',
            'selected':{'mod_first':best['mod_first'],'mod_second':best['mod_second']},
            'active':{'mod_first':best['mod_first'],'mod_second':best['mod_second']} if gate else None,
            'selected_dev':best['dev'],'sealed_test_research_only':test,'trials':records,
            'split':{'train':[0,a],'dev':[a,b],'sealed_test':[b,len(ids)]},
            'predictive_advantage':'NOT_ESTABLISHED','limitations':'DEV reuses 100 choices; conservative gate is heuristic, not a significance proof'}

class ParameterAudit:
    """Append-only run audit with a digest; never silently promote predictions."""
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS param_runs_v34 (run_id TEXT PRIMARY KEY,kind TEXT NOT NULL,record TEXT NOT NULL,sha256 TEXT NOT NULL)')
    def register(self,kind,result):
        if kind not in ('fit_step','fit_lift','transfer','inventory'):raise ValueError('unknown research kind')
        value=json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
        digest=hashlib.sha256((kind+':'+value).encode()).hexdigest()
        ident='pl5.v34.'+digest[:24]
        with sqlite3.connect(self.path) as db:
            old=db.execute('SELECT kind,record,sha256 FROM param_runs_v34 WHERE run_id=?',(ident,)).fetchone()
            if old is not None:
                if old!=(kind,value,digest):raise ValueError('research audit hash collision or tampering')
                return ident,False
            db.execute('INSERT INTO param_runs_v34 VALUES (?,?,?,?)',(ident,kind,value,digest))
        return ident,True
    def read(self,ident):
        with sqlite3.connect(self.path) as db:
            row=db.execute('SELECT kind,record,sha256 FROM param_runs_v34 WHERE run_id=?',(ident,)).fetchone()
        if row is None:raise KeyError(ident)
        kind,value,digest=row
        if hashlib.sha256((kind+':'+value).encode()).hexdigest()!=digest or 'pl5.v34.'+digest[:24]!=ident:
            raise ValueError('audit record altered')
        return {'run_id':ident,'kind':kind,'data':json.loads(value),'sha256':digest}
    def summary(self):
        with sqlite3.connect(self.path) as db:ids=[r[0] for r in db.execute('SELECT run_id FROM param_runs_v34 ORDER BY run_id')]
        return [self.read(x) for x in ids]
