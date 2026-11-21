"""V3.1 category invention, exhaustive certification and research-only AAN/ESSE interface."""
import hashlib
import json
import sqlite3
import numpy as np
import pytest
from pailie5.primitive_categories_v31 import (
    invent_categories, category_gap_report, CategoryRegistry,
    run_operator_on_100k, analyze_v29_primitives, InventedCategory,
)


def quotient_table():
    a, b = np.indices((10, 10))
    return ((a % 2 + b % 3) % 3).astype(np.uint8)


def cyclic_table():
    a, b = np.indices((10, 10))
    orb = np.array([0, 2, 1, 0, 1, 2, 2, 1, 0, 2], dtype=np.uint8)
    return orb[(a - b) % 10]


def test_auto_creates_quotient_operation_not_merely_existing_formula():
    table = quotient_table()
    found, errors = invent_categories(table, source_id="known-quotient")
    assert any(c.family == 'row_column_quotient' for c in found)
    c = next(c for c in found if c.family == 'row_column_quotient')
    assert c.basis_size == 6 and c.representation_bits < c.raw_bits
    assert c.certify()['checked_pairs'] == 100
    assert np.array_equal(c.table(), table)
    assert c.card()['prediction_advantage'] == 'not_established'


def test_invents_cyclic_difference_orbit():
    found, _ = invent_categories(cyclic_table())
    cat = next(c for c in found if c.family == 'cyclic_difference')
    assert cat.basis_size == 10
    assert len(cat.payload['orbit']) == 10
    for a in range(10):
        for b in range(10):
            assert cat.call(a, b) == int(cyclic_table()[a, b])


def test_rejects_random_uncompressible_operations():
    rng = np.random.default_rng(42)
    t = rng.integers(0, 4, size=(10, 10), dtype=np.uint8)
    t.ravel()[:4] = np.arange(4)
    invented, rejected = invent_categories(t)
    assert not invented
    assert category_gap_report(t)['status'] == 'language_gap_open'
    assert any(r['reason'] == '压缩收益不足' for r in rejected)


@pytest.mark.parametrize('bad', [np.zeros((5, 5), dtype=int), np.zeros((10, 10), dtype=float),
                                 np.ones((10, 10), dtype=int), np.full((10,10), 4, dtype=int)])
def test_input_table_rejected(bad):
    with pytest.raises(ValueError): invent_categories(bad)


def test_invalid_minimum_savings_rejected():
    with pytest.raises(ValueError): invent_categories(quotient_table(), min_saved_bits=0)
    with pytest.raises(ValueError): invent_categories(quotient_table(), min_saved_bits=201)


def test_invalid_inputs_and_payload_tampering():
    c = invent_categories(quotient_table())[0][0]
    for x, y in [(-1,0), (0,10), (0,1.2), (True,4)]:
        with pytest.raises(ValueError): c.call(x,y)
    with pytest.raises(ValueError): c.vector(np.array([-1]), np.array([0]))
    bad = json.loads(json.dumps(c.__dict__))
    bad['payload']['core'][0][0] = (bad['payload']['core'][0][0] + 1) % c.levels
    # Definition-ID guard should reject mutated operation before execution.
    with pytest.raises(ValueError,match="ID"): InventedCategory(**bad)
    bad['id']='evil'
    with pytest.raises(ValueError): InventedCategory(**bad)


def test_complete_100k_mask_guard_no_outside_original_space():
    c = invent_categories(quotient_table())[0][0]
    m = run_operator_on_100k(c, (0,4), (0,))
    mask = m['mask']
    assert mask.shape == (100000,) and mask.dtype == np.uint8
    assert mask.sum() + m['removed'] == 100000
    assert m['status'] == 'research_only_not_auto_activated'
    assert m['mask_sha256'] == hashlib.sha256(mask.tobytes()).hexdigest()
    for n in [0, 19283, 99999, 12345, 90162]:
        expected = int(c.call(int(f'{n:05d}'[0]), int(f'{n:05d}'[4])) == 0)
        assert int(mask[n]) == expected


def test_mask_bounds_guard():
    c = invent_categories(quotient_table())[0][0]
    with pytest.raises(ValueError): run_operator_on_100k(c, (0,5))
    with pytest.raises(ValueError): run_operator_on_100k(c, (2,2))
    with pytest.raises(ValueError): run_operator_on_100k(c, (0,1), (3,))


def test_registry_immutable_read_and_tamper_detected(tmp_path):
    db = CategoryRegistry(tmp_path / 'research.sqlite')
    c = invent_categories(cyclic_table(), source_id='source-x')[0][0]
    assert db.register(c)
    assert not db.register(c)
    assert db.get(c.id).certify()['status'] == 'passed'
    assert db.summary()[0]['status'] == 'research_only'
    with sqlite3.connect(db.path) as conn:
        conn.execute('UPDATE v31_categories SET table_sha256=? WHERE id=?', ('0'*64, c.id))
    with pytest.raises(ValueError): db.get(c.id)


def test_never_accepts_arbitrary_python_in_descriptor():
    c = invent_categories(quotient_table())[0][0]
    bad = dict(c.__dict__)
    bad['family'] = "__import__('os').system('evil')"
    with pytest.raises(ValueError): InventedCategory(**bad)


