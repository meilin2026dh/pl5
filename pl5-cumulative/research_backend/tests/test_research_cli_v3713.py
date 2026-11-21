"""End-to-end CLI tests through Python interpreter, not mocks."""
from pathlib import Path
import json
import subprocess
import sys

SCRIPT = Path(__file__).resolve().parents[1] / 'research_v3713.py'


def _run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str,args)], capture_output=True, text=True)


def test_cli_generate_and_select_with_machine_audit(tmp_path):
    result = _run('codebook','--strength',2,'--budget',100,'--min-distance',3,'--output',tmp_path)
    assert result.returncode==0, result.stderr
    report=json.loads((tmp_path/'audit.json').read_text())
    assert report['codebook']['retained_count']==100
    assert report['codebook']['min_positional_distance']>=3
    assert report['source_cover']['coverage_fraction']==1
    assert report['codebook']['coverage']['coverage_fraction'] <= 1
    assert (tmp_path/'codebook.txt').read_text().count('\n') == 100


def test_cli_frozen_conformal_calibration_on_synthetic_data(tmp_path):
    file=tmp_path/'ranks.json'
    file.write_text(json.dumps({
        'model_sha256':'c'*64,'training_end_issue':'100',
        'alpha':0.1,'calibration_issues':[str(i) for i in range(101,200)],
        'calibration_ranks':list(range(1000,100000,1000)),
        'test_issues':['300','301'],'test_ranks':[200,98000],
        'input_type':'synthetic_demo'
    }))
    result=_run('conformal','--input',file,'--output',tmp_path/'out.json')
    assert result.returncode==0, result.stderr
    report=json.loads((tmp_path/'out.json').read_text())
    assert report['calibration']['cutoff']==90000
    assert report['holdout']['misses']==1
    assert report['dataset_provenance']=='synthetic_demo'
    assert report['predictive_advantage']=='NOT_ESTABLISHED'


def test_cli_invalid_file_fails_without_fabricated_result(tmp_path):
    out=tmp_path/'out.json'
    result=_run('conformal','--input',tmp_path/'missing.json','--output',out)
    assert result.returncode != 0
    assert not out.exists()


def test_cli_fixed_filter_outputs_risk_not_conformal_guarantee(tmp_path):
    payload={'training_end_issue':'100','precommitted':True,
             'observations':[['101','00001'],['102','00002']],
             'kept_by_issue':{'101':['00001','11111'],'102':['22222','33333']},
             'input_type':'synthetic_demo'}
    inp=tmp_path/'filter.json'
    inp.write_text(json.dumps(payload))
    result=_run('fixed-filter','--input',inp,'--output',tmp_path/'risk.json')
    assert result.returncode==0,result.stderr
    report=json.loads((tmp_path/'risk.json').read_text())
    assert report['misses']==1
    assert report['conformal_guarantee'] is False


def test_cli_dynamic_budget_uses_financial_cap_as_hard_ceiling(tmp_path):
    payload = {
        'training_end_issue':'100','model_sha256':'f'*64,'scale_model_sha256':'a'*64,
        'alpha':0.2,'calibration_issues':[str(i) for i in range(101,110)],
        'calibration_ranks':list(range(1000,10000,1000)),
        'calibration_difficulty_scales':[1]*9,
        'future_issues':[{'issue':'200','difficulty_scale':2,'affordable_max_tickets':10000},
                         {'issue':'201','difficulty_scale':1,'affordable_max_tickets':12000}],
        'holdout':[{'issue':'200','difficulty_scale':2,'affordable_max_tickets':10000,'actual_rank':12000},
                   {'issue':'201','difficulty_scale':1,'affordable_max_tickets':12000,'actual_rank':7000}],
        'input_type':'synthetic_demo'
    }
    data=tmp_path/'in.json'
    data.write_text(json.dumps(payload))
    out=tmp_path/'dynamic.json'
    result=_run('dynamic-budget','--input',data,'--output',out)
    assert result.returncode==0,result.stderr
    report=json.loads(out.read_text())
    assert report['daily_budgets'][0]['required_tickets']==16000
    assert report['daily_budgets'][0]['status']=='coverage_target_unaffordable'
    assert report['daily_budgets'][0]['purchasable_tickets']==10000
    assert report['daily_budgets'][1]['required_tickets']==8000
    assert report['holdout']['calibrated_hits']==2
    assert report['holdout']['actually_purchasable_hits']==1


def test_cli_dynamic_budget_does_not_write_invalid_request(tmp_path):
    file=tmp_path/'bad.json'
    file.write_text(json.dumps({'alpha':0.1}))
    out=tmp_path/'out.json'
    result=_run('dynamic-budget','--input',file,'--output',out)
    assert result.returncode!=0
    assert not out.exists()
