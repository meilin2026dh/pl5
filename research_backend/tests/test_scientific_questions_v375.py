"""Tests for V3.7.5 hypothesis-driven autonomous science (synthetic only)."""
from __future__ import annotations
import json
from pathlib import Path
import pytest

from pailie5.scientific_questions_v375 import build_registry, choose_experiment
from pailie5.scientific_runtime_v375 import run_scientific_cycles
from pailie5.autonomous_v374 import _preplanned_cycle


def fake_result(root: Path, cycle: int, case: str, *, train_error: int,
                held_correct: int, issue_tags=()) -> None:
    folder = root/'cycles'/f'{cycle:05d}'
    folder.mkdir(parents=True, exist_ok=True)
    (folder/'result.json').write_text(json.dumps({
        'cycle_number':cycle,'case':case,'seed':1000+cycle,'issues':list(issue_tags),
        'arms':[
            {'arm':'full','training_count':60,'training_errors':train_error,
             'holdout':{'count':40,'errors':40-held_correct}},
            {'arm':'grammar_only','training_count':60,'training_errors':15,
             'holdout':{'count':40,'errors':22}},
        ],'status':'negative_control' if case.startswith('iid') else 'exploratory_only'
    }),encoding='utf8')


def state_for(cases):
    return {'completed_cycles':len(cases),'history':[
        {'cycle_number':i,'case':case,'seed':1000+i, 'weakness':.8,
         'issues':[], 'transfer_candidate':False, 'status':'exploratory_only'}
        for i,case in enumerate(cases,1)
    ],'base_seed':37501,'evaluation_budget':110,'control_every':4}


def test_scientific_catalog_distinguishes_random_spurious_and_structural_failure(tmp_path):
    fake_result(tmp_path,1,'iid_a',train_error=30,held_correct=4,
                issue_tags=['random_data_spurious_fit','generalization_gap'])
    fake_result(tmp_path,2,'shifted_bilinear',train_error=2,held_correct=8)
    reg=build_registry(tmp_path,state_for(['iid_a','shifted_bilinear']))
    by_kind={q['kind']:q for q in reg['questions']}
    assert {'random_data_spurious_fit','generalization_gap','weak_structured_generalization'} <= set(by_kind)
    for question in reg['questions']:
        assert question['parent_id']=='Q-math-generalization'
        assert len(question['hypotheses'])>=2
        assert all(x['falsified_by'] and x['experimental_test'] for x in question['hypotheses'])
        assert question['conclusion']=='UNRESOLVED'
        assert question['planning_priority']>=0
    assert any('cycles/00002/result.json' in e['source'] for e in by_kind['weak_structured_generalization']['evidence'])
    assert reg['production_enabled'] is False


def test_next_science_question_prioritizes_unresolved_structural_problem(tmp_path):
    fake_result(tmp_path,1,'iid_a',train_error=40,held_correct=2,issue_tags=['random_data_spurious_fit'])
    fake_result(tmp_path,2,'difference_squares',train_error=2,held_correct=9)
    st=state_for(['iid_a','difference_squares'])
    reg=build_registry(tmp_path,st)
    proposed=choose_experiment(reg,st)
    assert proposed['question_id'].startswith('Q-')
    assert proposed['question_id']=='Q-weak_structured_generalization'
    assert proposed['case']=='difference_squares'
    assert proposed['hypothesis_id'] and proposed['experiment_rationale']
    assert proposed['confirmatory_pvalue_permitted'] is False


def test_no_experiment_recycling_after_quota(tmp_path):
    fake_result(tmp_path,1,'shifted_bilinear',train_error=1,held_correct=4)
    st=state_for(['shifted_bilinear'])
    plans=tmp_path/'science'/'plans'
    plans.mkdir(parents=True)
    for j in range(2,4):
        (plans/f'{j:05d}.json').write_text(json.dumps({'cycle_number':j,
            'question_id':'Q-weak_structured_generalization',
            'hypothesis_id':f'H-{j}','case':'shifted_bilinear'}))
    reg=build_registry(tmp_path,st)
    q=next(x for x in reg['questions'] if x['kind']=='weak_structured_generalization')
    assert q['status']=='needs_new_method'
    assert choose_experiment(reg,st)['question_id']!='Q-weak_structured_generalization'


