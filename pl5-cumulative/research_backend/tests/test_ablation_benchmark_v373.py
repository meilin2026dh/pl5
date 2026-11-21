import importlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import pytest

def b(): return importlib.import_module('pailie5.ablation_benchmark_v373')
def s(): return importlib.import_module('pailie5.ablation_statistics_v373')

def test_benchmark_module_exists():
    assert importlib.util.find_spec('pailie5.ablation_benchmark_v373') is not None

def test_statistics_module_exists():
    assert importlib.util.find_spec('pailie5.ablation_statistics_v373') is not None

def test_exact_signflip_reference_examples():
    assert s().exact_sign_flip([1,1,1,1]) == pytest.approx(0.125)
    assert s().exact_sign_flip([1,-1]) == 1.0
    assert s().exact_sign_flip([0,0,0]) == 1.0

def test_holm_preserves_names_and_controls_family():
    assert s().holm_adjust({'c':.04,'a':.01,'b':.03}) == pytest.approx({'a':.03,'b':.06,'c':.06})
    assert s().holm_adjust({'x':1.0,'y':0.0})=={'x':1.0,'y':0.0}

@pytest.mark.parametrize('values',[[],[float('nan')],[float('inf')]])
def test_invalid_signflip_input(values):
    with pytest.raises(ValueError): s().exact_sign_flip(values)

@pytest.mark.parametrize('values',[{'x':-1},{'x':1.1},{'x':float('nan')}])
def test_invalid_holm_input(values):
    with pytest.raises(ValueError): s().holm_adjust(values)

def test_eight_structures_two_controls_and_six_arms():
    assert len(b().CASES)==10 and len(b().ARMS)==6
    assert sum(t['group']=='iid_control' for t in b().CASES.values())==2
    for case in b().CASES:
        truth=b().truth_table(case,37301)
        assert truth.shape==(10,10)
        a,h=b().split_table(truth,37301,case)
        assert len(a.rows)==60 and len(h.rows)==40
        assert not set(a.pairs)&set(h.pairs)
        assert a.fingerprint==b().split_table(truth,37301,case)[0].fingerprint

def test_warm_sources_are_frozen_and_no_target_is_an_exact_copy():
    bank,metadata=b().load_warm_bank()
    assert len(bank)==len(metadata)==4
    from pailie5.structure_ast_v372 import table
    for case,task in b().CASES.items():
        if task['group']=='iid_control': continue
        assert all(not np.array_equal(table(e),b().truth_table(case,37301)) for e in bank)

def test_synthetic_reference_tables_match_independent_scalar_interpreter():
    from pailie5.symbolic_operators_v30 import eval_expr_scalar
    for case,task in b().CASES.items():
        if task['group']=='iid_control': continue
        scalar=np.array([[eval_expr_scalar(task['expression'],a,c)%10 for c in range(10)] for a in range(10)])
        assert np.array_equal(scalar,b().truth_table(case,37301))

def test_smoke_run_protocol_frozen_and_budget_matched(tmp_path):
    dest=tmp_path/'run'
    result=b().run_suite(dest,seeds=(123,),cases=('shifted_bilinear','iid_a'),arms=('full','no_mutation'),budget=80)
    assert len(result['trials'])==4
    assert (dest/'protocol.json').is_file()
    assert all(x['evaluations']==80 and x['budget_matched'] for x in result['trials'])
    assert result['protocol_sha256']
    assert all((dest/x['operator_path']).exists() for x in result['trials'])
    assert all(x['production_enabled'] is False for x in result['trials'])
    assert result['protocol']['warm_start_cost_scope']=='destination_search_only; source_acquisition_excluded'
    with pytest.raises(FileExistsError):
        b().run_suite(dest,seeds=(123,),cases=('iid_a',),arms=('full',),budget=80)

def test_cli_help_and_bad_budget(tmp_path):
    root=Path(__file__).resolve().parents[1]
    help_=subprocess.run([sys.executable,str(root/'research_v373.py'),'--help'],capture_output=True,text=True)
    assert help_.returncode==0 and 'budget' in help_.stdout
    bad=subprocess.run([sys.executable,str(root/'research_v373.py'),'--output',str(tmp_path/'bad'),'--budget','0'],capture_output=True,text=True)
    assert bad.returncode!=0 and not (tmp_path/'bad').exists()
