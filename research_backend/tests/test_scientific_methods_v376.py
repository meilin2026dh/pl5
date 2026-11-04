"""Behavior-first tests for V3.7.6 autonomous scientific method selection."""
import json
from pathlib import Path
import pytest

from pailie5.scientific_methods_v376 import propose_study


def _registry():
    return {"questions": [
        {"id": "Q-weak_structured_generalization", "kind": "weak_structured_generalization",
         "status": "needs_new_method", "planning_priority": 5.675,
         "evidence": [{"cycle_number": 10, "case": "difference_squares", "holdout_accuracy": 0.375}],
         "hypotheses": [
             {"id": "H-weak_structured_generalization-structural_capacity", "falsified_by": "non-improvement"},
             {"id": "H-weak_structured_generalization-search_instability", "falsified_by": "no benefit"},
         ]},
        {"id":"Q-frontier_unresolved_structure", "kind":"frontier_unresolved_structure",
         "status":"open", "planning_priority":0.5,"evidence":[],"hypotheses":[]},
    ]}


def test_methods_change_one_operational_dimension_each():
    seen = []
    history = []
    for n in (1,2,3):
        p = propose_study(_registry(), history, n, 37601, 120, 4)
        seen.append(p["method"])
        assert p["baseline"]["train_cells"] == 60
        assert p["baseline"]["holdout_cells"] == 20
        assert p["baseline"]["evaluation_budget"] == 120
        assert p["baseline"]["max_nodes"] == 11
        assert p["challenger"] != p["baseline"]
        assert sum(p["cost_budget_by_arm"].values()) <= 360
        assert p["production_enabled"] is False
        assert p["test_labels_hidden_from_fit"] is True
        assert p["confirmatory_pvalue_permitted"] is False
        history.append({"method":p["method"], "holdout_delta":0.0})
    assert set(seen) == {"more_training", "more_search", "richer_grammar"}


def test_mandatory_independent_random_control_at_fourth():
    history = [{"method":m,"holdout_delta":0.04} for m in ("more_training","more_search","richer_grammar")]
    p=propose_study(_registry(),history,4,37601,120,4)
    assert p["mandatory_null_control"] is True
    assert p["case"].startswith("iid_")
    assert p["question_id"] == "Q-periodic_null_control"
    assert p["study_number"] == 4


def test_method_selection_uses_new_seed_and_unresolved_prior_problem():
    p=propose_study(_registry(), [], 1, 37601, 120, 4)
    q=propose_study(_registry(), [{"method":p["method"]}], 2, 37601, 120, 4)
    assert p["case"] == "difference_squares"
    assert p["question_id"] == "Q-weak_structured_generalization"
    assert p["seed"] != q["seed"]
    assert p["question_id"] != "Q-frontier_unresolved_structure"
    assert p["scientific_conclusion"] == "UNRESOLVED"
    assert p["falsification_criterion"]


def test_invalid_method_inputs_rejected():
    for budget in (0, 2, 50001, True):
        with pytest.raises(ValueError):
            propose_study(_registry(), [], 1, 37601, budget, 4)
    with pytest.raises(ValueError):
        propose_study(_registry(), [], 0, 37601, 120, 4)
    with pytest.raises(ValueError):
        propose_study(_registry(), [], 1, 37601, 120, 1)


def test_plans_deterministic_independent_of_test_scores():
    a=propose_study(_registry(),[],1,37601,120,4)
    b=propose_study(_registry(),[],1,37601,120,4)
    assert a==b
    assert "holdout" not in json.dumps(a).lower() or a["baseline"]["holdout_cells"] == 20

from pailie5.scientific_runtime_v376 import run_method_studies


def _make_history(tmp_path):
    historical=tmp_path/'historical_v375'
    science=historical/'science'
    science.mkdir(parents=True)
    (science/'registry.json').write_text(json.dumps(_registry()),encoding='utf8')
    return historical


