"""AST tests use V3.0's independent scalar interpreter as the oracle."""
import importlib
import numpy as np
import pytest
from pailie5.symbolic_operators_v30 import BINARY, eval_expr_scalar


def module():
    return importlib.import_module('pailie5.structure_ast_v372')


def test_v372_ast_module_exists():
    assert importlib.util.find_spec('pailie5.structure_ast_v372') is not None


@pytest.mark.parametrize('op', BINARY)
def test_integer_semantics_match_independent_scalar_interpreter(op):
    m = module()
    tree = ('binary', op, ('binary', 'sub', ('a',), ('b',)), ('const', 3))
    observed = m.table(tree)
    expected = np.array([[eval_expr_scalar(tree, a, b) % 10 for b in range(10)] for a in range(10)])
    np.testing.assert_array_equal(observed, expected)


@pytest.mark.parametrize('bad', [
    ('call', '__import__'), ('binary', 'exec', ('a',), ('b',)),
    ('const', True), ('const', 4), ('a', 0), (), 'a+b',
    ('binary', 'add', ('a',)), ('binary', 'add', ('a',), ('b',), ('a',)),
])
def test_untrusted_nodes_rejected(bad):
    with pytest.raises(ValueError): module().validate_ast(bad)


def test_deep_tree_rejected_before_unsafe_recursion():
    tree = ('a',)
    for _ in range(100): tree = ('binary', 'add', tree, ('b',))
    with pytest.raises(ValueError): module().validate_ast(tree)


def test_json_load_round_trip_and_unknown_tokens():
    m = module()
    tree = m.load_ast(['binary', 'mul', ['a'], ['binary', 'add', ['b'], ['const', 1]]])
    assert tree == ('binary', 'mul', ('a',), ('binary', 'add', ('b',), ('const', 1)))
    with pytest.raises(ValueError): m.load_ast({'call': '__import__'})


@pytest.mark.parametrize('tree', [
    ('binary', 'add', ('a',), ('const', 0)),
    ('binary', 'mul', ('b',), ('const', 1)),
    ('binary', 'sub', ('a',), ('a',)),
    ('binary', 'add', ('b',), ('a',)),
    ('binary', 'mul', ('const', 2), ('const', 3)),
    ('binary', 'absdiff', ('binary', 'sub', ('a',), ('b',)), ('const', 5)),
])
def test_simplification_preserves_all_100_input_pairs(tree):
    m = module()
    np.testing.assert_array_equal(m.table(tree), m.table(m.normalize(tree)))


def test_seeded_mutation_changes_tree_structure_within_bounds():
    m = module()
    tree = ('binary', 'add', ('a',), ('b',))
    rng1, rng2 = np.random.default_rng(29), np.random.default_rng(29)
    left = [m.mutate(tree, rng1, max_nodes=9, max_depth=5) for _ in range(80)]
    right = [m.mutate(tree, rng2, max_nodes=9, max_depth=5) for _ in range(80)]
    assert left == right
    assert any(m.validate_ast(t)[0] > 3 for t in left)
    assert any(m.validate_ast(t)[0] < 3 for t in left)
    for t in left: m.validate_ast(t, max_nodes=9, max_depth=5)


def test_crossover_reproducible_and_safe():
    m = module()
    a = ('binary', 'add', ('a',), ('const', 3))
    b = ('binary', 'mul', ('b',), ('b',))
    r, s = np.random.default_rng(8), np.random.default_rng(8)
    children = [m.crossover(a, b, r, max_nodes=9, max_depth=5) for _ in range(40)]
    assert children == [m.crossover(a, b, s, max_nodes=9, max_depth=5) for _ in range(40)]
    assert any(c != a for c in children)
    for c in children: m.validate_ast(c, max_nodes=9, max_depth=5)
