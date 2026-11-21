from __future__ import annotations
import json
import pytest
from pailie5.data import load_csv, Draws
from pailie5.discovery import validate_spec, template_hypotheses, step_metrics
from pailie5.knowledge import KnowledgeBase, fingerprint, holdout_key
from pailie5.research_agent import ResearchAgent


def synthetic(n=180):
    return load_csv(('period,number\n'+''.join(f'{2026000+i},{(i*1337)%100000:05d}\n' for i in range(1,n+1))).encode())


def test_sources_idempotent_and_cross_check(tmp_path):
    kb=KnowledgeBase(tmp_path/'kb.sqlite')
    content=b'period,number\n2026001,01234\n2026002,00001\n'
    one=kb.import_csv(content,'official document manually checked')
    assert one.status=='imported' and one.inserted==2
    two=kb.import_csv(content,'same bytes')
    assert two.status=='unchanged' and two.inserted==0
    other=b'period,number\n2026002,00001\n2026003,99999\n'
    three=kb.import_csv(other,'second document')
    assert three.inserted==1
    assert len(kb.merged_draws().frame)==3
    with pytest.raises(ValueError,match='冲突'):
        kb.import_csv(b'period,number\n2026002,11111\n','bad source')
    assert len(kb.merged_draws().frame)==3
    assert len(kb.sources())==2
    kb.close()


def test_no_silent_zero_padding_in_research_db(tmp_path):
    kb=KnowledgeBase(tmp_path/'kb.sqlite')
    with pytest.raises(ValueError,match='5位'):
        kb.import_csv(b'period,number\n1,234\n','truncated')
    assert len(kb.sources())==0
    with pytest.raises(ValueError,match='演示数据'):
        kb.import_csv(b'period,number\n1,00001\n','demo',demo=True)
    kb.close()


def test_safe_dsl_rejects_code():
    for spec in [{'type':'exec','script':'rm -rf /'},
                 {'type':'recency','half_life':-1},
                 {'type':'positional','python':'exec("x")'}]:
        with pytest.raises(ValueError): validate_spec(spec)
    assert len(template_hypotheses())==5


def test_holdout_never_appears_in_development(tmp_path):
    base=synthetic(180)
    altframe=base.frame.copy()
    altframe.loc[179,'number']='99999'
    alt=Draws(altframe,tuple())
    a=ResearchAgent(base,KnowledgeBase(tmp_path/'a.sqlite'))
    b=ResearchAgent(alt,KnowledgeBase(tmp_path/'b.sqlite'))
    params={'count':1000,'window':100,'min_train':80,'dev_size':10,
            'holdout_size':10,'seed':7,'llm':False,'dev_alpha':0.01}
    s={'params':params}
    p=a.propose(s)
    da=a.develop({**s,**p})
    db=b.develop({**s,**p})
    assert da==db
    a.kb.close(); b.kb.close()


def test_one_time_lock_and_preregister_before_open(tmp_path,monkeypatch):
    kb=KnowledgeBase(tmp_path/'kb.sqlite')
    draws=synthetic(160)
    agent=ResearchAgent(draws,kb)
    actual=agent.open_holdout
    def guarded(state):
        existing=kb.get_experiment(state['lock_key'])
        assert existing is not None
        assert existing['status']=='sealed_pending'
        return actual(state)
    monkeypatch.setattr(agent,'open_holdout',guarded)
    report=agent.run(count=1000,dev_size=10,holdout_size=10,min_train=100,
                     window=100,seed=12,use_langgraph='off')
    assert report['experiment_id']==1
    assert report['holdout']['periods']==10
    assert kb.experiments()[0]['status']!='sealed_pending'
    with pytest.raises(ValueError,match='已经开封'):
        agent.run(count=2000,dev_size=10,holdout_size=10,min_train=100,
                  window=100,seed=99,use_langgraph='off')
    kb.close()


def test_fair_baseline_k_100000(tmp_path):
    kb=KnowledgeBase(tmp_path/'kb.sqlite')
    agent=ResearchAgent(synthetic(170),kb)
    report=agent.run(count=100000,dev_size=10,holdout_size=10,min_train=100,
                     window=100,use_langgraph='off')
    assert report['holdout']['hits']==10
    assert report['holdout']['theoretical_cover_rate']==1.0
    assert report['holdout']['binomial_p']==1.0
    kb.close()

def test_community_csv_normalization():
    from pailie5.sources import normalize_community_csv
    data='period,date,winningNumber\n'+''.join(f'{i},2026-01-01,{i%100000:05d}\n' for i in range(1,130))
    normalized=normalize_community_csv(data.encode())
    loaded=load_csv(normalized)
    assert len(loaded.frame)==129
    assert loaded.frame['number'].iat[0]=='00001'
    with pytest.raises(ValueError,match='非5位'):
        normalize_community_csv(data.replace('00001','1').encode())
    with pytest.raises(ValueError,match='上游包含重复期号'):
        normalize_community_csv(('period,date,winningNumber\n'+''.join('1,2026-01-01,00001\n' for i in range(101))).encode())

def test_safe_symbolic_program_synthesis():
    from pailie5.discovery import generated_blends, score_spec
    proposals=generated_blends(seed=25)
    assert proposals==generated_blends(seed=25)
    values=score_spec(synthetic(35).frame['number'].tolist(),proposals[0])
    assert len(values)==100000
    with pytest.raises(ValueError):
        validate_spec({'name':'evil','type':'blend','components':[{'type':'blend'}, {'type':'positional'}], 'weights':[1,1]})

def test_period_normalizes_five_and_seven_digit_formats(tmp_path):
    from pailie5.knowledge import canonical_period
    assert canonical_period('26271')=='2026271'
    assert canonical_period('2026271')=='2026271'
    kb=KnowledgeBase(tmp_path/'kb.sqlite')
    kb.import_csv(b'period,number\n26271,62246\n26272,01234\n','provincial official exported manually')
    receipt=kb.import_csv(b'period,number\n2026271,62246\n2026273,34567\n','another source')
    assert receipt.inserted==1
    assert kb.merged_draws().frame['period'].tolist()==['2026271','2026272','2026273']
    with pytest.raises(ValueError,match='冲突'):
        kb.import_csv(b'period,number\n2026272,99999\n','source disagreement')
    kb.close()