def test_method_runtime_freezes_both_arms_before_holdout(tmp_path,monkeypatch):
    import pailie5.scientific_runtime_v376 as runtime
    historical=_make_history(tmp_path)
    seen=[]
    real_fit=runtime.fit_budgeted
    real_evaluate=runtime.evaluate_frozen
    def fit_wrapper(training, config, mechanisms, **kw):
        assert len(training.rows) in (60,80)
        assert all((10*a+b) not in json.loads((tmp_path/'new'/'studies'/'00001'/'plan.json').read_text())['holdout_pair_ids'] for a,b,_ in training.rows)
        seen.append(('fit',len(training.rows)))
        return real_fit(training,config,mechanisms,**kw)
    def eval_wrapper(operator,held):
        assert (tmp_path/'new'/'studies'/'00001'/'fits'/'baseline'/'operator.json').is_file()
        assert (tmp_path/'new'/'studies'/'00001'/'fits'/'challenger'/'operator.json').is_file()
        seen.append(('eval',len(held.rows)))
        return real_evaluate(operator,held)
    monkeypatch.setattr(runtime,'fit_budgeted',fit_wrapper)
    monkeypatch.setattr(runtime,'evaluate_frozen',eval_wrapper)
    state=run_method_studies(tmp_path/'new',historical,studies=1,budget=100,seed=37601)
    assert state['completed_studies']==1
    assert [x[0] for x in seen]==['fit','fit','eval','eval']
    plan=json.loads((tmp_path/'new'/'studies'/'00001'/'plan.json').read_text())
    result=json.loads((tmp_path/'new'/'studies'/'00001'/'result.json').read_text())
    assert len(set(plan['holdout_pair_ids']))==20
    assert set(plan['holdout_pair_ids']).isdisjoint(plan['train_pair_order'])
    assert result['baseline']['holdout_count']==result['challenger']['holdout_count']==20
    assert result['scientific_conclusion']=='UNRESOLVED'
    assert result['production_enabled'] is False
    assert state['history'][0]['plan_sha256']==plan['sha256']


def test_method_runtime_studies_resume_preserves_previous_records(tmp_path):
    old=_make_history(tmp_path)
    out=tmp_path/'new'
    before=(old/'science'/'registry.json').read_bytes()
    s=run_method_studies(out,old,studies=2,budget=100,seed=37601)
    first=(out/'studies'/'00001'/'result.json').read_bytes()
    assert s['completed_studies']==2
    s=run_method_studies(out,old,studies=2,budget=100,seed=37601)
    assert s['completed_studies']==4
    assert (out/'studies'/'00001'/'result.json').read_bytes()==first
    assert (old/'science'/'registry.json').read_bytes()==before
    null=json.loads((out/'studies'/'00004'/'result.json').read_text())
    assert null['mandatory_null_control'] is True
    assert null['case'].startswith('iid_')


def test_method_runtime_rejects_tampered_plans_and_old_registry(tmp_path):
    old=_make_history(tmp_path)
    out=tmp_path/'new'
    run_method_studies(out,old,studies=1,budget=100,seed=37601)
    plan=out/'studies'/'00002'/'plan.json'
    plan.parent.mkdir(parents=True)
    plan.write_text(json.dumps({'sha256':'bogus','study_number':2}))
    with pytest.raises(ValueError,match='plan digest'):
        run_method_studies(out,old,studies=1,budget=100,seed=37601)
    assert not (out/'studies'/'00002'/'result.json').exists()
    plan.unlink()
    (old/'science'/'registry.json').write_text(json.dumps({'questions':[]}))
    with pytest.raises(ValueError,match='historical registry changed'):
        run_method_studies(out,old,studies=1,budget=100,seed=37601)


def test_method_runtime_refuses_active_lock_and_bad_budgets(tmp_path):
    old=_make_history(tmp_path)
    out=tmp_path/'new'
    out.mkdir()
    (out/'.run.lock').write_text('other')
    with pytest.raises(RuntimeError,match='already running'):
        run_method_studies(out,old,studies=1,budget=100,seed=37601)
    (out/'.run.lock').unlink()
    with pytest.raises(ValueError):
        run_method_studies(out,old,studies=99,budget=100,seed=37601)
    assert not (out/'state.json').exists()


