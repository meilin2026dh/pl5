"""PL5 V3.7.4 bounded autonomous scientific research controller.

This is an offline, auditable hypothesis/experiment/critique loop, NOT an
unrestricted LLM, background service, self-modifying program or betting tool.
Synthetic tasks are exploratory; every experiment uses a fresh split/seed.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
from typing import Sequence

import numpy as np

from .ablation_benchmark_v373 import CASES, load_warm_bank, split_table, truth_table
from .ablation_search_v373 import AblationConfig, Mechanisms, fit_budgeted
from .structure_ast_v372 import AST, normalize, validate_ast
from .structure_evidence_v372 import load_operator, save_operator, evaluate_frozen, certify_table
from .structure_search_v372 import CellDataset
from .symbolic_operators_v30 import eval_expr

STRUCTURED_CASES = (
    'shifted_bilinear', 'gcd_offsets', 'xor_mixed', 'difference_squares',
    'asymmetric_cubic', 'shifted_square', 'shifted_minimum', 'abs_product_plus_b',
)
POLICIES = ('full', 'no_warm', 'selective', 'grammar_only')


def _digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def _write_once(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')


def _atomic_update(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    with temp.open('w', encoding='utf8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')
    temp.replace(path)


def _subexpressions(tree: AST):
    yield tree
    if tree[0] == 'binary':
        yield from _subexpressions(tree[2])
        yield from _subexpressions(tree[3])


def select_warm_starts(training: CellDataset, bank: Sequence[AST], *,
                       max_items: int = 6, max_screen: int = 30) -> tuple[tuple[AST, ...], int]:
    """Preselect reusable formulas using training labels exclusively.

    Each distinct candidate scored against training is charged as a separate
    model evaluation in the subsequent cycle's *total* evaluation budget.
    """
    if not isinstance(training, CellDataset) or not 1 <= max_items <= 32 or not 1 <= max_screen <= 200:
        raise ValueError('invalid knowledge screening input or budget')
    candidate_trees: list[AST] = []
    seen: set[AST] = set()
    for expression in bank:
        validate_ast(expression)
        for sub in _subexpressions(expression):
            try:
                validate_ast(sub, max_nodes=11, max_depth=6)
                sub = normalize(sub)
            except ValueError:
                continue
            if sub not in seen:
                seen.add(sub)
                candidate_trees.append(sub)
    chosen: list[tuple[int, int, str, AST]] = []
    inputs = np.array([10 * a + b for a, b, _ in training.rows], dtype=int)
    actual = np.array([target for _, _, target in training.rows], dtype=int)
    used = 0
    for expr in candidate_trees:
        if used >= max_screen:
            break
        used += 1  # Invalid arithmetic also costs a screening evaluation.
        try:
            table_values = np.asarray(eval_expr(expr)).reshape(100)
            misses = int(np.count_nonzero(table_values[inputs] % 10 != actual))
            nodes, _ = validate_ast(expr)
            chosen.append((misses, nodes, repr(expr), expr))
        except (ValueError, OverflowError, ArithmeticError):
            continue
    chosen.sort(key=lambda row: row[:3])
    return tuple(row[3] for row in chosen[:max_items]), used


def choose_next_task(state: dict, *, control_every: int = 4) -> str:
    """Prefer poorly generalized tasks while injecting periodic null controls.

    Past holdouts affect only *future*, independently-seeded experiments. This
    schedule is exploratory and cannot establish confirmatory significance.
    """
    if not isinstance(control_every, int) or control_every < 2:
        raise ValueError('control_every must be >= 2')
    completed = state.get('completed_cycles', 0)
    if completed % control_every == control_every - 1:
        return 'iid_a' if (completed // control_every) % 2 == 0 else 'iid_b'
    history = state.get('history', [])
    if history:
        recent = history[-1]
        if recent['case'] in STRUCTURED_CASES and recent.get('weakness', 0) > .50:
            same_case = sum(row['case'] == recent['case'] for row in history)
            if same_case < 2:
                return recent['case']  # New seed + lock; never reuse its test rows.
    observed = {case: sum(row['case'] == case for row in history) for case in STRUCTURED_CASES}
    return min(STRUCTURED_CASES, key=lambda case: (observed[case], STRUCTURED_CASES.index(case)))


def _new_state(seed: int, budget: int, control_every: int) -> dict:
    return {'schema': 'pl5-v374-autonomy-1', 'base_seed': seed,
            'evaluation_budget': budget, 'control_every': control_every,
            'completed_cycles': 0, 'history': [], 'issues': [],
            'next_hypothesis': 'Can a train-selected structured expression generalize to unseen digit pairs?',
            'production_enabled': False, 'predictive_advantage': 'NOT_ESTABLISHED',
            'study_type': 'adaptive_synthetic_exploration_not_confirmatory'}


def _preplanned_cycle(state: dict, cycle_number: int) -> dict:
    seed = (state['base_seed'] + cycle_number * 1009) % (2**32)
    default_case = choose_next_task(state, control_every=state['control_every'])
    focus = state.get('focus_case')
    if focus is not None and focus not in (*STRUCTURED_CASES, 'iid_a', 'iid_b'):
        raise ValueError('invalid scientific focus case')
    mandatory_null_control = (state['completed_cycles'] % state['control_every'] == state['control_every']-1)
    case = default_case if mandatory_null_control else (focus or default_case)
    null = case.startswith('iid_')
    return {
        'schema': 'pl5-v374-predeclared-cycle-1', 'cycle_number': cycle_number,
        'case': case, 'seed': seed, 'budget': state['evaluation_budget'],
        'question': ('Does the agent incorrectly fit a random independent table?' if null else
                     'Does adaptive expression search generalize on a new synthetic structure?'),
        'hypothesis': state['next_hypothesis'], 'train_cells': 60, 'holdout_cells': 40,
        'policies': list(POLICIES), 'test_labels_hidden_from_fit': True,
        'adaptive_task_selection': True, 'confirmatory_pvalue_permitted': False,
        'research_only': True, 'production_enabled': False,
        **({'scientific_question_id': state['focus_question_id'],
            'scientific_hypothesis_id': state['focus_hypothesis_id'],
            'scientific_plan_sha256': state['focus_plan_sha256']}
           if 'focus_question_id' in state else {}),
    }


def _get_bank(state: dict, root: Path) -> tuple[AST, ...]:
    base, _ = load_warm_bank()
    discovered = []
    # Consume only previously completed cycle records, never pending artifacts.
    for row in state['history']:
        if row.get('case', '').startswith('iid_') or not row.get('transfer_candidate'):
            continue
        operator = root/'cycles'/f"{row['cycle_number']:05d}"/'fits'/'full'/'operator.json'
        if operator.exists():
            discovered.append(load_operator(operator).expression)
    return tuple(dict.fromkeys((*base, *discovered[-20:])))


def _cycle(root: Path, state: dict, cycle_number: int) -> dict:
    cycle_dir = root/'cycles'/f'{cycle_number:05d}'
    protocol_path = cycle_dir/'protocol.json'
    proposal = _preplanned_cycle(state, cycle_number)
    if protocol_path.exists():
        protocol = json.loads(protocol_path.read_text('utf8'))
        if protocol != proposal:
            raise ValueError('locked cycle configuration mismatch: refusing to alter preregistered experiment')
    else:
        _write_once(protocol_path, proposal)
        protocol = proposal
    result_path = cycle_dir/'result.json'
    if result_path.exists():
        return json.loads(result_path.read_text('utf8'))
    case, seed = protocol['case'], protocol['seed']
    truth = truth_table(case, seed)
    training, holdout = split_table(truth, seed, case)
    if len(set(training.pairs) & set(holdout.pairs)):
        raise ValueError('train/holdout overlap')
    bank = _get_bank(state, root)
    selected, screening = select_warm_starts(training, bank, max_items=6,
                                            max_screen=min(30, max(1, protocol['budget']//5)))
    if screening >= protocol['budget']:
        raise ValueError('knowledge screening exhausts cycle budget')
    arms_config = {
        'full': (Mechanisms(), bank, protocol['budget'], 0),
        'no_warm': (Mechanisms(warm_start=False), (), protocol['budget'], 0),
        'selective': (Mechanisms(), selected, protocol['budget']-screening, screening),
        'grammar_only': (Mechanisms(mutation=False,crossover=False,warm_start=False,guided=False),
                         (), protocol['budget'], 0),
    }
    frozen: dict[str, dict] = {}
    for arm in protocol['policies']:
        mechanism, start, search_budget, selector_cost = arms_config[arm]
        fit_path = cycle_dir/'fits'/arm/'fit.json'
        op_path = cycle_dir/'fits'/arm/'operator.json'
        if fit_path.exists() and op_path.exists():
            frozen[arm] = json.loads(fit_path.read_text('utf8'))
            continue
        if fit_path.exists() != op_path.exists():
            raise RuntimeError('incomplete frozen operator pair; manual forensic review required')
        config = AblationConfig(seed=seed, evaluation_budget=search_budget)
        fitted = fit_budgeted(training, config, mechanism, warm_starts=tuple(start))
        # Save operator first, then its fit record, both with exclusive create.
        save_operator(fitted.operator, op_path)
        record = {'arm': arm, 'operator_id': fitted.operator.identity,
                  'training_errors': fitted.training_errors,
                  'training_count': fitted.training_count,
                  'training_evaluations': fitted.evaluations,
                  'selector_evaluations': selector_cost,
                  'budget_matched': fitted.budget_matched and
                                    fitted.evaluations+selector_cost == protocol['budget'],
                  'selection_used': 'training_cells_only',
                  'candidate_origin': fitted.winning_origin}
        _write_once(fit_path, record)
        frozen[arm] = record
    # Important: holdout answers are opened only after every candidate is frozen.
    evaluation = []
    for arm in protocol['policies']:
        record = frozen[arm]
        op = load_operator(cycle_dir/'fits'/arm/'operator.json')
        if record['operator_id'] != op.identity:
            raise ValueError('frozen operator integrity mismatch')
        metrics = evaluate_frozen(op, holdout)
        certificate = certify_table(op, truth)
        evaluation.append({**record, 'frozen_before_holdout': True,
                           'holdout': metrics, 'whole_table_errors': certificate['whole_table_errors'],
                           'exact_table': certificate['exact_on_all_100_pairs'],
                           'nodes': certificate['nodes']})
    full = next(r for r in evaluation if r['arm'] == 'full')
    control = case.startswith('iid_')
    train_acc = 1-full['training_errors']/full['training_count']
    test_acc = full['holdout']['accuracy']
    issues = []
    if not all(row['budget_matched'] for row in evaluation):
        issues.append('search_budget_unmatched')
    if train_acc - test_acc > .20:
        issues.append('generalization_gap')
    if control and test_acc < .2 and train_acc > .2:
        issues.append('random_data_spurious_fit')
    grammar = next(r for r in evaluation if r['arm'] == 'grammar_only')
    if test_acc < grammar['holdout']['accuracy']:
        issues.append('adaptive_search_not_better_than_grammar_on_this_task')
    transfer = (not control and test_acc >= .8 and full['training_errors']/60 <= .20)
    diagnosis = ('No confirmed reusable structure; new seed needed.' if control else
                 'Train/holdout mismatch; prioritize a fresh split and simpler structures.'
                 if 'generalization_gap' in issues else
                 'Candidate structure may transfer, but only to a fresh task; do not reuse this test split.')
    result = {'schema':'pl5-v374-cycle-result-1','cycle_number':cycle_number,
              'case':case,'seed':seed,'arms':evaluation,'issues':issues,
              'diagnosis':diagnosis, 'weakness':1-test_acc,'transfer_candidate':transfer,
              'status':'negative_control' if control else 'exploratory_only',
              'next_hypothesis': diagnosis, 'production_enabled':False,
              'predictive_advantage':'NOT_ESTABLISHED'}
    _write_once(result_path,result)
    return result


def _run_cycles_unlocked(output: Path | str, *, cycles: int=3, budget: int=400,
               seed: int=37401, control_every: int=4) -> dict:
    """Run exactly `cycles` finite, persistent research turns; not a daemon."""
    if (type(cycles) is not int or not 1 <= cycles <= 30 or
        type(seed) is not int or not 0 <= seed < 2**32 or
        type(budget) is not int or not 100 <= budget <= 50000 or
        type(control_every) is not int or not 2 <= control_every <= 20):
        raise ValueError('invalid bounded autonomy configuration')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    state_path = output/'state.json'
    if state_path.exists():
        state = json.loads(state_path.read_text('utf8'))
        if (state['base_seed'],state['evaluation_budget'],state['control_every']) != (seed,budget,control_every):
            raise ValueError('locked research configuration: cannot silently change seed or budget')
    else:
        state=_new_state(seed,budget,control_every)
        _write_once(state_path,state)
    for _ in range(cycles):
        cycle_number=state['completed_cycles']+1
        try:
            result=_cycle(output,state,cycle_number)
        except Exception as exc:
            issue_file=output/'cycles'/f'{cycle_number:05d}'/'failure.json'
            _atomic_update(issue_file, {'cycle': cycle_number, 'error_type': type(exc).__name__,
                                        'description': str(exc),
                                        'research_question': 'Which input, checkpoint or algorithm boundary caused this error?',
                                        'safe_response':'pause_without_overwriting_completed_evidence'})
            raise
        row={k: result[k] for k in ('cycle_number','case','seed','weakness','issues','transfer_candidate','status')}
        state['history'].append(row)
        state['issues'].extend({'cycle_number':cycle_number,'issue':issue} for issue in result['issues'])
        state['completed_cycles']=cycle_number
        state['next_hypothesis']=result['next_hypothesis']
        _atomic_update(state_path,state)
    return state


def run_cycles(output: Path | str, *, cycles: int=3, budget: int=400,
               seed: int=37401, control_every: int=4) -> dict:
    """Exclusively run finite autonomous cycles; fail safely if another process owns the directory."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    lock_path = output/'.run.lock'
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RuntimeError('research already running or stale lock; inspect before retry') from exc
    try:
        with os.fdopen(fd, 'w', encoding='utf8') as handle:
            handle.write(f'pid={os.getpid()}\n')
        return _run_cycles_unlocked(output, cycles=cycles, budget=budget,
                                    seed=seed, control_every=control_every)
    finally:
        lock_path.unlink(missing_ok=True)