def test_reproducible_and_different_originals_have_different_identity():
    x = invent_categories(quotient_table())[0]
    y = invent_categories(quotient_table())[0]
    assert [c.id for c in x] == [c.id for c in y]
    z = quotient_table().copy();z[0,0] = (z[0,0]+1)%3
    zz, _ = invent_categories(z)
    assert all(c.id not in set(v.id for v in x) for c in zz)


def test_heldout_draws_do_not_affect_frozen_invention():
    rng = np.random.default_rng(7)
    hist = [''.join(map(str,row)) for row in rng.integers(0,10,(250,5))]
    a = analyze_v29_primitives(hist, maximum=2)
    b = analyze_v29_primitives(hist[:-50] + ['99999']*50, maximum=2)
    assert a['training_history_sha256'] == b['training_history_sha256']
    assert a['cards'] == b['cards']
    assert a['record_state'] == 'research_only'


def test_payload_is_json_round_trip_with_no_callable_code():
    op = invent_categories(cyclic_table())[0][0]
    dump = json.loads(json.dumps(op.__dict__))
    again = InventedCategory(**dump)
    assert again.certify()['status'] == 'passed'
    assert 'payload' in again.card()


def test_new_ability_can_compose_with_other_new_abilities():
    from pailie5.primitive_categories_v31 import compose_abilities
    rowop = invent_categories(quotient_table())[0][0]
    diffop = next(v for v in invent_categories(cyclic_table())[0] if v.family == 'cyclic_difference')
    p = {"apply": diffop.id, "args": [
         {"apply": rowop.id, "args": [{"digit": 0}, {"digit": 1}]},
         {"digit": 4}]}
    got = compose_abilities(p, {rowop.id: rowop, diffop.id: diffop})
    assert len(got['outputs']) == 100000
    assert got['status'] == 'research_only_not_auto_activated'
    for n in [0, 12345, 99999, 35791]:
        digits = [int(x) for x in f'{n:05d}']
        expect = diffop.call(rowop.call(digits[0], digits[1]), digits[4])
        assert got['outputs'][n] == expect
    with pytest.raises(ValueError):
        compose_abilities({'execute': 'rm -rf /'}, {rowop.id: rowop})


def test_registry_deduplicates_math_rediscovered_by_another_study(tmp_path):
    db = CategoryRegistry(tmp_path / 'research.sqlite')
    a = invent_categories(cyclic_table(), source_id='experiment-A')[0][0]
    b = invent_categories(cyclic_table(), source_id='experiment-B')[0][0]
    assert a.id == b.id and a.source_id != b.source_id
    assert db.register(a)
    assert not db.register(b)
    assert db.get(a.id).source_id == 'experiment-A'  # first immutable provenance


def test_cli_table_file_and_synthetic_demo(tmp_path):
    import subprocess, sys
    root=__import__('pathlib').Path(__file__).resolve().parents[1]
    t = quotient_table().tolist()
    infile=tmp_path/'table.json'; infile.write_text(json.dumps(t))
    report=tmp_path/'r.json'; db=tmp_path/'a.sqlite'
    cp=subprocess.run([sys.executable,'research_v31.py','table','--table-json',str(infile),
                       '--report',str(report),'--registry',str(db)],cwd=root,capture_output=True,text=True,timeout=30)
    assert cp.returncode == 0, cp.stderr
    got=json.loads(report.read_text())
    assert got['generated'] >= 1
    assert got['predictive_advantage']=='NOT_ESTABLISHED'
    cp=subprocess.run([sys.executable,'research_v31.py','demo','--report',str(report),
                       '--registry',str(db)],cwd=root,capture_output=True,text=True,timeout=30)
    assert cp.returncode == 0, cp.stderr
    got=json.loads(report.read_text())
    assert got['esse_experiment']['total'] == 100000
    assert got['aan_composition']['number_count'] == 100000


def test_cli_historical_research_uses_training_only(tmp_path):
    import subprocess, sys, csv
    root=__import__('pathlib').Path(__file__).resolve().parents[1]
    rng=np.random.default_rng(81)
    rows=[''.join(map(str,r)) for r in rng.integers(0,10,(250,5))]
    csv_path=tmp_path/'draws.csv'
    with csv_path.open('w',newline='') as fp:
        writer=csv.writer(fp);writer.writerow(['issue','date','number'])
        for i,n in enumerate(rows):writer.writerow([str(i+1),f'2026-01-{(i%28)+1:02d}',n])
    report=tmp_path/'research.json'
    cp=subprocess.run([sys.executable,'research_v31.py','study','--history',str(csv_path),
                       '--maximum','2','--report',str(report),'--registry',str(tmp_path/'db.sqlite')],
                       cwd=root,capture_output=True,text=True,timeout=45)
    assert cp.returncode==0,cp.stderr
    got=json.loads(report.read_text('utf-8'))
    assert got['total_history_periods'] == 250
    assert got['record_state'] == 'research_only'
    assert len(got['language_gaps']) == 2
