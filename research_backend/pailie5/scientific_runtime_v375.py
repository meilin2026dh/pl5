"""V3.7.5 bounded question-led researcher using the existing V3.7.4 search engine."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path

from .autonomous_v374 import (_atomic_update, _new_state, _run_cycles_unlocked,
                              _write_once, choose_next_task)
from .scientific_questions_v375 import build_registry, choose_experiment


def _json_digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                      ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _plan(root: Path, state: dict, registry: dict) -> dict:
    number = state['completed_cycles']+1
    path = root/'science'/'plans'/f'{number:05d}.json'
    if path.exists():
        prior=json.loads(path.read_text('utf8'))
        signature=prior.pop('sha256',None)
        if signature != _json_digest(prior):
            raise ValueError('locked scientific plan digest mismatch')
        if prior.get('cycle_number') != number or prior.get('budget') != state['evaluation_budget']:
            raise ValueError('locked scientific plan configuration mismatch')
        prior['sha256']=signature
        return prior
    chosen=choose_experiment(registry, state)
    compulsory = (state['completed_cycles'] % state['control_every'] == state['control_every']-1)
    if compulsory:
        chosen={**chosen,
                'question_id':'Q-periodic_null_control',
                'hypothesis_id':'H-periodic_null_calibration',
                'case':choose_next_task(state,control_every=state['control_every']),
                'experiment_rationale':'Periodic independent random negative control; cannot be displaced by priorities.',
                'falsification_criterion':'A truly independent random target repeatedly shows a verified out-of-sample advantage after multiplicity correction.',
                'followup_attempt':0,
                'mandatory_null_control':True}
    else:
        chosen['mandatory_null_control']=False
    payload={
        'schema':'pl5-v375-locked-question-plan-1',
        'cycle_number':number,
        'seed':(state['base_seed'] + number * 1009) % (2**32),
        'budget':state['evaluation_budget'],
        'train_cells':60, 'holdout_cells':40,
        'proposed_before_cycle_result':True,
        'prospective_experiment':True,
        'study_type':'adaptive_synthetic_exploration_not_confirmatory',
        **chosen,
    }
    payload['sha256']=_json_digest(payload)
    _write_once(path,payload)
    return payload


def run_scientific_cycles(output: Path | str, *, cycles: int=3, budget: int=400,
                          seed: int=37401, control_every: int=4) -> dict:
    """Run exactly `cycles` new experimental cycles, or pause safely on failure.

    Acquires the same `.run.lock` as V3.7.4 to protect shared state/artifacts.
    All previously frozen experiment outputs are immutable. Never a daemon.
    """
    if (type(cycles) is not int or not 1 <= cycles <= 30 or
        type(seed) is not int or not 0 <= seed < 2**32 or
        type(budget) is not int or not 100 <= budget <= 50000 or
        type(control_every) is not int or not 2 <= control_every <= 20):
        raise ValueError('invalid bounded science configuration')
    root=Path(output)
    root.mkdir(parents=True,exist_ok=True)
    lock=root/'.run.lock'
    try:
        fd=os.open(lock,os.O_CREAT | os.O_EXCL | os.O_WRONLY,0o600)
    except FileExistsError as exc:
        raise RuntimeError('research already running or stale lock; inspect before retry') from exc
    try:
        with os.fdopen(fd,'w',encoding='utf8') as stream:
            stream.write(f'pid={os.getpid()}\nengine=scientific-v375\n')
        state_path=root/'state.json'
        if state_path.exists():
            state=json.loads(state_path.read_text('utf8'))
            if (state.get('base_seed'),state.get('evaluation_budget'),state.get('control_every')) != (seed,budget,control_every):
                raise ValueError('locked research configuration mismatch')
        else:
            state=_new_state(seed,budget,control_every)
            _write_once(state_path,state)
        for _ in range(cycles):
            current=build_registry(root,state)
            _atomic_update(root/'science'/'registry.json',current)
            prospective=_plan(root,state,current)
            state['focus_case']=prospective['case']
            state['focus_question_id']=prospective['question_id']
            state['focus_hypothesis_id']=prospective['hypothesis_id']
            state['focus_plan_sha256']=prospective['sha256']
            _atomic_update(state_path,state)
            state=_run_cycles_unlocked(root,cycles=1,budget=budget,seed=seed,
                                      control_every=control_every)
            # Reconcile only completed results; never resolve research questions
            # from one adaptive synthetic experiment.
            current=build_registry(root,state)
            _atomic_update(root/'science'/'registry.json',current)
            snapshot=root/'science'/'registries'/f"{state['completed_cycles']:05d}.json"
            if not snapshot.exists():
                _write_once(snapshot,current)
        return state
    finally:
        lock.unlink(missing_ok=True)
