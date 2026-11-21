"""Tests for V3.0 symbolic formula discovery and conservative registration."""
import json
import hashlib
import sqlite3
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from pailie5.symbolic_operators_v30 import (
    eval_expr, search_formula, certify_formula, reconstruct_table,
    structural_summary, analyze_primitives, register_symbolic
)


def _rand_history(n=260, seed=27):
    rng=np.random.default_rng(seed)
    return [''.join(map(str,row)) for row in rng.integers(0,10,(n,5))]

@pytest.mark.parametrize('k',[3,4])
def test_symbolic_discovers_arithmetic_formula_and_certifies(k):
    a,b=np.indices((10,10));truth=(a+b)%k
    cert=search_formula(truth,max_nodes=5)
    assert cert.status=='exact_symbolic'
    assert cert.whole_table_errors==0 and cert.unseen_pair_errors==0
    assert cert.compressed_bits<cert.raw_table_bits
    assert cert.input_pairs_train==70 and cert.input_pairs_unseen==30
    assert certify_formula(cert,truth)
    assert np.array_equal(reconstruct_table(cert),truth)
    assert cert.formula and 'mod' in cert.formula

@pytest.mark.parametrize('seed',[11,12])
def test_unstructured_random_table_favors_full_lookup(seed):
    rng=np.random.default_rng(seed)
    table=rng.integers(0,4,(10,10),dtype=np.uint8)
    # Guarantee complete output alphabet.
    table.ravel()[:4]=np.arange(4)
    cert=search_formula(table,seed=seed,max_nodes=5)
    assert cert.status=='raw_table_preferred'
    with pytest.raises(ValueError,match='不得冒充'):
        reconstruct_table(cert)

@pytest.mark.parametrize('bad',[
    np.ones((5,5),dtype=np.uint8),
    np.full((10,10),2,dtype=np.uint8),
    np.zeros((10,10),dtype=float)
])
def test_bad_input_rejected(bad):
    with pytest.raises(ValueError):search_formula(bad)


def test_ast_is_safe_and_no_dynamic_eval():
    with pytest.raises(ValueError):eval_expr(('call', '__import__'))
    with pytest.raises(ValueError):eval_expr(('binary','evil',('a',),('b',)))
    with pytest.raises(ValueError):eval_expr(('const',999))


def test_frozen_table_tamper_detected():
    a,b=np.indices((10,10));table=(a+b)%3
    cert=search_formula(table)
    bad=table.copy();bad[0,0]=1
    with pytest.raises(ValueError,match='指纹'):certify_formula(cert,bad)


def test_split_reproducibility():
    a,b=np.indices((10,10));t=(a*b)%4
    x=search_formula(t,seed=345,beam_width=20)
    y=search_formula(t,seed=345,beam_width=20)
    assert x==y


def test_nonnegative_histograms_and_class_invariance():
    a,b=np.indices((10,10));t=(a+b)%3
    info=structural_summary(t)
    assert len(info['class_95pct_energy_ranks'])==3
    assert sum(info['class_histogram'])==100
    assert all(1<=v<=10 for v in info['class_95pct_energy_ranks'])


def test_history_registration_append_only_and_no_promotion(tmp_path):
    hist=_rand_history()
    db=tmp_path/'symbolic.sqlite'
    rep=analyze_primitives(hist,maximum=2,beam_width=12,max_nodes=3,registry=db)
    assert len(rep['items'])==2
    assert rep['no_false_promotion']
    assert all(i['research_only'] for i in rep['items'])
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT COUNT(*) FROM v30_symbolic').fetchone()[0]==2
        assert conn.execute('SELECT COUNT(*) FROM v30_symbolic WHERE status="research_only"').fetchone()[0]==2
    assert register_symbolic(rep,db)==0


def test_heldout_draw_changes_cannot_change_formula_selection():
    h=_rand_history()
    a=analyze_primitives(h,maximum=2,beam_width=10,max_nodes=3)
    modified=h[:-50]+['99999']*50
    b=analyze_primitives(modified,maximum=2,beam_width=10,max_nodes=3)
    assert a['items']==b['items']
    assert a['history_sha256']!=b['history_sha256']


def test_cli_formula_demo(tmp_path):
    out=tmp_path/'demo.json'
    root=Path(__file__).resolve().parents[1]
    cp=subprocess.run([sys.executable,'research_v30.py','formula-demo','--report',str(out)],cwd=root,capture_output=True,text=True,timeout=30)
    assert cp.returncode==0,cp.stderr
    data=json.loads(out.read_text('utf-8'))
    assert data['certified'] and data['symbolic']['status']=='exact_symbolic'

@pytest.mark.parametrize('operation',['add','sub','mul','absdiff','xor','min','max','equal','less','gcd'])
def test_independent_scalar_interpreter_matches_vector(operation):
    from pailie5.symbolic_operators_v30 import eval_expr_scalar
    expression=('binary',operation,('a',),('b',))
    vector=eval_expr(expression).reshape(10,10)
    for a in range(10):
        for b in range(10):
            assert int(vector[a,b])==eval_expr_scalar(expression,a,b)
