"""V3.7.12: bounded source-informed *unary-template* transfer.

Research only. A template transformation is chosen by the experiment author,
not autonomously invented. No target holdout labels enter model selection.
Cost accounting covers feature-table slots, not all solver CPU operations.
"""
from __future__ import annotations

from .cross_task_v3711 import (
    FrozenPrimitiveBank, FrozenBudgetedPrimitive, TransferConfig,
    evaluate_provisional, fit_budgeted_transfer,
)
from .generated_primitives_v3710 import (
    GeneratorConfig, _all_specs, _feature, _rectangles, fit_counterexample_primitive,
)
from .latent_primitives_v377 import fit_additive_primitive
from .structure_search_v372 import CellDataset
import numpy as np


class TemplateConfig:
    """Fixed maximum target-side candidate-table budget, not a runtime budget."""
    def __init__(self, max_features: int = 16):
        if type(max_features) is not int or not 1 <= max_features <= len(_all_specs()):
            raise ValueError('max_features must be an integer within full grammar')
        self.max_features=max_features


def source_template_candidates(bank: FrozenPrimitiveBank,
                               config: TemplateConfig=TemplateConfig()) -> tuple:
    """Predefined source-based unary swaps and one left-unary lift.

    Source certifications certify only original specs; derived proposals are
    *not* certified or promoted prior to target training checks.
    """
    if not isinstance(bank,FrozenPrimitiveBank) or not isinstance(config,TemplateConfig):
        raise ValueError('invalid certified source bank/config')
    grammar=set(_all_specs())
    ordered=[]
    def include(spec):
        if spec in grammar and spec not in ordered:
            ordered.append(spec)
    for spec in bank.specs:include(spec)
    for ua,op,ub in bank.specs:include((ub,op,ua))
    # The transformation is deliberately simple, human specified and bounded.
    for ua,op,ub in bank.specs:
        replacement='square' if ua in ('inc','twice_inc') else 'inc'
        include((replacement,op,ub))
    for spec in _all_specs():include(spec)
    return tuple(ordered[:config.max_features])


def _fit_fixed_subset(training:CellDataset, specs:tuple, bank_id:str|None) -> FrozenBudgetedPrimitive:
    rects=_rectangles(training)
    target=np.array([r[4] for r in rects],dtype=np.int64)
    matches=[];incomplete=False
    if rects:
        for spec in specs:
            raw=_feature(spec)
            phi=np.array([(raw[a0,b0]+raw[a1,b1]-raw[a0,b1]-raw[a1,b0])%10
                          for a0,a1,b0,b1,_ in rects],dtype=np.int64)
            for k in range(1,10):
                if np.any((k*phi-target)%10):
                    continue
                adjusted=CellDataset(tuple((a,b,(y-k*int(raw[a,b]))%10)
                                           for a,b,y in training.rows))
                fitted=fit_additive_primitive(adjusted)
                if fitted.status=='unidentifiable':
                    incomplete=True
                elif fitted.status=='identified':
                    completion=tuple((fitted.u[a]+fitted.v[b]+k*int(raw[a,b]))%10
                                     for a in range(10) for b in range(10))
                    matches.append((spec,completion))
    distinct={row[1] for row in matches}
    if incomplete or len(distinct)>1:
        status='unidentifiable'; reason='budgeted train-consistent candidate completions disagree or are incomplete'
        chosen=None;selected=None
    elif len(distinct)==1:
        status='provisional_identified'; reason='unique among a limited proposed template subset only'
        selected,chosen=matches[0]
    else:
        status='no_fit'; reason='no compatible model in fixed training-only subset'
        chosen=None;selected=None
    return FrozenBudgetedPrimitive(status,chosen,selected,training.pairs,training.fingerprint,
                                   bank_id,len(specs),len(matches),reason)


def fit_template_transfer(training:CellDataset, bank:FrozenPrimitiveBank,
                          config:TemplateConfig=TemplateConfig()) -> FrozenBudgetedPrimitive:
    if not isinstance(training,CellDataset) or not isinstance(bank,FrozenPrimitiveBank) or not isinstance(config,TemplateConfig):
        raise ValueError('expected training, certified bank and template config')
    if training.fingerprint in bank.source_training_sha256:
        raise ValueError('target training cannot reuse source training')
    return _fit_fixed_subset(training,source_template_candidates(bank,config),bank.identity)


def evaluate_template_pair(training:CellDataset,held:CellDataset,
                           bank:FrozenPrimitiveBank,config:TemplateConfig=TemplateConfig())->dict:
    if not isinstance(held,CellDataset) or not isinstance(training,CellDataset):
        raise ValueError('train and holdout must be CellDataset')
    if set(training.pairs)&set(held.pairs):
        raise ValueError('train and holdout overlap')
    source=fit_template_transfer(training,bank,config)
    base=fit_budgeted_transfer(training,None,TransferConfig(config.max_features))
    def summary(model):
        result=evaluate_provisional(model,held) if model.status=='provisional_identified' else None
        return {'status':model.status,'feature_slots':model.features_checked,
                'operator_id':model.identity,'spec':model.selected_spec,
                'heldout_errors':None if result is None else result['errors'],
                'heldout_count':len(held.rows),'heldout_accuracy':None if result is None else result['accuracy']}
    return {'schema':'pl5-v3712-matched-target-feature-slots-1',
            'source_informed':summary(source),'canonical':summary(base),
            'bank_id':bank.identity,'train_sha256':training.fingerprint,
            'heldout_sha256':held.fingerprint,'target_feature_slots_each':config.max_features,
            'source_bank_training_cost_excluded_from_target_comparison':True,
            'full_pipeline_compute_matched':False,
            'fit_used_target_holdout_labels':False,'production_enabled':False,
            'real_lottery_advantage_established':False}


def source_acquisition_ledger(bank:FrozenPrimitiveBank,
                              source_tasks:tuple[tuple[CellDataset,CellDataset],...])->dict:
    """Recompute source work. Feature tables only; prior search and solver cost omitted."""
    if not isinstance(bank,FrozenPrimitiveBank) or not isinstance(source_tasks,tuple) or len(source_tasks)!=len(bank.source_training_sha256):
        raise ValueError('sources must match the frozen source-bank certification')
    seen=[];total=0;proposals=0
    for i,task in enumerate(source_tasks):
        if not isinstance(task,tuple) or len(task)!=2 or not all(isinstance(v,CellDataset) for v in task):
            raise ValueError('invalid source tasks')
        train,held=task
        if train.fingerprint!=bank.source_training_sha256[i] or held.fingerprint!=bank.source_holdout_sha256[i]:
            raise ValueError('sources differ from frozen bank')
        fitted=fit_counterexample_primitive(train,GeneratorConfig())
        if fitted.status!='identified' or fitted.identity !=bank.source_operator_ids[i]:
            raise ValueError('source certificate mismatch')
        total+=fitted.distinct_features;proposals+=fitted.proposals
        seen.append({'train_sha256':train.fingerprint,'holdout_sha256':held.fingerprint,
                     'distinct_features_checked':fitted.distinct_features,
                     'coefficient_proposals':fitted.proposals,
                     'source_status':fitted.status})
    return {'schema':'pl5-v3712-source-acquisition-ledger-1','source_count':len(seen),
            'source_bank_id':bank.identity,'source_feature_tables_examined':total,
            'source_coefficient_proposals':proposals,'source_tasks':seen,
            'includes_legacy_source_fit_cost':False,
            'includes_source_holdout_evaluation_cost':False,
            'includes_target_additive_solver_cost':False,
            'pipeline_compute_matched':False}
