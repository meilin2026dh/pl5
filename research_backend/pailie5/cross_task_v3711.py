"""V3.7.11 research-only train-to-train mathematical primitive transfer.

Source tasks are independently validated before creating a frozen grammar bank.
Both trial arms evaluate the *same number of full-table candidate features*,
but CPU time and upstream source-training cost are NOT compute matched.
A budget-limited model is identified within the probed hypothesis set only.
Results are synthetic and cannot establish real lottery predictive advantage.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from math import comb
import json
import numpy as np

from .generated_primitives_v3710 import (
    GeneratorConfig, _all_specs, _feature, _rectangles,
    fit_counterexample_primitive, evaluate_generated,
)
from .latent_primitives_v377 import fit_additive_primitive
from .structure_search_v372 import CellDataset


def _digest(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                             allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class TransferConfig:
    max_features: int = 8

    def __post_init__(self):
        if type(self.max_features) is not int or not 1 <= self.max_features <= len(_all_specs()):
            raise ValueError('max_features must be a plain integer within full candidate grammar')


@dataclass(frozen=True)
class FrozenPrimitiveBank:
    specs: tuple[tuple[str, str, str], ...]
    source_training_sha256: tuple[str, ...]
    source_holdout_sha256: tuple[str, ...]
    source_operator_ids: tuple[str, ...]

    @property
    def identity(self):
        return _digest(('pl5-v3711-bank-1', self.specs, self.source_training_sha256,
                        self.source_holdout_sha256, self.source_operator_ids))

    def to_dict(self):
        return {'schema':'pl5-v3711-frozen-bank-1','bank_id':self.identity,
                'specs':self.specs,'source_training_sha256':self.source_training_sha256,
                'source_holdout_sha256':self.source_holdout_sha256,
                'source_operator_ids':self.source_operator_ids,
                'source_certification':'independent source holdout, zero errors',
                'production_enabled':False,'real_lottery_advantage_established':False}


def certify_transfer_bank(source_tasks: tuple[tuple[CellDataset, CellDataset], ...]) -> FrozenPrimitiveBank:
    if not isinstance(source_tasks,tuple) or not 1 <= len(source_tasks) <= 30:
        raise ValueError('expected 1..30 source train/holdout pairs')
    specs=[]; training_fps=[]; holdout_fps=[]; ids=[]
    for task in source_tasks:
        if not isinstance(task,tuple) or len(task)!=2 or not all(isinstance(x,CellDataset) for x in task):
            raise ValueError('source tasks must contain CellDataset training and holdout')
        training, held = task
        if set(training.pairs) & set(held.pairs):
            raise ValueError('source validation overlap')
        if training.fingerprint in training_fps:
            raise ValueError('duplicate source task')
        frozen=fit_counterexample_primitive(training,GeneratorConfig())
        if (frozen.status!='identified' or frozen.spec is None or
                evaluate_generated(frozen,held)['errors']!=0):
            raise ValueError('source validation failed: absent or inaccurate identified primitive')
        if frozen.spec not in specs:
            specs.append(frozen.spec)
        training_fps.append(training.fingerprint)
        holdout_fps.append(held.fingerprint)
        ids.append(frozen.identity)
    return FrozenPrimitiveBank(tuple(specs),tuple(training_fps),tuple(holdout_fps),tuple(ids))


@dataclass(frozen=True)
class FrozenBudgetedPrimitive:
    status: str
    completion: tuple[int, ...] | None
    selected_spec: tuple[str,str,str] | None
    source_pairs: tuple[tuple[int,int],...]
    source_sha256: str
    bank_id: str | None
    features_checked: int
    matches: int
    reason: str

    @property
    def identity(self):
        return _digest(('pl5-v3711-budgeted-1',self.status,self.completion,
                        self.selected_spec,self.source_sha256,self.bank_id,
                        self.features_checked,self.matches))

    def predict(self,a:int,b:int)->int | None:
        if type(a) is not int or type(b) is not int or not 0<=a<=9 or not 0<=b<=9:
            raise ValueError('digits must be integers 0..9')
        if self.status!='provisional_identified': return None
        return self.completion[a*10+b]

    def to_dict(self):
        return {'schema':'pl5-v3711-budgeted-1','operator_id':self.identity,
                'status':self.status,'spec':self.selected_spec,
                'source_sha256':self.source_sha256,'source_pairs':self.source_pairs,
                'bank_id':self.bank_id,'features_checked':self.features_checked,
                'matching_parameterizations':self.matches,'reason':self.reason,
                'scope':'searched candidate subset only',
                'training_only':True,'production_enabled':False,
                'real_lottery_advantage_established':False,
                'compute_matched':'candidate full-table feature evaluations only; source cost excluded'}


def fit_budgeted_transfer(training: CellDataset, bank: FrozenPrimitiveBank | None=None,
                          config: TransferConfig=TransferConfig()) -> FrozenBudgetedPrimitive:
    if not isinstance(training,CellDataset) or (bank is not None and not isinstance(bank,FrozenPrimitiveBank)) or not isinstance(config,TransferConfig):
        raise ValueError('invalid training/bank/config')
    if bank is not None and training.fingerprint in bank.source_training_sha256:
        raise ValueError('target training may not be reused as source')
    grammar=_all_specs()
    order=(tuple(bank.specs)+tuple(spec for spec in grammar if spec not in bank.specs)
           if bank is not None else grammar)
    candidate_specs=order[:config.max_features]
    rects=_rectangles(training)
    target=np.array([r[4] for r in rects],dtype=np.int64)
    matches=[]
    incomplete=False
    if rects:
        for spec in candidate_specs:
            raw=_feature(spec)
            phi=np.array([(raw[a0,b0]+raw[a1,b1]-raw[a0,b1]-raw[a1,b0])%10
                          for a0,a1,b0,b1,_ in rects],dtype=np.int64)
            for k in range(1,10):
                if np.any((k*phi-target)%10):
                    continue
                adjusted=CellDataset(tuple((a,b,(y-k*int(raw[a,b]))%10)
                                           for a,b,y in training.rows))
                fit=fit_additive_primitive(adjusted)
                if fit.status=='unidentifiable':
                    incomplete=True
                elif fit.status=='identified':
                    completion=tuple((fit.u[a]+fit.v[b]+k*int(raw[a,b]))%10
                                     for a in range(10) for b in range(10))
                    matches.append((spec,completion))
    distinct={m[1] for m in matches}
    if incomplete or len(distinct)>1:
        status='unidentifiable'; reason='compatible models have multiple possible unobserved completions'
        chosen=None; spec=None
    elif len(distinct)==1:
        status='provisional_identified'; reason='unique completion among budgeted searched hypotheses only'
        spec,chosen=matches[0]
    else:
        status='no_fit'; reason='no compatible model in the budgeted searched candidate subset'
        chosen=None;spec=None
    return FrozenBudgetedPrimitive(status,chosen,spec,training.pairs,training.fingerprint,
                                   None if bank is None else bank.identity,
                                   len(candidate_specs),len(matches),reason)


def evaluate_provisional(frozen:FrozenBudgetedPrimitive, held:CellDataset)->dict:
    if not isinstance(frozen,FrozenBudgetedPrimitive) or not isinstance(held,CellDataset):
        raise ValueError('expected frozen fit and heldout dataset')
    if set(frozen.source_pairs) & set(held.pairs):
        raise ValueError('train/holdout overlap')
    if frozen.status!='provisional_identified':
        raise ValueError('cannot evaluate abstaining fit')
    errors=sum(frozen.predict(a,b)!=y for a,b,y in held.rows)
    return {'operator_id':frozen.identity,'held_sha256':held.fingerprint,
            'count':len(held.rows),'errors':errors,'accuracy':1-errors/len(held.rows),
            'refit':False,'production_enabled':False}


def diagnose_training_noise(training:CellDataset, bank:FrozenPrimitiveBank,
                            config:TransferConfig=TransferConfig())->dict:
    """Leave-one-label-out *diagnosis* only; no prediction authorization."""
    if not isinstance(training,CellDataset) or not isinstance(bank,FrozenPrimitiveBank):
        raise ValueError('invalid train or bank')
    if len(training.rows)<22:
        raise ValueError('noise diagnostic needs at least 22 observations')
    corrections=set()
    for idx,(a,b,y) in enumerate(training.rows):
        subset=CellDataset(training.rows[:idx]+training.rows[idx+1:])
        candidate=fit_budgeted_transfer(subset,bank,config)
        if candidate.status!='provisional_identified':
            continue
        predicted=candidate.predict(a,b)
        if predicted != y:
            if sum(candidate.predict(ra,rb)!=ry for ra,rb,ry in training.rows)==1:
                corrections.add(((a,b),y,predicted))
    if len(corrections)==1:
        (a,b),observed,suggested=next(iter(corrections))
        status='single_label_suspected'
    elif len(corrections)>1:
        (a,b),observed,suggested=(-1,-1),None,None
        status='ambiguous_anomalies'
    else:
        (a,b),observed,suggested=(-1,-1),None,None
        status='no_unique_single_label_explanation'
    return {'schema':'pl5-v3711-training-noise-diagnosis-1',
            'status':status,'suspect_pair':(a,b) if status=='single_label_suspected' else None,
            'observed_digit':observed,'suggested_digit':suggested,
            'candidate_corrections':len(corrections),
            'source_sha256':training.fingerprint,'bank_id':bank.identity,
            'evidence_scope':'train-only leave-one-out, not proof of label corruption',
            'production_enabled':False,'auto_corrected':False}


def detect_labeled_shift(frozen:FrozenBudgetedPrimitive, observed:CellDataset,
                         *,expected_error_rate:float=0.02,alpha:float=0.001)->dict:
    """One fixed size-20 labeled post-fit window; binomial iid-null heuristic.

    The caller is responsible for true chronology: the function cannot verify
    that observed labels are later than the fit. No sequential optional peeking.
    """
    if not isinstance(frozen,FrozenBudgetedPrimitive) or not isinstance(observed,CellDataset):
        raise ValueError('invalid frozen model or observed labeled dataset')
    if frozen.status!='provisional_identified':
        raise ValueError('cannot monitor abstaining fit')
    if len(observed.rows)!=20:
        raise ValueError('exactly 20 labeled observations required for prespecified window')
    if (type(expected_error_rate) not in (int,float) or not 0 < expected_error_rate < 1 or
            type(alpha) not in (int,float) or not 0 < alpha < 1):
        raise ValueError('expected 0 < error rate, alpha < 1')
    errors=sum(frozen.predict(a,b)!=y for a,b,y in observed.rows)
    p=float(sum(comb(20,k)*expected_error_rate**k*(1-expected_error_rate)**(20-k)
                for k in range(errors,21)))
    return {'schema':'pl5-v3711-fixed-window-shift-1',
            'status':'shift_suspected' if p <= alpha else 'no_shift_signal',
            'observed_errors':errors,'window_size':20,'iid_noise_rate_null':expected_error_rate,
            'p_value':p,'alpha':alpha,'observed_sha256':observed.fingerprint,
            'frozen_operator_id':frozen.identity,
            'labels_arrived_after_training':True,
            'fit_was_refreshed':False,'production_enabled':False,
            'assumptions':'caller-provided chronological provenance; fixed single look; iid null'}
