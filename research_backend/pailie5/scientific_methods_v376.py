"""V3.7.6: bounded design of competing scientific experimental *methods*.

All method classes are preapproved interventions on the existing safe AST
searcher. This module cannot execute generated code or claim discovery.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy

from .autonomous_v374 import STRUCTURED_CASES

METHODS = ('more_training', 'richer_grammar', 'more_search')
METHOD_REASON = {
    'more_training': (
        'Does reducing observational ambiguity improve generalization?',
        'A fresh controlled task shows no improvement from more training cells.'),
    'richer_grammar': (
        'Does increased mathematical expression capacity improve generalization?',
        'A richer admissible tree grammar fails to improve on a fresh task.'),
    'more_search': (
        'Does extra search effort resolve representable-but-missed expressions?',
        'A doubled candidate budget fails to improve on a fresh task.'),
    'balanced_sampling': (
        'Could more informative input-coordinate coverage help without more labels?',
        'A different train-only coordinate allocation fails on a fresh held-out split.'),
    'cross_family_replication': (
        'Does a different mathematical family respond to a change in proposal guidance?',
        'An unguided search provides no consistent gain on an unrelated structured family.'),
}


def propose_study(registry: dict, history: list[dict], study_number: int,
                  seed: int, budget: int, control_every: int = 4) -> dict:
    """Pick a new *intervention* based on the unresolved question/evidence.

    Previous studies may guide what to explore next, but each new evaluation
    uses a different seeded truth table and never reuses test labels.
    """
    if (not isinstance(registry, dict) or not isinstance(registry.get('questions'), list)
        or not isinstance(history, list)
        or type(study_number) is not int or not 1 <= study_number <= 10000
        or type(seed) is not int or not 0 <= seed < 2**32
        or type(budget) is not int or not 100 <= budget <= 10000
        or type(control_every) is not int or not 2 <= control_every <= 20):
        raise ValueError('invalid finite scientific experiment design')
    if len(history) != study_number-1:
        raise ValueError('study history must be contiguous and complete')
    candidates = [x for x in registry['questions'] if x.get('status') == 'needs_new_method']
    if not candidates:
        candidates = [x for x in registry['questions'] if x.get('status') in ('open', 'investigating')]
    if not candidates:
        raise ValueError('no unresolved scientific question available')
    candidates.sort(key=lambda q: (-float(q.get('planning_priority', 0)), str(q['id'])))
    question = candidates[0]
    observations = [x for x in question.get('evidence', ()) if x.get('case') in STRUCTURED_CASES]
    case = observations[-1]['case'] if observations else 'difference_squares'
    mandatory = study_number % control_every == 0
    substantive=[x for x in history if not x.get('mandatory_null_control')]
    if (not mandatory and
        sum(x.get('method')=='cross_family_replication' for x in substantive)>=2 and
        all(float(x.get('holdout_delta',0))<=0 for x in substantive)):
        raise ValueError('bounded method library exhausted; new mathematical primitive or search hypothesis required')
    filtered=[x for x in history if not x.get('mandatory_null_control')]
    tried = Counter(x.get('method') for x in filtered)
    exhausted=(all(tried[m]>0 and max(float(x.get('holdout_delta',0)) for x in filtered
                  if x.get('method')==m)<=0 for m in METHODS))
    if mandatory:
        # Use the same method-selection policy but not the previous data.
        method = min(METHODS, key=lambda m: (tried[m], METHODS.index(m)))
        case = 'iid_a' if (study_number//control_every) % 2 else 'iid_b'
    elif exhausted and tried['balanced_sampling']==0:
        # Synthesize an alternate method by modifying the sampling policy,
        # rather than re-running the three exhausted interventions.
        method='balanced_sampling'
    elif exhausted and tried['balanced_sampling']>0 and tried['cross_family_replication']<2:
        # A different target family and one policy switch, chosen without
        # reading its unseen labels. Avoid claiming independence across
        # repeated splits of one fixed synthetic table.
        method='cross_family_replication'
        prior=({x.get('case') for x in question.get('evidence',())} |
               {x.get('case') for x in filtered if x.get('method')=='cross_family_replication'})
        case=next((c for c in STRUCTURED_CASES if c not in prior and c!=case),
                  next(c for c in STRUCTURED_CASES if c!=case))
    else:
        # Try untested method classes first. Only after coverage use observed
        # exploratory effects to direct the next experiment (never a p-value).
        method = min(METHODS, key=lambda m: (tried[m],
                     -sum(float(x.get('holdout_delta', 0)) for x in history
                          if x.get('method') == m) / max(1, tried[m]),
                     METHODS.index(m)))
    baseline = {'train_cells':60, 'holdout_cells':20,
                'evaluation_budget':budget, 'max_nodes':11}
    challenger = deepcopy(baseline)
    if method == 'more_training': challenger['train_cells'] = 80
    if method == 'richer_grammar': challenger['max_nodes'] = 13
    if method == 'more_search': challenger['evaluation_budget'] = budget*2
    if method == 'balanced_sampling':
        baseline['sampling']='chronological_random'
        challenger['sampling']='balanced'
    if method == 'cross_family_replication':
        baseline['guided']=True
        challenger['guided']=False
    max_cost = sum(x['evaluation_budget'] for x in (baseline,challenger))
    if max_cost > 30000:
        raise ValueError('bounded evaluation cost exceeded')
    rationale, falsifier = METHOD_REASON[method]
    return {
        'schema':'pl5-v376-method-proposal-1', 'study_number':study_number,
        'seed':(seed + study_number*1009) % 2**32,
        'case':case, 'question_id':'Q-periodic_null_control' if mandatory else question['id'],
        'method':method, 'scientific_rationale':rationale,
        'source_failure':('three_prior_method_classes_not_improving'
                          if method=='balanced_sampling' else
                          'exhausted_training_capacity_and_sampling_methods'
                          if method=='cross_family_replication' else None),
        'falsification_criterion':falsifier,
        'baseline':baseline, 'challenger':challenger,
        'cost_budget_by_arm':{'baseline':budget,
                              'challenger':challenger['evaluation_budget']},
        'common_holdout_pairs':20,
        'mandatory_null_control':mandatory,
        'test_labels_hidden_from_fit':True,
        'method_selection':'adaptive_exploratory_not_confirmatory',
        'confirmatory_pvalue_permitted':False,
        'scientific_conclusion':'UNRESOLVED',
        'production_enabled':False,
    }
