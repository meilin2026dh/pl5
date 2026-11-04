"""V3.7.6 scientific intervention runner: safe, bounded and append-only.

Method proposals (not code) change dataset information, grammar capacity, or
candidate budget. The same sealed holdout tests a reference and challenger.
No scientific or lottery prediction claims are made from this adaptive run.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path

import numpy as np

from .ablation_benchmark_v373 import CASES, truth_table
from .ablation_search_v373 import AblationConfig, Mechanisms, fit_budgeted
from .scientific_methods_v376 import propose_study
from .structure_evidence_v372 import save_operator, load_operator, evaluate_frozen
from .structure_search_v372 import CellDataset


def _digest_json(obj: dict) -> str:
    return sha256(json.dumps(obj,sort_keys=True,separators=(',', ':'),
                             ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def _write_once(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x',encoding='utf8') as f:
        json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False)
        f.write('\n')


def _atomic_update(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix('.temporary')
    with tmp.open('w',encoding='utf8') as f:
        json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False)
        f.write('\n')
    tmp.replace(path)


def _balanced_sample(candidates: list[int], count: int=60) -> list[int]:
    """Input-coordinate diversity, without consulting any target labels."""
    if count > len(candidates) or len(set(candidates)) != len(candidates):
        raise ValueError('invalid sampling candidates')
    remaining=list(candidates)
    picked=[]
    rows=[0]*10
    columns=[0]*10
    for _ in range(count):
        best=min(range(len(remaining)),key=lambda index:(
            rows[remaining[index]//10]+columns[remaining[index]%10],
            max(rows[remaining[index]//10],columns[remaining[index]%10]),index))
        value=remaining.pop(best)
        picked.append(value)
        rows[value//10]+=1
        columns[value%10]+=1
    return picked


def _science_questions_from_history(history: list[dict]) -> list[dict]:
    tested={method:[row for row in history
                    if row.get('method')==method and not row.get('mandatory_null_control')]
            for method in ('more_training','richer_grammar','more_search')}
    if not all(tested.values()):
        return []
    if any(any(row.get('holdout_delta',0)>0 for row in rows) for rows in tested.values()):
        return []
    evidence=[{'study_number':row['study_number'], 'method':method,
               'holdout_delta':row['holdout_delta']}
              for method,rows in tested.items() for row in rows]
    balanced=any(row.get('method')=='balanced_sampling' for row in history)
    questions=[{'id':'Q-method_family_nonimprovement',
             'scientific_question':'Why do independent changes to sample size, expression capacity, and search budget fail to improve held-out results?',
             'evidence':evidence, 'hypotheses':[
               {'id':'H-coordinate_sampling','description':'Input-coordinate choice, rather than quantity, limits identifiability.',
                'test':'Compare balanced vs original coordinate sampling with equal label budget.'},
               {'id':'H-inductive_bias','description':'The fixed primitive grammar or search proposal distribution misses necessary structure.',
                'test':'Replicate on an unrelated target family before attempting new primitives.'}],
             'status':'investigating' if balanced else 'open',
             'scientific_conclusion':'UNRESOLVED',
             'confirmatory_pvalue_permitted':False}]
    cross=[row for row in history if row.get('method')=='cross_family_replication'
           and not row.get('mandatory_null_control')]
    informative=[row for row in history if not row.get('mandatory_null_control')]
    if len(cross)>=2 and all(row.get('holdout_delta',0)<=0 for row in informative):
        questions.append({
            'id':'Q-new_primitive_needed',
            'scientific_question':'Does the current mathematical primitive set or proposal distribution prevent reliable generalization?',
            'evidence':[{'study_number':row['study_number'],
                         'method':row['method'],'holdout_delta':row['holdout_delta']}
                        for row in informative],
            'hypotheses':[
              {'id':'H-missing_primitive',
               'description':'The current bounded primitive vocabulary cannot express the required structure compactly.',
               'test':'Predeclare a new safe mathematical primitive and benchmark it on a new task family.'},
              {'id':'H-search_proposal_bias',
               'description':'The search distribution does not reach existing representable expressions efficiently.',
               'test':'Test alternative proposal mechanisms at equal budget with untouched targets.'}],
            'status':'needs_new_method','scientific_conclusion':'UNRESOLVED',
            'confirmatory_pvalue_permitted':False,
            'stop_reason':'bounded_method_library_exhausted; no unsupported automatic code generation'})
    return questions


def _locked_plan(root: Path, registry: dict, state: dict) -> dict:
    number=state['completed_studies']+1
    path=root/'studies'/f'{number:05d}'/'plan.json'
    proposal=propose_study(registry,state['history'],number,state['base_seed'],
                           state['budget'],state['control_every'])
    # Select and freeze the *coordinates* before generating a target table.
    case_index=list(CASES).index(proposal['case'])
    order=np.random.default_rng(np.random.SeedSequence([
        proposal['seed'],991,case_index])).permutation(100).tolist()
    proposal.update({'train_pair_order':order[:80], 'holdout_pair_ids':order[80:],
                     'study_type':'adaptive_synthetic_exploration_not_confirmatory',
                     'frozen_before_accessing_test_labels':True})
    if proposal['method']=='balanced_sampling':
        proposal['challenger_pair_ids']=_balanced_sample(order[:80],60)
    proposal['sha256']=_digest_json(proposal)
    if path.exists():
        existing=json.loads(path.read_text('utf8'))
        signature=existing.pop('sha256',None)
        if signature != _digest_json(existing):
            raise ValueError('locked scientific method plan digest mismatch')
        existing['sha256']=signature
        if existing != proposal:
            raise ValueError('locked scientific method plan configuration mismatch')
        return existing
    _write_once(path,proposal)
    return proposal


def _train_and_freeze(root: Path, plan: dict) -> list[dict]:
    study=root/'studies'/f"{plan['study_number']:05d}"
    # The labels for test coordinates are not assembled into a dataset until
    # BOTH fits are saved and their identities validated.
    truth=truth_table(plan['case'],plan['seed'])
    records=[]
    for arm in ('baseline','challenger'):
        cfg=plan[arm]
        order=(plan['challenger_pair_ids'] if arm=='challenger'
               and plan['method']=='balanced_sampling' else
               plan['train_pair_order'][:cfg['train_cells']])
        training=CellDataset(tuple((int(i//10),int(i%10),int(truth.flat[i])) for i in order))
        if set(training.pairs) & {(i//10,i%10) for i in plan['holdout_pair_ids']}:
            raise ValueError('train/heldout coordinate overlap')
        record_path=study/'fits'/arm/'fit.json'
        op_path=study/'fits'/arm/'operator.json'
        if record_path.exists() != op_path.exists():
            raise RuntimeError('incomplete frozen fit artifacts; manual review required')
        if record_path.exists():
            record=json.loads(record_path.read_text('utf8'))
            if record['operator_id'] != load_operator(op_path).identity:
                raise ValueError('frozen operator identity mismatch')
            if record['training_fingerprint'] != training.fingerprint:
                raise ValueError('frozen training fingerprint mismatch')
        else:
            fitted=fit_budgeted(training,AblationConfig(
                seed=plan['seed'],evaluation_budget=cfg['evaluation_budget'],
                max_nodes=cfg['max_nodes']),Mechanisms(
                warm_start=False,guided=cfg.get('guided',True)))
            save_operator(fitted.operator,op_path)
            record={'arm':arm,'operator_id':fitted.operator.identity,
                    'training_fingerprint':training.fingerprint,
                    'training_correct':len(training.rows)-fitted.training_errors,
                    'training_count':len(training.rows),
                    'evaluations':fitted.evaluations,
                    'budget_matched':fitted.budget_matched,
                    'candidate_origin':fitted.winning_origin,
                    'test_labels_available_during_fit':False,
                    'training_pair_ids':list(order)}
            _write_once(record_path,record)
        records.append(record)
    # Freeze complete, now open the common unseen truth labels for evaluation.
    holdout=CellDataset(tuple((int(i//10),int(i%10),int(truth.flat[i]))
                              for i in plan['holdout_pair_ids']))
    evaluated=[]
    for record in records:
        operator=load_operator(study/'fits'/record['arm']/'operator.json')
        held=evaluate_frozen(operator,holdout)
        evaluated.append({**record,'holdout_correct':held['count']-held['errors'],
                          'holdout_count':held['count'],
                          'holdout_accuracy':held['accuracy'],
                          'common_holdout_fingerprint':holdout.fingerprint,
                          'frozen_before_holdout':True})
    return evaluated


def _read_signed(path: Path, *, label: str) -> dict:
    card=json.loads(path.read_text('utf8'))
    digest=card.pop('sha256',None)
    if digest != _digest_json(card):
        raise ValueError(f'{label} digest mismatch')
    card['sha256']=digest
    return card


def _verify_completed(root: Path, state: dict) -> None:
    if len(state.get('history', [])) != state.get('completed_studies', -1):
        raise ValueError('completed history length mismatch')
    for expected, row in enumerate(state['history'],1):
        folder=root/'studies'/f'{expected:05d}'
        plan=_read_signed(folder/'plan.json',label='plan')
        result=_read_signed(folder/'result.json',label='result')
        if (row.get('study_number')!=expected or plan.get('study_number')!=expected
            or result.get('study_number')!=expected
            or result.get('plan_sha256')!=plan['sha256']
            or row.get('plan_sha256')!=plan['sha256']
            or row.get('holdout_delta')!=result['holdout_delta']):
            raise ValueError('completed study record does not match frozen history')
        for arm in ('baseline','challenger'):
            try:
                operator=load_operator(folder/'fits'/arm/'operator.json')
            except (ValueError,KeyError,OSError) as exc:
                raise ValueError('frozen operator integrity check failed') from exc
            if operator.identity!=result[arm]['operator_id']:
                raise ValueError('frozen operator identity mismatch')


def _execute(root: Path,plan: dict) -> dict:
    path=root/'studies'/f"{plan['study_number']:05d}"/'result.json'
    if path.exists():
        result=_read_signed(path,label='result')
        if result.get('plan_sha256')!=plan['sha256']:
            raise ValueError('result/plan digest mismatch')
        return result
    evaluated=_train_and_freeze(root,plan)
    baseline,challenger=evaluated
    delta=round(challenger['holdout_accuracy']-baseline['holdout_accuracy'],8)
    issues=[]
    if not all(row['budget_matched'] for row in evaluated):
        issues.append('search_budget_unmatched')
    if not plan['mandatory_null_control'] and delta <= 0:
        issues.append('method_did_not_improve_on_this_task')
    if plan['mandatory_null_control'] and max(x['holdout_accuracy'] for x in evaluated) >= .30:
        issues.append('null_control_outlier_needs_replication')
    result={'schema':'pl5-v376-method-result-1',
            'study_number':plan['study_number'],'plan_sha256':plan['sha256'],
            'question_id':plan['question_id'], 'method':plan['method'],
            'case':plan['case'], 'seed':plan['seed'],
            'baseline':baseline,'challenger':challenger,
            'holdout_delta':delta,'issues':issues,
            'mandatory_null_control':plan['mandatory_null_control'],
            'evaluation_budget_by_arm':plan['cost_budget_by_arm'],
            'independent_split':True,'science_mode':'adaptive_exploratory',
            'scientific_conclusion':'UNRESOLVED',
            'claim_of_causal_resolution':False,'confirmatory_pvalue_permitted':False,
            'production_enabled':False, 'predictive_advantage':'NOT_ESTABLISHED'}
    result['sha256']=_digest_json(result)
    _write_once(path,result)
    return result


def run_method_studies(output: Path | str, historical: Path | str, *, studies: int=3,
                       budget: int=160, seed: int=37601, control_every: int=4) -> dict:
    """Run finite experimental-method studies using immutable V3.7.5 inputs."""
    if (type(studies) is not int or not 1<=studies<=12
        or type(budget) is not int or not 100<=budget<=10000
        or type(seed) is not int or not 0<=seed<2**32
        or type(control_every) is not int or not 2<=control_every<=20):
        raise ValueError('invalid bounded V3.7.6 research request')
    root=Path(output).resolve()
    historical=Path(historical).resolve()
    if root==historical or historical in root.parents:
        raise ValueError('new method experiments must not overwrite historical source')
    source=historical/'science'/'registry.json'
    if not source.is_file():
        raise ValueError('V3.7.5 scientific question registry unavailable')
    original_bytes=source.read_bytes()
    registry=json.loads(original_bytes)
    original_digest=sha256(original_bytes).hexdigest()
    root.mkdir(parents=True,exist_ok=True)
    lock=root/'.run.lock'
    try:
        fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError as exc:
        raise RuntimeError('research already running; inspect stale lock first') from exc
    try:
        with os.fdopen(fd,'w',encoding='utf8') as f:
            f.write(f'pid={os.getpid()}\nengine=v376\n')
        state_path=root/'state.json'
        if state_path.exists():
            state=json.loads(state_path.read_text('utf8'))
            if (state.get('base_seed'),state.get('budget'),state.get('control_every'))!=(seed,budget,control_every):
                raise ValueError('locked scientific method run configuration mismatch')
            if state.get('historical_registry_sha256')!=original_digest:
                raise ValueError('historical registry changed since research began')
            _verify_completed(root,state)
        else:
            if not registry.get('questions'):
                raise ValueError('no prior scientific questions')
            state={'schema':'pl5-v376-method-state-1',
                   'historical_registry_sha256':original_digest,
                   'historical_completed_cycles':registry.get('observed_cycles'),
                   'base_seed':seed,'budget':budget,'control_every':control_every,
                   'completed_studies':0,'history':[], 'production_enabled':False,
                   'scientific_conclusion':'UNRESOLVED'}
            _write_once(state_path,state)
        for _ in range(studies):
            # A recovered complete immutable result is safely reconciled.
            plan=_locked_plan(root,registry,state)
            result=_execute(root,plan)
            state['history'].append({
                'study_number':plan['study_number'],
                'plan_sha256':plan['sha256'], 'question_id':plan['question_id'],
                'case':plan['case'], 'method':plan['method'],
                'mandatory_null_control':plan['mandatory_null_control'],
                'holdout_delta':result['holdout_delta'], 'issues':result['issues'],
                'result_path':f"studies/{plan['study_number']:05d}/result.json"})
            state['completed_studies']+=1
            state['emergent_questions']=_science_questions_from_history(state['history'])
            _atomic_update(state_path,state)
        return state
    finally:
        lock.unlink(missing_ok=True)