def test_method_runtime_refuses_partial_frozen_artifact(tmp_path):
    old=_make_history(tmp_path)
    out=tmp_path/'new'
    run_method_studies(out,old,studies=1,budget=100,seed=37601)
    # Re-enter the second study while a compromised partial fit exists.
    artifact=out/'studies'/'00002'/'fits'/'baseline'/'fit.json'
    artifact.parent.mkdir(parents=True)
    artifact.write_text('{}')
    with pytest.raises(RuntimeError,match='incomplete frozen'):
        run_method_studies(out,old,studies=1,budget=100,seed=37601)
    assert not (out/'studies'/'00002'/'result.json').exists()


def test_completed_study_integrity_detects_tampering(tmp_path):
    old=_make_history(tmp_path)
    out=tmp_path/'new'
    run_method_studies(out,old,studies=1,budget=100,seed=37601)
    op=out/'studies'/'00001'/'fits'/'baseline'/'operator.json'
    op.write_text(op.read_text().replace('"production_enabled": false', '"production_enabled": true'))
    with pytest.raises(ValueError,match='frozen operator|artifact integrity'):
        run_method_studies(out,old,studies=1,budget=100,seed=37601)


def test_completed_study_result_detects_tampering(tmp_path):
    old=_make_history(tmp_path)
    out=tmp_path/'new'
    run_method_studies(out,old,studies=1,budget=100,seed=37601)
    result=out/'studies'/'00001'/'result.json'
    record=json.loads(result.read_text())
    record['holdout_delta']=0.99
    result.write_text(json.dumps(record))
    with pytest.raises(ValueError,match='result digest'):
        run_method_studies(out,old,studies=1,budget=100,seed=37601)


def test_scientific_method_cli_runs_once(tmp_path):
    import subprocess,sys
    old=_make_history(tmp_path)
    cli=Path(__file__).resolve().parents[1]/'research_methods_v376.py'
    p=subprocess.run([sys.executable,str(cli),'--output',str(tmp_path/'new'),
                      '--historical',str(old),'--studies','1','--budget','100'],
                      capture_output=True,text=True,timeout=30)
    assert p.returncode==0,p.stderr
    receipt=json.loads(p.stdout)
    assert receipt['total_method_studies']==1
    assert receipt['production_enabled'] is False
    assert receipt['background_running'] is False


def test_after_three_nonimproving_methods_researcher_synthesizes_sampling_method():
    history=[{'method':m,'holdout_delta':0.0,'mandatory_null_control':False}
             for m in ('more_training','richer_grammar','more_search')]
    history.append({'method':'more_training','holdout_delta':-.1,'mandatory_null_control':True})
    plan=propose_study(_registry(),history,5,37601,100,4)
    assert plan['method']=='balanced_sampling'
    assert plan['challenger']['train_cells']==plan['baseline']['train_cells']==60
    assert plan['challenger']['sampling']=='balanced'
    assert plan['baseline']['sampling']=='chronological_random'
    assert plan['source_failure']=='three_prior_method_classes_not_improving'


