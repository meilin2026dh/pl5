"""Search tests focus on isolation and falsification, not just seeded answers."""
import importlib
import json
from dataclasses import replace
import numpy as np
import pytest


def m(): return importlib.import_module('pailie5.structure_search_v372')
def e(): return importlib.import_module('pailie5.structure_evidence_v372')


def example():
    a, b = np.indices((10, 10)); truth = (a + b) % 10
    ids = np.random.default_rng(712).permutation(100)
    def cells(indices):
        return m().CellDataset(tuple((int(i // 10), int(i % 10), int(truth.flat[i])) for i in indices))
    return truth, cells(ids[:70]), cells(ids[70:])


def test_search_and_evidence_modules_exist():
    assert importlib.util.find_spec('pailie5.structure_search_v372') is not None
    assert importlib.util.find_spec('pailie5.structure_evidence_v372') is not None


def test_train_only_search_is_deterministic_and_hard_bounded():
    truth, train, holdout = example()
    cfg = m().SearchConfig(seed=81, max_evaluations=500, generations=3)
    first, second = m().fit(train, cfg), m().fit(train, cfg)
    assert first.to_dict() == second.to_dict()
    assert first.evaluated_expressions <= 500
    assert first.training_errors == 0
    assert e().evaluate_frozen(first.operator, holdout)['errors'] == 0
    assert e().certify_table(first.operator, truth)['exact_on_all_100_pairs']


def test_changing_holdout_labels_cannot_change_frozen_operator():
    _, train, holdout = example()
    result = m().fit(train, m().SearchConfig(max_evaluations=500, generations=2))
    before = result.to_dict()
    altered = m().CellDataset(tuple((a, b, (y + 1) % 10) for a, b, y in holdout.rows))
    assert e().evaluate_frozen(result.operator, altered)['errors'] == 30
    assert result.to_dict() == before
    assert e().evaluate_frozen(result.operator, holdout)['errors'] == 0


def test_evaluation_rejects_training_overlap_by_default():
    _, train, _ = example()
    result = m().fit(train, m().SearchConfig(max_evaluations=100, generations=1))
    with pytest.raises(ValueError, match='overlap'): e().evaluate_frozen(result.operator, train)


@pytest.mark.parametrize('rows', [(), ((0, 0, 1), (0, 0, 2)), ((True, 0, 1),),
    ((10, 0, 1),), ((0, 0, 10),), ((0, 0, 1.5),), ((0, 1),)])
def test_invalid_cell_datasets_rejected(rows):
    with pytest.raises(ValueError): m().CellDataset(rows)


@pytest.mark.parametrize('settings', [dict(seed=True), dict(seed=-1),
    dict(max_evaluations=0), dict(max_nodes=16), dict(max_depth=9),
    dict(complexity_penalty=float('nan')), dict(complexity_penalty=float('inf')),
    dict(population=1), dict(generations=0), dict(beam_width=0)])
def test_invalid_search_settings_rejected(settings):
    with pytest.raises(ValueError): m().SearchConfig(**settings)


def test_warm_start_is_charged_and_frozen_reuse_does_not_refit():
    _, train, holdout = example()
    src = m().fit(train, m().SearchConfig(max_evaluations=500, generations=1))
    dst = m().fit(train, m().SearchConfig(max_evaluations=40, generations=1), warm_starts=(src.operator.expression,))
    assert dst.training_errors == 0
    assert 1 <= dst.evaluated_expressions <= 40
    assert e().evaluate_frozen(dst.operator, holdout)['errors'] == 0


def test_artifact_roundtrip_and_tamper_detection(tmp_path):
    _, train, _ = example()
    result = m().fit(train, m().SearchConfig(max_evaluations=100, generations=1))
    path = tmp_path / 'operator.json'
    e().save_operator(result.operator, path)
    assert e().load_operator(path) == result.operator
    card = json.loads(path.read_text())
    card['operator']['expression'] = ['const', 0]
    path.write_text(json.dumps(card))
    with pytest.raises(ValueError, match='integrity'): e().load_operator(path)


def test_properties_provide_explicit_counterexamples():
    _, train, _ = example()
    op = m().fit(train, m().SearchConfig(max_evaluations=500, generations=1)).operator
    arbitrary = replace(op, expression=('binary', 'sub', ('a',), ('b',)))
    target = (np.indices((10, 10))[0] - np.indices((10, 10))[1]) % 10
    cert = e().certify_table(arbitrary, target)
    assert not cert['properties']['commutative']
    assert cert['properties']['commutativity_counterexample'] is not None
    assert not cert['properties']['associative']
    assert cert['properties']['associativity_counterexample'] is not None


def test_random_table_is_not_certified_as_exact():
    _, train, _ = example()
    result = m().fit(train, m().SearchConfig(max_evaluations=500, generations=1))
    random = np.random.default_rng(102).integers(0, 10, (10, 10))
    cert = e().certify_table(result.operator, random)
    assert not cert['exact_on_all_100_pairs']
    assert cert['first_mismatch'] is not None
    assert cert['production_enabled'] is False
    assert cert['predictive_advantage'] == 'NOT_ESTABLISHED'


def test_tiny_budget_keeps_safe_baseline_even_with_overflowing_warm_start():
    _, train, _ = example()
    square = ('binary', 'mul', ('const', 9), ('const', 9))
    fourth = ('binary', 'mul', square, square)
    eighth = ('binary', 'mul', fourth, fourth)  # 15 nodes; exceeds legacy integer bound.
    result = m().fit(train, m().SearchConfig(max_evaluations=1, max_nodes=15, max_depth=8),
                     warm_starts=(eighth,))
    assert result.evaluated_expressions == 1
    assert result.operator.expression == ('a',)


def test_integer_behaviors_not_merged_just_because_final_digit_tables_match():
    _, train, _ = example()
    shifted = ('binary', 'add', ('a',), ('binary', 'add', ('const', 5), ('const', 5)))
    result = m().fit(train, m().SearchConfig(max_evaluations=3), warm_starts=(shifted,))
    assert result.distinct_integer_behaviors == 3
