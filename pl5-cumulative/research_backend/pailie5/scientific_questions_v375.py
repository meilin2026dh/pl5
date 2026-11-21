"""PL5 V3.7.5: auditable scientific question registry and experimental planning.

All evidence is exploratory synthetic math; priorities are planning heuristics,
not statistical probabilities or claims of a discovered theorem.
"""
from __future__ import annotations
from pathlib import Path
import json

from .autonomous_v374 import STRUCTURED_CASES, choose_next_task

# These are candidate explanations to be tested, not inferred root causes.
QUESTIONS = {
    'weak_structured_generalization': {
        'question': 'Why do formulas fitted to a structured table fail on unseen input pairs?',
        'observation': 'A structured target has weak held-out reconstruction accuracy.',
        'priority_base': 7.0,
        'hypotheses': (
            ('structural_capacity', 'The bounded expression grammar lacks a compact representation.',
             'A larger grammar with the same train/test split fails to improve on a fresh task.',
             'Replicate the problematic structured task under a fresh seed and compare full with grammar-only.'),
            ('search_instability', 'The search misses a representable formula because of finite budget.',
             'Repeated independent equal-budget searches show no improvement or variability.',
             'Replicate under a new split/seed and compare full search to grammar-only.'),
            ('sample_ambiguity', 'Training cells underdetermine the target expression.',
             'New independent training/held-out splits do not change the ambiguity or gap.',
             'Repeat on a fresh train/held-out split without reusing old held-out labels.'),
        ),
    },
    'generalization_gap': {
        'question': 'What causes a large training-to-held-out mismatch?',
        'observation': 'The reported training accuracy exceeds held-out accuracy by >20 percentage points.',
        'priority_base': 5.0,
        'hypotheses': (
            ('overfit', 'The large hypothesis search overfits training cells.',
             'Independent held-out tests consistently match training accuracy.',
             'Repeat with a fresh split and fixed candidate budget.'),
            ('sampling', 'The training split is unrepresentative of the full table.',
             'Repeated independent splits produce the same gap regardless of sample composition.',
             'Use a distinct fresh split/seed on the same structured family.'),
            ('null_fit', 'The target has no learnable structure and the gap is accidental fitting.',
             'Independent null controls yield persistent held-out accuracy above chance.',
             'Re-run an independent random negative control and compare against 10% baseline.'),
        ),
    },
    'random_data_spurious_fit': {
        'question': 'Can the search reliably reject spurious patterns in independent random data?',
        'observation': 'Null-control training appears fitted but held-out accuracy remains near chance.',
        'priority_base': 3.0,
        'hypotheses': (
            ('multiple_testing', 'Searching many formulas creates apparently strong random fits.',
             'Chance-calibrated null simulations repeatedly show no excess fitting.',
             'Repeat a new independent random table with the same fixed search budget.'),
            ('selection_bias', 'Selecting the training champion exaggerates its ability to generalize.',
             'Frozen selections show reproducible above-chance performance on fresh null tables.',
             'Compare frozen outcomes with independently generated null tables.'),
        ),
    },
    'adaptive_search_not_better_than_grammar_on_this_task': {
        'question': 'When does adaptive structural search improve on an equal-budget grammar baseline?',
        'observation': 'A selected full-search model failed to outperform grammar-only on a held-out task.',
        'priority_base': 4.5,
        'hypotheses': (
            ('operator_inefficiency', 'Mutations and crossover waste budget on unsuitable task structure.',
             'Equal-budget independent replications consistently favor adaptive search.',
             'Repeat a structured target with full and grammar-only mechanisms.'),
            ('variance', 'The observed policy ranking is caused by stochastic search variation.',
             'Independent seeds reproduce the same stable performance difference.',
             'Compare full and grammar-only on new seeds without reusing old held-out cells.'),
        ),
    },
    'frontier_unresolved_structure': {
        'question': 'Which untested mathematical structure is most informative to investigate next?',
        'observation': 'Research scope contains structured mathematical tasks without enough evidence.',
        'priority_base': 1.0,
        'hypotheses': (
            ('finite_grammar', 'The bounded grammar is sufficient for simple structured families.',
             'An unseen structured family cannot be reconstructed by the current grammar.',
             'Select a new structured task with a frozen training/held-out protocol.'),
            ('transfer_gap', 'Warm starts from prior tasks help recover related motifs.',
             'Fresh split results do not improve relative to no-warm controls.',
             'Compare warm-start and no-warm controls on a fresh structured family.'),
        ),
    },
}


