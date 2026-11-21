"""V3724 regression: predeclared budgets, separation, tampering, nulls."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pytest

from pailie5.grammar_discovery_v3724 import (
    VERSION,FEATURES,MAX_EVALS,_proposals,_table,commit_holdout,fit,freeze,evaluate,_read_checked
)
from pailie5.structure_search_v372 import CellDataset


def data(kind='composite',seed=372404):
    a,b=np.indices((10,10))
    if kind=='composite':table=(a*b+a+4)%10
    elif kind=='negative':table=np.random.default_rng(seed).integers(0,10,(10,10))
    elif kind=='unary':table=(a+b+4)%10
    else:raise ValueError('unknown case')
    shuffled=np.random.default_rng(seed).permutation(100)
    def make(indices):return CellDataset(tuple((int(i//10),int(i%10),int(table.flat[i])) for i in indices))
    return make(shuffled[:48]),make(shuffled[48:64]),make(shuffled[64:])


def test_equal_candidate_budget_and_grammar_diversity():
    bas=list(__import__('itertools').islice(_proposals('baseline'),MAX_EVALS))
    new=list(__import__('itertools').islice(_proposals('expanded'),MAX_EVALS))
    assert len(bas)==len(new)==2200
    assert all(s1==s2 and np.array_equal(t1,t2) for (s1,t1),(s2,t2) in zip(bas[:400],new[:400]))
    assert all(s['grammar']!='binary_composition' for s,_ in bas)
    assert any(s['grammar']=='binary_composition' for s,_ in new)
    assert len({json.dumps(s,sort_keys=True) for s,_ in new})==MAX_EVALS


def test_program_eval_unsafe_rejected():
    with pytest.raises(ValueError):_table({'grammar':'eval','src':'__import__("os")'})
    with pytest.raises(ValueError):_table({'grammar':'binary_composition','left':'a','right':'a','operation':'add','shift':0})
    with pytest.raises(ValueError):_table({'grammar':'unary_affine','feature':'a','shift':0,'scale':True})
    with pytest.raises(ValueError):_table({'grammar':'unary_poly2','feature':'a','coefficients':[1,2,10]})


def test_new_composition_passes_but_unary_baseline_rejects(tmp_path):
    train,val,hold=data()
    for arm in ('baseline','expanded'):
        root=tmp_path/arm
        f=fit(train,root,arm=arm)
        freeze_result=freeze(root,val)
        ev=evaluate(root,hold)
        assert f['candidate_evaluations']==2200
        assert f['training_only'] and freeze_result['test_labels_seen'] is False
        if arm=='expanded':
            assert f['grammar_expansion_triggered'] and f['base_stage_errors']>0
            assert freeze_result['status']=='FROZEN' and ev['test_errors']==0
        else:
            assert freeze_result['status']=='ABSTAIN' and ev['test_errors'] is None


def test_known_unary_control_both_pass(tmp_path):
    train,val,hold=data(kind='unary')
    for arm in ('baseline','expanded'):
        root=tmp_path/arm
        assert fit(train,root,arm=arm)['best_training_errors']==0
        assert freeze(root,val)['status']=='FROZEN'
        assert evaluate(root,hold)['test_errors']==0


def test_random_null_abstains(tmp_path):
    train,val,hold=data(kind='negative')
    fit(train,tmp_path,arm='expanded')
    assert freeze(tmp_path,val)['status']=='ABSTAIN'
    assert evaluate(tmp_path,hold)['test_errors'] is None


def test_precommit_required_to_reveal_and_single_evaluation(tmp_path):
    train,val,hold=data()
    nonce='v3724-setter-secret-nonce-0123456789'
    digest=commit_holdout(hold,nonce)
    f=fit(train,tmp_path,arm='expanded',holdout_digest=digest)
    assert f['holdout_commitment']==digest
    freeze(tmp_path,val)
    with pytest.raises(ValueError,match='commitment'):
        evaluate(tmp_path,hold)
    with pytest.raises(ValueError,match='commitment'):
        evaluate(tmp_path,hold,nonce='wrongnonce-with-adequate-length')
    assert evaluate(tmp_path,hold,nonce=nonce)['commitment_verified']
    with pytest.raises(FileExistsError):evaluate(tmp_path,hold,nonce=nonce)


def test_tampered_holdout_rejected(tmp_path):
    train,val,hold=data()
    nonce='another-valid-secret-holdout-nonce'
    fit(train,tmp_path,arm='expanded',holdout_digest=commit_holdout(hold,nonce))
    freeze(tmp_path,val)
    rows=list(hold.rows);a,b,v=rows[0];rows[0]=(a,b,(v+1)%10)
    with pytest.raises(ValueError,match='commitment'):
        evaluate(tmp_path,CellDataset(tuple(rows)),nonce=nonce)
    assert not (tmp_path/'evaluation.json').exists()


def test_partition_overlap_detected(tmp_path):
    train,val,hold=data()
    fit(train,tmp_path,arm='expanded')
    with pytest.raises(ValueError,match='overlap'):
        freeze(tmp_path,train)
    freeze(tmp_path,val)
    with pytest.raises(ValueError,match='overlap'):
        evaluate(tmp_path,train)


def test_signed_fit_tamper_detected(tmp_path):
    train,val,hold=data()
    fit(train,tmp_path,arm='expanded')
    f=tmp_path/'fit.json';content=f.read_text();f.write_text(content.replace('"candidate_budget": 2200','"candidate_budget": 2201'))
    with pytest.raises(ValueError,match='checksum'):freeze(tmp_path,val)


def test_cannot_modify_frozen_selection(tmp_path):
    train,val,hold=data()
    fit(train,tmp_path,arm='expanded');freeze(tmp_path,val)
    fp=tmp_path/'freeze.json';r=json.loads(fp.read_text());r['selected']=None
    fp.write_text(json.dumps(r))
    with pytest.raises(ValueError,match='checksum'):evaluate(tmp_path,hold)


def test_no_repeated_fit_or_freeze(tmp_path):
    train,val,hold=data();fit(train,tmp_path,arm='expanded')
    with pytest.raises(FileExistsError):fit(train,tmp_path,arm='expanded')
    freeze(tmp_path,val)
    with pytest.raises(FileExistsError):freeze(tmp_path,val)


def test_replay_identical_logical_evidence(tmp_path):
    train,val,hold=data()
    results=[]
    for name in ('first','second'):
        root=tmp_path/name
        f=fit(train,root,arm='expanded');fr=freeze(root,val);ev=evaluate(root,hold)
        # Wall-clock is measured, deliberately excluded from deterministic evidence check.
        f.pop('wall_ns_fit')
        f.pop('integrity_sha256')
        fr.pop('fit_sha256')
        fr.pop('integrity_sha256')
        ev.pop('freeze_sha256')
        ev.pop('integrity_sha256')
        results.append((f,fr,ev))
    assert results[0]==results[1]


def test_bad_digest_and_nonce_rejected(tmp_path):
    train,val,hold=data()
    with pytest.raises(ValueError):commit_holdout(hold,'short')
    with pytest.raises(ValueError):fit(train,tmp_path,arm='expanded',holdout_digest='invalid')
