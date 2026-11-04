"""No generated code is executed in process; executor is injected test double."""
from __future__ import annotations
import json
import re
import sqlite3
import pytest
from autoresearch.collaboration_v22 import (
    FAMILIES, V22ResearchLab, _source_pair, suggest_family, counterexample_cases,
    _compare, _run_container, _validate_cases,
)
from autoresearch.paper_factory_v20 import offline_blueprint

TEXT = '''Empirical frequency model for sequential digits. Statistical methods must
be evaluated using independent data and fixed probability baselines. Algorithms
from research papers do not imply that lottery outcomes can be predicted.'''


@pytest.fixture
def context(tmp_path):
    with sqlite3.connect(tmp_path/'test.db') as db:
        lab=V22ResearchLab(db)
        lab.council.paper.documents.add_document('paper-v22','Frequency modeling of discrete symbols',TEXT,kind='local',url='local:test')
        paper=lab.council.paper.documents.get_document('paper-v22')
        b=lab.council.paper.register_blueprint('paper-v22',offline_blueprint(paper))
        project=lab.council.create(b['blueprint_id'],goal='Examine reproducibility of numeric-frequency candidate scores',budget=10,periods=3)
        yield lab,project['project_id']


def oracle(family,history,numbers):
    if family=='digit_sum':return [sum(map(int,n)) for n in numbers]
    if family=='span':return [max(map(int,n))-min(map(int,n)) for n in numbers]
    if family=='adjacent_energy':return [sum(abs(int(n[j])-int(n[j-1])) for j in range(1,5)) for n in numbers]
    if family=='lag_overlap':return [sum(n[j]==history[-1][j] for j in range(5)) if history else 0 for n in numbers]
    if family=='digit_frequency':
        counts=[[1]*10 for _ in range(5)]
        for n in history[-120:]:
            for j in range(5):counts[j][int(n[j])]+=1
        return [sum(counts[j][int(n[j])] for j in range(5)) for n in numbers]
    raise AssertionError(family)


def fake_executor(source,cases,language):
    family=next(f for f in FAMILIES if source in _source_pair(f))
    return [oracle(family,case['history'],case['candidates']) for case in cases]


def test_family_compiler_has_three_structures_and_valid_python():
    from autoresearch.python_lab_v08 import inspect_python_source
    for family in FAMILIES:
        p,r,j=_source_pair(family)
        assert inspect_python_source(p)['function']=='score_batch'
        assert inspect_python_source(r)['function']=='score_batch'
        assert 'scoreBatch(' in j
        assert p!=r
        assert re.search('require\\(|process\\.',j) is None


def test_generate_plan_and_resume(context):
    lab,pid=context
    result=lab.generate(pid)
    assert result['created'] and result['family']=='digit_frequency'
    assert result['python_sources']==2 and result['node_sources']==1
    assert not result['automatic_approval']
    assert not lab.generate(pid)['created']
    assert lab.council._artifact(pid,'adversarial_review')['checks_implemented_as_tests'] is False
    assert lab.status(pid)['generated'] and not lab.status(pid)['evaluated']
    with pytest.raises(ValueError,match='不可变更'):
        lab.generate(pid,family='span')
    assert not lab.council.state(pid)['algorithm_auto_promotion']


def test_sandbox_gate_and_faked_cross_runtime(context):
    lab,pid=context
    lab.generate(pid)
    with pytest.raises(PermissionError):lab.evaluate(pid,executor=fake_executor)
    result=lab.evaluate(pid,allow_docker=True,executor=fake_executor,complete_domain=True)
    assert result['engineering_pass']
    assert result['compared_score_values']==102256
    assert result['cases']==7
    assert result['checks']['spec_conformance']['equal']
    assert result['checks']['python_node']['equal']
    assert result['checks']['python_pair']['equal']
    assert result['checks']['candidate_permutation']
    assert result['fair_draw_top100_chance']==0.001
    assert not result['esse_auto_activate']
    assert lab.status(pid)['evaluated']
    with pytest.raises(ValueError,match='封存'):
        lab.evaluate(pid,allow_docker=True,executor=fake_executor)


def test_failing_cross_language_fails_gate(context):
    lab,pid=context
    lab.generate(pid,family='lag_overlap')
    def broken(source,cases,language):
        out=fake_executor(source,cases,language)
        if language=='node':out[0][0]+=1
        return out
    result=lab.evaluate(pid,allow_docker=True,executor=broken)
    assert not result['engineering_pass']
    assert result['checks']['python_node']['mismatches']==1


def test_refuse_wrong_cases_and_untrusted_node():
    cases,_=counterexample_cases()
    _validate_cases(cases)
    bad=[dict(history=[],candidates=['1234'])]
    with pytest.raises(ValueError):_validate_cases(bad)
    with pytest.raises(ValueError):_source_pair('original_paper_magic_method')
    with pytest.raises(ValueError):_compare([[1]],[[1,2]],[{'candidates':['00000']}])
    # Real Docker path must not execute arbitrary JS, even if docker is installed.
    # When docker is absent it rejects before use of subprocess.
    import shutil
    if shutil.which('docker') is None:
        with pytest.raises(RuntimeError,match='Docker'):
            _run_container('function evil(){}',cases[:1],'node')



def test_unknown_method_does_not_forge_new_algorithm(context):
    lab,pid=context
    assert suggest_family('Transformer embeddings and generic neural networks') is None
    assert suggest_family('first-order Markov model')=='lag_overlap'
    assert lab.auto_generate(maximum=2)['created']==1
    assert lab.auto_generate(maximum=2)['created']==0
    assert not lab.status(pid)['automatic_release']


def test_immutable_generated_and_report_integrity(context):
    lab,pid=context
    lab.generate(pid)
    with pytest.raises(sqlite3.DatabaseError):lab.db.execute('UPDATE v22_generated SET family="span"')
    lab.evaluate(pid,allow_docker=True,executor=fake_executor)
    with pytest.raises(sqlite3.DatabaseError):lab.db.execute('DELETE FROM v22_evaluations')
    lab.db.execute('DROP TRIGGER v22_evaluations_no_update')
    lab.db.execute('UPDATE v22_evaluations SET report_json="{}"')
    with pytest.raises(ValueError,match='完整性'):
        lab.status(pid)


def test_permutation_and_leading_zero_controls(context):
    cases,meta=counterexample_cases()
    assert meta['permutation']==[1,4]
    assert cases[1]['candidates']==list(reversed(cases[4]['candidates']))
    assert any(n.startswith('0') for n in cases[5]['candidates'])
    assert len(cases[1]['history'])==3
    for family in FAMILIES:
        scores=[oracle(family,c['history'],c['candidates']) for c in cases]
        normal=dict(zip(cases[1]['candidates'],scores[1]))
        assert all(normal[n]==score for n,score in zip(cases[4]['candidates'],scores[4]))


def test_all_three_matching_bad_scores_do_not_pass_spec(context):
    lab,pid=context
    lab.generate(pid)
    def wrong_consensus(source,cases,language):
        return [[0 for _ in c['candidates']] for c in cases]
    report=lab.evaluate(pid,allow_docker=True,executor=wrong_consensus)
    assert report['checks']['python_pair']['equal']
    assert report['checks']['python_node']['equal']
    assert not report['checks']['spec_conformance']['equal']
    assert not report['engineering_pass']
