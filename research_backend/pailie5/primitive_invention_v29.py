"""V2.9: learned finite-domain binary primitives, not combinations of V2.8 AST operators.

A binary operation here is a frozen 10x10 table, discovered from TRAINING-only
position-pair statistics using two operator induction mechanisms.  This is a
bounded finite-algebra search, not an open-ended invention of mathematics.

Selection uses an exact likelihood-ratio e-value against the simple uniform
null, with a multiplicity budget for ALL attempted primitives and mixtures.
The final holdout is read only after selection. Evidence is research-only.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import itertools
import json
import math
import sqlite3
import numpy as np
from scipy.stats import beta

N = 100000
DIGITS = np.stack([np.arange(N, dtype=np.int32)//10**k%10 for k in (4,3,2,1,0)], axis=1).astype(np.uint8)
FAMILIES = ("spectral_bilinear", "local_diffusion")
MIXTURES = (0.25, 0.5, 1.0)


def history_array(numbers: list[str]) -> np.ndarray:
    if not isinstance(numbers, list) or not 190 <= len(numbers) <= 5000:
        raise ValueError("历史样本必须是190—5000期")
    if any(type(x) is not str or len(x) != 5 or not x.isascii() or not x.isdecimal() for x in numbers):
        raise ValueError("必须使用五位ASCII数字，保留前导零")
    return np.array([[ord(c)-48 for c in row] for row in numbers], dtype=np.uint8)


def _canonical_partition(a: np.ndarray) -> bytes:
    """Canonical label renaming by first encounter; values can be any integer."""
    seen = {}
    values = []
    for item in np.asarray(a).ravel():
        n = int(item)
        if n not in seen: seen[n] = len(seen)
        values.append(seen[n])
    return bytes(values)


def _baseline_partitions(k: int) -> set[bytes]:
    a, b = np.indices((10, 10))
    fn = [a, b, (a+b)%k, (a-b)%k, np.abs(a-b)%k, (a*b)%k,
          (a^b)%k, np.minimum(a,b)%k, np.maximum(a,b)%k,
          (a==b).astype(int), (a<b).astype(int), ((a+b)%2)]
    return {_canonical_partition(t) for t in fn}


def _quantize(score: np.ndarray, k: int) -> np.ndarray:
    if score.shape != (10,10) or not np.all(np.isfinite(score)):
        raise ValueError("算子诱导分数格式无效")
    order = np.argsort(score.ravel(), kind="stable")
    table = np.empty(100, dtype=np.uint8)
    table[order] = np.arange(100, dtype=np.int32)*k//100
    return table.reshape(10,10)


def _pair_counts(training: np.ndarray, p: int, q: int) -> np.ndarray:
    return np.bincount(training[:,p].astype(np.int32)*10+training[:,q], minlength=100).reshape(10,10).astype(float)


def induce_table(training: np.ndarray, positions: tuple[int,int], family: str, k: int) -> np.ndarray:
    if family not in FAMILIES or k not in (3,4): raise ValueError("未知基础算子搜索家族")
    p, q = positions
    if not (0 <= p < q <= 4): raise ValueError("位置必须严格递增且在0—4之间")
    if training.ndim!=2 or training.shape[1]!=5 or len(training)<50:
        raise ValueError("基础算子至少需要50期训练数据")
    counts = _pair_counts(training, p, q)
    # In the iid-uniform reference each of the 100 cells has probability 0.01.
    residual = (counts - len(training)/100.) / math.sqrt(len(training)/100.+4.)
    if family == "spectral_bilinear":
        u, s, vh = np.linalg.svd(residual, full_matrices=False)
        score = s[0]*np.outer(u[:,0],vh[0,:])
    else:
        # Diffuse a residual on the fixed digit grid.  This is a *learned*
        # operation table, not a fixed modular arithmetic rule.
        score = .5*residual + .125*(np.roll(residual,1,axis=0)+np.roll(residual,-1,axis=0)+
                                   np.roll(residual,1,axis=1)+np.roll(residual,-1,axis=1))
    return _quantize(score, k)


def _partition_stability(a: np.ndarray, b: np.ndarray) -> float:
    # Pairwise co-membership across all 100 input pairs; labels may be permuted.
    x = a.ravel(); y = b.ravel()
    aa = x[:,None]==x[None,:]; bb=y[:,None]==y[None,:]
    return float(np.mean(aa==bb))


@dataclass(frozen=True)
class Primitive:
    positions: tuple[int,int]
    family: str
    levels: int
    table: tuple[int,...]
    train_fingerprint: str
    stability: float

    def __post_init__(self):
        if not (isinstance(self.positions,tuple) and len(self.positions)==2 and 0<=self.positions[0]<self.positions[1]<=4):
            raise ValueError("位置范围无效")
        if self.family not in FAMILIES or self.levels not in (3,4): raise ValueError("家族或输出类型无效")
        if len(self.table)!=100 or any(type(v) is not int or not 0<=v<self.levels for v in self.table):
            raise ValueError("二元算子必须含100个已验证的真值表项")
        if len(set(self.table)) != self.levels: raise ValueError("算子输出类数不足")

    @property
    def table_array(self):return np.array(self.table,dtype=np.uint8).reshape(10,10)
    @property
    def identity(self):
        data={'positions':self.positions,'table':self.table}
        return 'pl5.primitive.'+hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()[:20]
    @property
    def table_sha256(self):return hashlib.sha256(bytes(self.table)).hexdigest()
    def call(self,a:int,b:int)->int:
        if type(a) is not int or type(b) is not int or not(0<=a<=9 and 0<=b<=9):raise ValueError('算子输入只能是数字0—9')
        return self.table[10*a+b]
    def vector(self, digits:np.ndarray = DIGITS)->np.ndarray:
        p,q=self.positions
        return self.table_array[digits[:,p],digits[:,q]]
    def full_crosscheck(self)->dict:
        fast=self.vector()
        for n in range(N):
            x=f'{n:05d}'
            if int(fast[n]) != self.call(int(x[self.positions[0]]),int(x[self.positions[1]])):
                raise ValueError(f'全域交叉核验失败: {x}')
        return {'checked':N,'status':'passed','sha256':hashlib.sha256(fast.tobytes()).hexdigest()}
    def properties(self)->dict:
        t=self.table_array
        return {'symmetric':bool(np.array_equal(t,t.T)),
                'occupied_output_classes':int(len(set(self.table))),
                'partition_entropy_bits':float(-sum(p*math.log2(p) for p in np.bincount(t.ravel(),minlength=self.levels)/100 if p)),
                'horizontal_transitions':int(np.count_nonzero(np.diff(t.astype(int),axis=1))),
                'vertical_transitions':int(np.count_nonzero(np.diff(t.astype(int),axis=0))),
                'partition_stability_train_halves':self.stability}
    def card(self)->dict:
        return {'uacp_version':'v1','id':self.identity,'version':'2.9.0',
                'kind':'learned_finite_binary_operation', 'family':self.family,
                'meaning':'f:{0,...,9}×{0,...,9}→{0,...,%d}; learned 100-cell truth table'%(self.levels-1),
                'positions':list(self.positions),'inputs':['integer_digit_0_to_9','integer_digit_0_to_9'],
                'output':f'categorical_digit_0_to_{self.levels-1}', 'table':list(self.table),
                'table_sha256':self.table_sha256,'train_fingerprint':self.train_fingerprint,
                'properties':self.properties(), 'dependencies':['training_only_pair_counts','numpy_svd_or_diffusion'],
                'execution':'frozen_safe_lookup_no_eval', 'status':'research_only',
                'escalation':'requires independent prospective evidence and human approval',
                'predictive_advantage':'unverified'}


def discover(training:np.ndarray, *, maximum:int=40)->tuple[list[Primitive],list[dict]]:
    if type(maximum) is not int or not 1<=maximum<=40:raise ValueError("每轮最多40个候选算子")
    if not isinstance(training,np.ndarray) or training.ndim!=2 or training.shape[1]!=5 or len(training)<120:
        raise ValueError("训练期不足120条")
    train_hash=hashlib.sha256(training.tobytes()).hexdigest()
    seen=set()
    baseline_by_k={k:_baseline_partitions(k) for k in (3,4)}
    result=[];rejected=[]
    # Enumerate a fixed, auditable family rather than cherry-picking seeds.
    for p,q in itertools.combinations(range(5),2):
        for family in FAMILIES:
            for k in (3,4):
                table=induce_table(training,(p,q),family,k)
                signature=(p,q,_canonical_partition(table))
                name=f'{p}{q}.{family}.{k}'
                if signature in seen or signature[2] in baseline_by_k[k]:
                    rejected.append({'candidate':name,'reason':'与固定基准或已发现的数字运算分区等价'})
                    continue
                early=induce_table(training[:max(50,len(training)//2)],(p,q),family,k)
                stability=_partition_stability(early,table)
                op=Primitive((p,q),family,k,tuple(int(v) for v in table.ravel()),train_hash,stability)
                result.append(op);seen.add(signature)
                if len(result)>=maximum:return result,rejected
    return result,rejected


def fit_primitive(operator:Primitive, training:np.ndarray, alpha:float=200.)->dict:
    if len(training)<100 or not 10<=alpha<=10000:raise ValueError('训练期或平滑强度错误')
    codes=operator.vector()
    base=np.bincount(codes,minlength=operator.levels).astype(float)/N
    observed=np.bincount(operator.vector(training),minlength=operator.levels).astype(float)
    posterior=(observed+alpha*base)/(len(training)+alpha)
    ratio=posterior/base
    return {'base':base,'counts':observed,'posterior':posterior,'ratio':ratio,'alpha':alpha,
            'training_periods':len(training)}


def bcse_research_clauses(operator:Primitive, fit:dict, mixture:float)->list[dict]:
    """At most four soft clauses, explicitly *not* authorized prediction rules.

    Credible intervals condition on a finite partition model and fixed prior.
    They do not measure uncertainty in operator selection or future true odds.
    """
    out=[]
    concentration=fit['training_periods']+fit['alpha']
    for code in range(operator.levels):
        a=float(fit['counts'][code]+fit['alpha']*fit['base'][code])
        b=concentration-a
        lo,hi=beta.ppf([0.025,0.975],a,b)
        out.append({'operator_id':operator.identity,'output_symbol':code,
                    'candidate_share':float(fit['base'][code]),
                    'train_occurrences':int(fit['counts'][code]),
                    'posterior_ratio':float(fit['ratio'][code]),
                    'signed_soft_penalty':float(-mixture*math.log(max(fit['ratio'][code],1e-15))),
                    'model_conditional_ratio_95pct_interval':
                        [float(lo/fit['base'][code]),float(hi/fit['base'][code])],
                    'mode':'research_only_not_authorized_for_esse'})
    return out


def score_evidence(operator:Primitive, fit:dict, validation:np.ndarray, mixture:float)->dict:
    if mixture not in MIXTURES:raise ValueError('无效的混合参数')
    code=operator.vector(validation)
    gains=np.log((1.-mixture)+mixture*fit['ratio'][code])
    log_e=float(np.sum(gains))
    return {'mixture':mixture,'periods':len(validation),'log_e_value':log_e,
            'mean_log_gain':float(gains.mean()),
            'first_half_gain':float(gains[:len(gains)//2].mean()),
            'second_half_gain':float(gains[len(gains)//2:].mean()),
            'mean_log_loss':math.log(N)-float(gains.mean())}


def pmf(operator:Primitive, fit:dict, mixture:float)->np.ndarray:
    # Partition covers the entire universe and is normalized exactly.
    p=(1.-mixture+mixture*fit['ratio'][operator.vector()])/N
    return p/p.sum()


def study(numbers:list[str],*,seed:int=20261102,maximum:int=40,validation_periods:int=60,
          holdout_periods:int=50,budget:int=100,alpha:float=0.01,registry=None)->dict:
    if type(seed) is not int or not 0<=seed<2**32 or not 1<=maximum<=40 or not 1<=budget<=100:
        raise ValueError('seed、候选数量或预算越界')
    if not 40<=validation_periods<=200 or not 30<=holdout_periods<=200 or not .0001<=alpha<=.05:
        raise ValueError('验证、封存期或证据阈值越界')
    data=history_array(numbers)
    train_end=len(data)-validation_periods-holdout_periods
    if train_end<120:raise ValueError('训练数据不足120期')
    train=data[:train_end];val=data[train_end:train_end+validation_periods];holdout=data[train_end+validation_periods:]
    primitives, duplicates=discover(train,maximum=maximum)
    evaluations=[]; fits=[]
    for op in primitives:
        fit=fit_primitive(op,train)
        fits.append(fit)
        for w in MIXTURES:
            evaluations.append({'operator_id':op.identity,'family':op.family,'positions':list(op.positions),
                'table_sha256':op.table_sha256, 'stability':op.stability,
                **score_evidence(op,fit,val,w)})
    # Familywise e-value union bound. Every hypothesis was fixed before validation.
    threshold=math.log(max(1,len(evaluations))/alpha)
    eligible=[r for r in evaluations if r['log_e_value']>=threshold
              and r['first_half_gain']>0 and r['second_half_gain']>0
              and r['stability']>=0.65]
    selected=max(eligible,key=lambda r:(r['log_e_value'],r['operator_id'])) if eligible else None
    if selected:
        index=next(i for i,op in enumerate(primitives) if op.identity==selected['operator_id'])
        op=primitives[index]; fit=fits[index]
        hold=score_evidence(op,fit,holdout,selected['mixture'])
        probabilities=pmf(op,fit,selected['mixture'])
        # No after-the-fact holdout gating.  Holdout only reports score.
        crosscheck=op.full_crosscheck()
        clauses=bcse_research_clauses(op,fit,selected['mixture'])
    else:
        hold={'periods':len(holdout),'mean_log_gain':0.,'mean_log_loss':math.log(N),
              'note':'开发验证未达到预注册证据门槛，封存段采用均匀基线'}
        probabilities=np.full(N,1./N,dtype=float)
        crosscheck=primitives[0].full_crosscheck() if primitives else None
        clauses=[]
    rng=np.random.default_rng(seed)
    ties=rng.random(N)
    order=np.lexsort((ties,-probabilities))
    control=np.random.default_rng(seed^0xBEE7).choice(N,budget,replace=False)
    report={'version':'pl5-v29-finite-primitive-invention','status':'research_only',
            'scope':'bounded autonomous finite-binary-operator induction, not unbounded mathematical discovery',
            'seed':seed,'data_source':'provided_by_caller_unverified',
            'history_sha256':hashlib.sha256('|'.join(numbers).encode()).hexdigest(),
            'splits':{'train_periods':train_end,'validation_periods':len(val),'holdout_periods':len(holdout)},
            'candidates_proposed':len(primitives)+len(duplicates),'new_unique_primitives':len(primitives),
            'duplicate_rejections':duplicates,'cards':[op.card() for op in primitives],
            'validation_experiments':evaluations,'tests_counted':len(evaluations),
            'null_hypothesis':'independent uniform next draw, conditioned on prior training data',
            'familywise_log_e_threshold':threshold,'alpha':alpha,
            'selected_operator':selected,'sealed_holdout':hold,
            'validation_gate':{'passed':bool(selected),'method':'terminal e-value with union-bound over all candidate-weight pairs; pre-fixed train/validation boundary',
                               'reason':'gate_passed_on_development_data' if selected else 'insufficient_evidence_uniform_abstention'},
            'independent_full_universe_crosscheck':crosscheck,
            'experimental_bcse_soft_clauses':clauses,
            'experimental_top_k':[f'{int(x):05d}' for x in order[:budget]],
            'equal_budget_random_control':[f'{int(x):05d}' for x in control],
            'model_probability_sum':float(probabilities.sum()),
            'fair_uniform_hit_chance':budget/N,
            'report_limitations':['后验模型分配不是已校准中奖概率','有限抽样即使出现规律不意味着未来偏差',
                                  '既往留出数据被看过后不可重复称为独立测试','查表算子是受约束的基础运算发明，不等于发明新数学公理'],
            'promotion':'research_only_no_automatic_esse_admission'}
    if registry is not None:register(report,registry)
    return report


def register(report:dict, dbfile:str|Path)->int:
    path=Path(dbfile);path.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS v29_primitives(id TEXT PRIMARY KEY, card_json TEXT NOT NULL, status TEXT NOT NULL CHECK(status="research_only"), created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
        db.execute('CREATE TABLE IF NOT EXISTS v29_experiments(run_sha256 TEXT PRIMARY KEY, result_json TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
        inserted=0
        for card in report['cards']:
            row=db.execute('INSERT OR IGNORE INTO v29_primitives(id,card_json,status) VALUES(?, ?, "research_only")',
                           (card['id'],json.dumps(card,sort_keys=True,ensure_ascii=False)))
            inserted+=row.rowcount
        payload=json.dumps(report,sort_keys=True,ensure_ascii=False,allow_nan=False)
        digest=hashlib.sha256(payload.encode()).hexdigest()
        db.execute('INSERT OR IGNORE INTO v29_experiments(run_sha256,result_json) VALUES(?,?)',(digest,payload))
    return inserted


def register_aan_primitives(report:dict, registry_path:str|Path)->int:
    """Explicitly publish *research-only* frozen primitive capabilities to AAN.

    This is an input primitive for workflows; it is NOT an ESSE approval.
    """
    from .capability_network import Capability, CapabilityRegistry
    registry=CapabilityRegistry(registry_path)
    try:
        added=0
        for card in report['cards']:
            cap=Capability(id=card['id']+'.'+card['train_fingerprint'][:12],name='有限域自主发明：'+card['family'],version='1.0.0',
                op='metric',requires=(),origin='V2.9训练数据诱导；'+card['train_fingerprint'][:20],
                params={'metric':'learned_primitive','positions':card['positions'],
                        'levels':card['properties']['occupied_output_classes'],'table':card['table'],
                        'train_count':report['splits']['train_periods'],
                        'train_fingerprint':card['train_fingerprint']},
                status='research',evidence='unverified',limitations='训练生成的有限运算表；不能宣称中奖预测优势')
            if registry.add(cap):added+=1
        return added
    finally:
        registry.close()
