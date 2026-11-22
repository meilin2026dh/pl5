import numpy as np
import pytest
from pailie5.data import load_csv
from pailie5.engine import select_numbers, score_candidates, evidence_gate
from pailie5.backtest import run_backtest


def data(n=160):
    rows = 'period,number\n' + ''.join(f'{j:04d},{j%100000:05d}\n' for j in range(1,n+1))
    return load_csv(rows.encode())


def test_preserve_leading_zeros_and_sort():
    ds = load_csv(b'period,number\n3,9\n1,00123\n2,00001\n')
    assert ds.frame['period'].tolist() == ['1','2','3']
    assert ds.frame['number'].tolist() == ['00123','00001','00009']
    assert any('左补零' in x for x in ds.warnings)


def test_duplicate_issue_rejected():
    with pytest.raises(ValueError,match='重复期号'):
        load_csv(b'period,number\n1,00001\n1,00002\n')


def test_bad_number_rejected():
    with pytest.raises(ValueError,match='不合法'):
        load_csv(b'period,number\n1,12-34\n')


def test_exact_count_reproducible():
    h = data(140).frame['number'].tolist()
    for model in ('positional','pairwise','ensemble','random'):
        a = select_numbers(h,count=1000,model=model,seed=12,use_gate=False)
        b = select_numbers(h,count=1000,model=model,seed=12,use_gate=False)
        assert len(a.numbers) == 1000
        assert np.array_equal(a.numbers,b.numbers)
        assert len(np.unique(a.numbers)) == 1000
        assert 0 <= a.numbers.min() < 100000 and a.numbers.max() < 100000


def test_no_history_lookahead_small_backtest():
    ds = data(160)
    bt = run_backtest(ds,count=1000,test_size=12,min_train=100,window=120,seed=10,use_gate=False)
    assert bt.n_test == 12
    assert len(bt.rows) == 4*12
    assert all(bt.summary['测试期数']==12)
    assert (bt.summary['随机期望命中期数'] == 0.12).all()


def test_gate_uniform_sample_can_fallback():
    h = data(80).frame['number'].tolist()
    gate = evidence_gate(h,'pairwise')
    assert not gate['active']
    result = select_numbers(h,count=300,model='pairwise',seed=12,use_gate=True)
    assert result.gated_fallback


def test_score_not_mutated_by_future_outcome():
    h = data(60).frame['number'].tolist()
    base = score_candidates(h,'positional')
    alt = score_candidates(h.copy(),'positional')
    assert np.array_equal(base,alt)


def test_last_period_prediction_cannot_see_its_actual(monkeypatch):
    import pailie5.backtest as module
    base = data(160)
    changed_frame = base.frame.copy()
    changed_frame.loc[159, 'number'] = '99999'
    from pailie5.data import Draws
    alt = Draws(changed_frame, tuple())
    chosen_history = []
    original = module.select_numbers
    def record(history, **kw):
        chosen_history.append(tuple(history))
        return original(history, **kw)
    monkeypatch.setattr(module, 'select_numbers', record)
    module.run_backtest(base,count=1000,test_size=1,min_train=100,window=100,use_gate=False)
    prev = chosen_history[:]
    chosen_history.clear()
    module.run_backtest(alt,count=1000,test_size=1,min_train=100,window=100,use_gate=False)
    assert chosen_history == prev
    assert all('99999' not in h for h in chosen_history)
