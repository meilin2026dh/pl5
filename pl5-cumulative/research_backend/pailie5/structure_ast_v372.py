"""Guarded structural variation of the existing V3.0 integer AST.

No dynamic Python execution. Intermediate results are integers (not digits).
Only the outermost result is reduced modulo 10. Hard bounds match V3.0.
"""
from __future__ import annotations

import numpy as np
from .symbolic_operators_v30 import BINARY, CONST, COMMUTATIVE, eval_expr

AST = tuple
ATOMS = (("a",), ("b",)) + tuple(("const", n) for n in CONST)
MAX_NODES = 15
MAX_DEPTH = 8
GRAMMAR = "pl5-v372-v30-integer-ast-final-mod10-1"


def validate_ast(tree: AST, *, max_nodes: int = MAX_NODES,
                 max_depth: int = MAX_DEPTH) -> tuple[int, int]:
    """Iterative shape check *before* calling any recursive legacy interpreter."""
    if (type(max_nodes) is not int or not 1 <= max_nodes <= MAX_NODES or
            type(max_depth) is not int or not 1 <= max_depth <= MAX_DEPTH):
        raise ValueError("invalid AST bounds")
    stack = [(tree, 1)]
    size, depth = 0, 0
    while stack:
        node, level = stack.pop()
        size += 1
        depth = max(depth, level)
        if size > max_nodes or level > max_depth:
            raise ValueError("AST exceeds node/depth bound")
        if not isinstance(node, tuple):
            raise ValueError("AST nodes must be tuples")
        if node in (("a",), ("b",)):
            continue
        if (len(node) == 2 and node[0] == "const" and
                type(node[1]) is int and node[1] in CONST):
            continue
        if (len(node) != 4 or node[0] != "binary" or
                not isinstance(node[1], str) or node[1] not in BINARY):
            raise ValueError("unknown or malformed AST node")
        stack.extend(((node[3], level + 1), (node[2], level + 1)))
    return size, depth


def load_ast(value) -> AST:
    """Decode only the JSON/list representation of the whitelisted grammar."""
    count = 0

    def convert(node, depth):
        nonlocal count
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH:
            raise ValueError("AST exceeds node/depth bound")
        if not isinstance(node, (list, tuple)):
            raise ValueError("AST must be a list/tuple, never code or an object")
        if len(node) == 4 and node[0] == "binary":
            return (node[0], node[1], convert(node[2], depth + 1), convert(node[3], depth + 1))
        if len(node) not in (1, 2):
            raise ValueError("malformed AST leaf")
        return tuple(node)

    result = convert(value, 1)
    validate_ast(result)
    return result


def _description(t: AST) -> str:
    if t[0] in ("a", "b"):
        return t[0]
    if t[0] == "const":
        return str(t[1])
    op, left, right = t[1], _description(t[2]), _description(t[3])
    if op in ("add", "sub", "mul"):
        symbol = {"add": "+", "sub": "-", "mul": "*"}[op]
        return f"({left}{symbol}{right})"
    return f"{op}({left},{right})"


def describe(tree: AST) -> str:
    validate_ast(tree)
    return _description(tree) + " mod 10"


def normalize(tree: AST) -> AST:
    """Only identities valid over integers; never use modular identities inside."""
    validate_ast(tree)

    def reduce(t):
        if t[0] != "binary":
            return t
        op, left, right = t[1], reduce(t[2]), reduce(t[3])
        zero, one = ("const", 0), ("const", 1)
        if op in COMMUTATIVE and repr(left) > repr(right):
            left, right = right, left
        if op == "add":
            if left == zero: return right
            if right == zero: return left
        if op == "sub":
            if right == zero: return left
            if left == right: return zero
        if op == "mul":
            if left == zero or right == zero: return zero
            if left == one: return right
            if right == one: return left
        if op in ("absdiff", "xor") and left == right: return zero
        if op in ("min", "max") and left == right: return left
        if op == "equal" and left == right: return one
        if op == "less" and left == right: return zero
        return ("binary", op, left, right)

    return reduce(tree)


def table(tree: AST) -> np.ndarray:
    validate_ast(tree)
    return np.mod(eval_expr(tree), 10).astype(np.uint8).reshape(10, 10)


def _paths(t, prefix=()):
    out = [prefix]
    if t[0] == "binary":
        out += _paths(t[2], prefix + (2,))
        out += _paths(t[3], prefix + (3,))
    return out


def _at(t, path):
    for i in path: t = t[i]
    return t


def _replace(t, path, new):
    if not path: return new
    parts = list(t)
    parts[path[0]] = _replace(parts[path[0]], path[1:], new)
    return tuple(parts)


def _choice(rng, items):
    return items[int(rng.integers(len(items)))]


def mutate(tree: AST, rng: np.random.Generator, *, max_nodes: int = MAX_NODES,
           max_depth: int = MAX_DEPTH, operators: tuple[str, ...] = BINARY) -> AST:
    """Propose subtree replacement, wrapping, shrinkage, or token mutation."""
    validate_ast(tree, max_nodes=max_nodes, max_depth=max_depth)
    if not operators or any(op not in BINARY for op in operators):
        raise ValueError("invalid mutation operators")
    paths = _paths(tree)
    for _ in range(24):
        path = _choice(rng, paths)
        node = _at(tree, path)
        atom = _choice(rng, ATOMS)
        op = _choice(rng, operators)
        mode = int(rng.integers(5))
        if mode == 0:
            replacement = atom
        elif mode == 1:
            replacement = ("binary", op, node, atom) if int(rng.integers(2)) else ("binary", op, atom, node)
        elif mode == 2 and node[0] == "binary":
            replacement = ("binary", op, node[2], node[3])
        elif mode == 3 and node[0] == "binary":
            replacement = node[2 + int(rng.integers(2))]
        else:
            replacement = ("binary", op, atom, _choice(rng, ATOMS))
        child = _replace(tree, path, replacement)
        try:
            validate_ast(child, max_nodes=max_nodes, max_depth=max_depth)
            return normalize(child)
        except ValueError:
            continue
    return tree


def crossover(left: AST, right: AST, rng: np.random.Generator, *,
              max_nodes: int = MAX_NODES, max_depth: int = MAX_DEPTH) -> AST:
    validate_ast(left, max_nodes=max_nodes, max_depth=max_depth)
    validate_ast(right, max_nodes=max_nodes, max_depth=max_depth)
    lp, rp = _paths(left), _paths(right)
    for _ in range(24):
        child = _replace(left, _choice(rng, lp), _at(right, _choice(rng, rp)))
        try:
            validate_ast(child, max_nodes=max_nodes, max_depth=max_depth)
            return normalize(child)
        except ValueError:
            continue
    return left
