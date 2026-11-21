import json
from pathlib import Path
from research_v19 import main
from pailie5.ability_lab_v19 import AbilityLab

def test_supervised_research_to_algorithm_ability_end_to_end(tmp_path, capsys):
    fixture=tmp_path/'papers.json'
    fixture.write_text(json.dumps([{
        'key':'synthetic-paper-v19','source':'arxiv','title':'Sequential testing and calibration',
        'abstract':'Synthetic research fixture on sequential model validation.',
        'url':'https://arxiv.org/abs/synthetic','date':'2026-10-01',
        'topic':'sequential testing'}]),encoding='utf8')
    args=['--lab-db',str(tmp_path/'ability.sqlite'),'--goal','cross_position',
          '--limit','1','--cycle-key','week-test-1','--verified-archive',
          '--db',str(tmp_path/'supervisor.sqlite'),'--papers-db',str(tmp_path/'papers.sqlite'),
          '--archive',str(tmp_path/'official-archive'),'once','--offline-fixture',str(fixture)]
    assert main(args)==0
    out=capsys.readouterr().out
    assert 'NOT_AUTOMATIC' in out and 'v19_ability_lab' in out
    with AbilityLab(tmp_path/'ability.sqlite') as lab:
        assert lab.latest()['total']==1
    assert main(args)==0
    with AbilityLab(tmp_path/'ability.sqlite') as lab:
        assert lab.latest()['total']==1