def test_focus_selection_changes_real_protocol_but_never_skips_null_control():
    state={'completed_cycles':0,'history':[], 'base_seed':2,'evaluation_budget':110,
           'control_every':4,'next_hypothesis':'test',
           'focus_case':'gcd_offsets','focus_question_id':'Q-weak_structured_generalization',
           'focus_hypothesis_id':'H-structural-capacity', 'focus_plan_sha256':'abcd'}
    protocol=_preplanned_cycle(state,1)
    assert protocol['case']=='gcd_offsets'
    assert protocol['scientific_question_id']=='Q-weak_structured_generalization'
    assert protocol['scientific_plan_sha256']=='abcd'
    state['completed_cycles']=3
    assert _preplanned_cycle(state,4)['case'].startswith('iid_')
    state['focus_case']='__unknown__'
    state['completed_cycles']=0
    with pytest.raises(ValueError,match='focus'):
        _preplanned_cycle(state,1)


def test_scientific_runtime_generates_locked_plan_and_evidence(tmp_path):
    root=tmp_path/'scientific'
    after=run_scientific_cycles(root,cycles=2,budget=110,seed=37510,control_every=4)
    assert after['completed_cycles']==2
    assert after['production_enabled'] is False
    for i in (1,2):
        plan=json.loads((root/'science'/'plans'/f'{i:05d}.json').read_text())
        protocol=json.loads((root/'cycles'/f'{i:05d}'/'protocol.json').read_text())
        assert protocol['scientific_plan_sha256']==plan['sha256']
        assert protocol['scientific_question_id']==plan['question_id']
        assert protocol['case']==plan['case']
        assert (root/'cycles'/f'{i:05d}'/'result.json').exists()
    registry=json.loads((root/'science'/'registry.json').read_text())
    assert registry['observed_cycles']==2
    assert registry['questions']
    old=(root/'cycles'/'00001'/'result.json').read_bytes()
    again=run_scientific_cycles(root,cycles=1,budget=110,seed=37510,control_every=4)
    assert again['completed_cycles']==3
    assert (root/'cycles'/'00001'/'result.json').read_bytes()==old


def test_scientific_runtime_refuses_parallel_execution(tmp_path):
    root=tmp_path/'scientific'
    root.mkdir()
    (root/'.run.lock').write_text('other process')
    with pytest.raises(RuntimeError,match='already running'):
        run_scientific_cycles(root,cycles=1,budget=110,seed=37510)
    assert (root/'.run.lock').exists()


def test_invalid_science_run_is_rejected_before_any_files(tmp_path):
    root=tmp_path/'scientific'
    with pytest.raises(ValueError):
        run_scientific_cycles(root,cycles=31,budget=110,seed=1)
    assert not (root/'cycles').exists()


def test_science_cli_executes_from_project_root(tmp_path):
    import subprocess,sys
    cli=Path(__file__).resolve().parents[1]/'research_scientific_v375.py'
    out=tmp_path/'cli'
    p=subprocess.run([sys.executable,str(cli),'--output',str(out),'--cycles','1',
                      '--budget','100','--seed','37501'],capture_output=True,text=True,timeout=60)
    assert p.returncode==0,p.stderr
    result=json.loads(p.stdout)
    assert result['completed_cycles']==1
    assert result['research_only'] is True
    assert result['background_running'] is False


def test_mandatory_null_control_has_its_own_scientific_identity(tmp_path):
    root=tmp_path/'null-controls'
    run_scientific_cycles(root,cycles=4,budget=100,seed=37501,control_every=4)
    plan=json.loads((root/'science'/'plans'/'00004.json').read_text())
    assert plan['mandatory_null_control'] is True
    assert plan['case'].startswith('iid_')
    assert plan['question_id']=='Q-periodic_null_control'
    assert plan['hypothesis_id']=='H-periodic_null_calibration'


def test_tampered_locked_plan_blocks_execution(tmp_path):
    root=tmp_path/'tamper'
    run_scientific_cycles(root,cycles=1,budget=100,seed=37501)
    plans=root/'science'/'plans'
    (plans/'00002.json').write_text(json.dumps({'sha256':'not-a-real-signature',
                                               'cycle_number':2,'budget':100}))
    with pytest.raises(ValueError,match='digest mismatch'):
        run_scientific_cycles(root,cycles=1,budget=100,seed=37501)
    assert not (root/'cycles'/'00002'/'result.json').exists()


def test_v375_current_package_metadata_is_consistent():
    import tomllib
    import pailie5
    package=Path(__file__).resolve().parents[1]
    metadata=tomllib.loads((package/'pyproject.toml').read_text())
    # V3.7.5 compatibility remains required when cumulative releases advance.
    assert metadata['project']['version']==pailie5.__version__
    assert tuple(map(int, pailie5.__version__.split('.'))) >= (3, 7, 5)