def test_balanced_sampler_frozen_before_truth_access(tmp_path):
    old=_make_history(tmp_path)
    out=tmp_path/'new'
    state=run_method_studies(out,old,studies=5,budget=100,seed=37601)
    assert state['completed_studies']==5
    plan=json.loads((out/'studies'/'00005'/'plan.json').read_text())
    assert plan['method']=='balanced_sampling'
    ids=plan['challenger_pair_ids']
    assert len(ids)==len(set(ids))==60
    assert set(ids)<=set(plan['train_pair_order'])
    assert not set(ids)&set(plan['holdout_pair_ids'])
    assert {i//10 for i in ids}==set(range(10))
    assert {i%10 for i in ids}==set(range(10))
    assert any(q['id']=='Q-method_family_nonimprovement' for q in state['emergent_questions'])
    result=json.loads((out/'studies'/'00005'/'result.json').read_text())
    assert result['baseline']['holdout_count']==result['challenger']['holdout_count']==20
    assert result['scientific_conclusion']=='UNRESOLVED'


def test_exhausted_sampling_method_changes_target_family_and_search_bias():
    h=[{'method':m,'holdout_delta':0,'mandatory_null_control':False} for m in
       ('more_training','richer_grammar','more_search')]
    h.append({'method':'more_training','holdout_delta':-.1,'mandatory_null_control':True})
    h.append({'method':'balanced_sampling','holdout_delta':0,'mandatory_null_control':False})
    h.append({'method':'richer_grammar','holdout_delta':0,'mandatory_null_control':False})
    p=propose_study(_registry(),h,7,37601,120,4)
    assert p['method']=='cross_family_replication'
    assert p['case']!='difference_squares'
    assert p['baseline']['guided'] is True
    assert p['challenger']['guided'] is False
    assert p['source_failure']=='exhausted_training_capacity_and_sampling_methods'


def test_cross_family_method_evaluates_without_test_leakage(tmp_path):
    import numpy as np
    from pailie5.scientific_runtime_v376 import _train_and_freeze
    history=[{'method':m,'holdout_delta':0,'mandatory_null_control':False} for m in
             ('more_training','richer_grammar','more_search')]
    history.append({'method':'more_training','holdout_delta':-.1,'mandatory_null_control':True})
    history.append({'method':'balanced_sampling','holdout_delta':0,'mandatory_null_control':False})
    history.append({'method':'richer_grammar','holdout_delta':0,'mandatory_null_control':False})
    plan=propose_study(_registry(),history,7,37601,100,4)
    order=np.random.default_rng(31).permutation(100).tolist()
    plan['train_pair_order']=order[:80]
    plan['holdout_pair_ids']=order[80:]
    assert plan['method']=='cross_family_replication'
    a,b=_train_and_freeze(tmp_path,plan)
    assert a['holdout_count']==b['holdout_count']==20
    assert a['common_holdout_fingerprint']==b['common_holdout_fingerprint']
    assert set(a['training_pair_ids']).isdisjoint(plan['holdout_pair_ids'])
    assert set(b['training_pair_ids']).isdisjoint(plan['holdout_pair_ids'])
    assert a['operator_id'] and b['operator_id']


def test_v376_package_version_matches_python_and_docs():
    import tomllib
    import pailie5
    package=Path(__file__).resolve().parents[1]
    metadata=tomllib.loads((package/'pyproject.toml').read_text(encoding='utf8'))
    assert metadata['project']['version']==pailie5.__version__=='3.7.6'


def test_exhausted_method_library_stops_instead_of_repeating_blindly():
    methods=["more_training","richer_grammar","more_search","more_training",
             "balanced_sampling","cross_family_replication","cross_family_replication",
             "more_training","more_search"]
    history=[{'method':m,'holdout_delta':0,'mandatory_null_control':i in (4,8)}
             for i,m in enumerate(methods,1)]
    with pytest.raises(ValueError,match='method library exhausted'):
        propose_study(_registry(),history,10,37601,120,4)


def test_science_registry_raises_new_primitive_problem_after_methods_fail():
    from pailie5.scientific_runtime_v376 import _science_questions_from_history
    ms=('more_training','richer_grammar','more_search','balanced_sampling','cross_family_replication','cross_family_replication')
    history=[{'study_number':i,'method':m,'holdout_delta':0,'mandatory_null_control':False}
             for i,m in enumerate(ms,1)]
    questions=_science_questions_from_history(history)
    assert any(q['id']=='Q-new_primitive_needed' and q['status']=='needs_new_method' for q in questions)
    assert all(q['scientific_conclusion']=='UNRESOLVED' for q in questions)


def test_cross_family_design_requires_two_fresh_targets_before_retirement():
    h=[{'method':m,'holdout_delta':0,'mandatory_null_control':False}
       for m in ('more_training','richer_grammar','more_search')]
    h.append({'method':'more_training','holdout_delta':0,'mandatory_null_control':True})
    h.append({'method':'balanced_sampling','holdout_delta':0,'mandatory_null_control':False})
    p6=propose_study(_registry(),h,6,37601,100,4)
    h.append({'method':p6['method'],'case':p6['case'],'holdout_delta':0,'mandatory_null_control':False})
    p7=propose_study(_registry(),h,7,37601,100,4)
    assert p6['method']==p7['method']=='cross_family_replication'
    assert p6['case']!=p7['case']
    assert p6['seed']!=p7['seed']