def _experiment_evidence(root: Path, state: dict) -> dict[str, list[dict]]:
    evidence = {kind: [] for kind in QUESTIONS}
    for row in state.get('history', []):
        number = row['cycle_number']
        if not 1 <= number <= state.get('completed_cycles', 0):
            raise ValueError('invalid history cycle order')
        path = root/'cycles'/f'{number:05d}'/'result.json'
        if not path.is_file():
            raise ValueError(f'completed cycle missing result: {number}')
        result = json.loads(path.read_text('utf8'))
        if result.get('cycle_number') != number or result.get('case') != row['case']:
            raise ValueError('result does not match completed state')
        full = next((x for x in result['arms'] if x['arm'] == 'full'), None)
        if full is None or not full['training_count'] or not full['holdout']['count']:
            raise ValueError('missing full arm or denominators')
        train_accuracy = 1 - full['training_errors'] / full['training_count']
        test_accuracy = 1 - full['holdout']['errors'] / full['holdout']['count']
        if not all(0 <= value <= 1 for value in (train_accuracy, test_accuracy)):
            raise ValueError('invalid accuracy outside [0, 1]')
        kinds = set(result.get('issues', ())) & QUESTIONS.keys()
        if result['case'] in STRUCTURED_CASES and test_accuracy < .5:
            kinds.add('weak_structured_generalization')
        if train_accuracy - test_accuracy > .20:
            kinds.add('generalization_gap')
        for kind in kinds:
            evidence[kind].append({
                'cycle_number': number, 'case': result['case'], 'seed': result['seed'],
                'train_accuracy': round(train_accuracy, 8),
                'holdout_accuracy': round(test_accuracy, 8),
                'source': f'cycles/{number:05d}/result.json',
                'interpretation': 'Exploratory observation only; not a verified causal explanation',
            })
    return evidence


def build_registry(root: Path | str, state: dict) -> dict:
    """Derive a reproducible problem tree solely from completed immutable results."""
    root = Path(root)
    evidence = _experiment_evidence(root, state)
    attempts: dict[str, int] = {}
    for path in sorted((root/'science'/'plans').glob('*.json')):
        proposal = json.loads(path.read_text('utf8'))
        if proposal.get('question_id'):
            key = str(proposal['question_id'])
            attempts[key] = attempts.get(key, 0) + 1
    questions = []
    for kind, definition in QUESTIONS.items():
        records = evidence[kind]
        if not records and kind != 'frontier_unresolved_structure':
            continue
        id_ = 'Q-' + kind
        total = attempts.get(id_, 0)
        # Planning priority is a documented heuristic, not probability of truth.
        urgency = max((1-row['holdout_accuracy'] for row in records), default=0)
        score = round(max(0, definition['priority_base'] + urgency + min(3, len(records))*.10 - total*1.2), 3)
        status = ('needs_new_method' if total >= 2 else 'investigating' if total else 'open')
        questions.append({
            'id': id_, 'parent_id': 'Q-math-generalization', 'kind': kind,
            'scientific_question': definition['question'], 'observation': definition['observation'],
            'hypotheses': [
                {'id': f'H-{kind}-{name}', 'explanation': explanation,
                 'falsified_by': falsifier, 'experimental_test': test,
                 'status': 'untested_or_exploratory'}
                for name, explanation, falsifier, test in definition['hypotheses']
            ],
            'evidence': records, 'focus_attempts': total,
            'followup_quota': 2, 'planning_priority': score,
            'priority_is_statistical_confidence': False,
            'status': status, 'conclusion': 'UNRESOLVED',
            'stop_condition': 'after two focused followups, require a new method or human review',
        })
    return {'schema':'pl5-v375-science-1', 'observed_cycles': state.get('completed_cycles',0),
            'parent_questions': [{'id':'Q-math-generalization',
                 'question':'When do learned mathematical expressions genuinely generalize?',
                 'conclusion':'UNRESOLVED'}],
            'questions': sorted(questions, key=lambda item:(-item['planning_priority'], item['id'])),
            'study_type':'adaptive_synthetic_exploration_not_confirmatory',
            'production_enabled':False, 'scientific_discovery_confirmed':False}


def choose_experiment(registry: dict, state: dict) -> dict:
    """Propose a falsifiable fresh experiment; no access to future held-out labels."""
    candidates = [q for q in registry['questions'] if q['status'] != 'needs_new_method']
    question = candidates[0] if candidates else next(q for q in registry['questions'] if q['kind']=='frontier_unresolved_structure')
    hypotheses = question['hypotheses']
    hypothesis = hypotheses[question['focus_attempts'] % len(hypotheses)]
    if question['kind'] in ('weak_structured_generalization', 'generalization_gap',
                            'adaptive_search_not_better_than_grammar_on_this_task'):
        struct = [e for e in reversed(question['evidence']) if e['case'] in STRUCTURED_CASES]
        case = struct[0]['case'] if struct else 'xor_mixed'
    elif question['kind'] == 'random_data_spurious_fit':
        case = 'iid_b' if question['focus_attempts'] % 2 else 'iid_a'
    else:
        case = choose_next_task(state, control_every=state.get('control_every', 4))
        if case.startswith('iid_'):
            case = min(STRUCTURED_CASES, key=lambda c: sum(x['case']==c for x in state.get('history',())))
    return {
        'question_id': question['id'], 'hypothesis_id': hypothesis['id'],
        'case': case, 'experiment_rationale': hypothesis['experimental_test'],
        'falsification_criterion': hypothesis['falsified_by'],
        'followup_attempt': question['focus_attempts']+1,
        'confirmatory_pvalue_permitted':False,
        'scientific_conclusion':'UNRESOLVED', 'production_enabled':False,
    }
