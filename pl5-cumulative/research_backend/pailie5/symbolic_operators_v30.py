"""V3.0 bounded symbolic discovery of mathematical descriptions for V2.9 primitives.

A finite 10x10 table may or may not admit a shorter closed-form expression.
We search an auditable, deterministic grammar. Evaluation is over all 100 input
pairs; 70/30 pair splitting evaluates expression generality, NOT draw forecast.
No eval/exec, untrusted Python or claim of predictive improvement.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import itertools
import json
import math
import sqlite3
from typing import Any

import numpy as np

from .primitive_invention_v29 import Primitive, discover, history_array

# Every program operates on integers; the only final normalization is mod k.
# Terms and operation semantics are versioned and bounded by a maximum AST size.
BINARY = ("add", "sub", "mul", "absdiff", "xor", "min", "max", "equal", "less", "gcd")
CONST = (0, 1, 2, 3, 5, 9)
GRAMMAR_VERSION = "v30-symbolic-integer-grammar-1"
GRID_A, GRID_B = (x.astype(np.int64).ravel() for x in np.indices((10, 10)))
COMMUTATIVE = {"add", "mul", "absdiff", "xor", "min", "max", "equal", "gcd"}


def _node_size(e: tuple) -> int:
    return 1 if e[0] in ("a", "b", "const") else 1 + _node_size(e[2]) + _node_size(e[3])


def _node_expr(e: tuple) -> str:
    if e[0] == "a": return "a"
    if e[0] == "b": return "b"
    if e[0] == "const": return str(e[1])
    lhs, rhs = _node_expr(e[2]), _node_expr(e[3])
    return {
        "add": f"({lhs}+{rhs})", "sub": f"({lhs}-{rhs})",
        "mul": f"({lhs}*{rhs})", "absdiff": f"abs({lhs}-{rhs})",
        "xor": f"({lhs} xor {rhs})", "min": f"min({lhs},{rhs})",
        "max": f"max({lhs},{rhs})", "equal": f"int({lhs}=={rhs})",
        "less": f"int({lhs}<{rhs})", "gcd": f"gcd({lhs},{rhs})",
    }[e[1]]


def _apply(op: str, left: np.ndarray, right: np.ndarray) -> np.ndarray:
    if op == "add": return left + right
    if op == "sub": return left - right
    if op == "mul": return left * right
    if op == "absdiff": return np.abs(left - right)
    if op == "xor": return np.bitwise_xor(left, right)
    if op == "min": return np.minimum(left, right)
    if op == "max": return np.maximum(left, right)
    if op == "equal": return (left == right).astype(np.int64)
    if op == "less": return (left < right).astype(np.int64)
    if op == "gcd": return np.gcd(left, right)
    raise ValueError("未注册的数学运算符")


def eval_expr(node: tuple, a: np.ndarray = GRID_A, b: np.ndarray = GRID_B) -> np.ndarray:
    if not isinstance(node, tuple): raise ValueError("表达式必须是安全的元组AST")
    if node == ("a",): return a.astype(np.int64)
    if node == ("b",): return b.astype(np.int64)
    if len(node) == 2 and node[0] == "const" and type(node[1]) is int and node[1] in CONST:
        return np.full_like(a, node[1], dtype=np.int64)
    if len(node) != 4 or node[0] != "binary" or node[1] not in BINARY:
        raise ValueError("不允许执行自定义代码或未知AST算子")
    if _node_size(node) > 15: raise ValueError("超出运算树上限")
    x = _apply(node[1], eval_expr(node[2], a, b), eval_expr(node[3], a, b))
    if np.any(np.abs(x) > 2_000_000): raise ValueError("运算结果超出安全界限")
    return x



def eval_expr_scalar(node: tuple, a: int, b: int) -> int:
    """Independent Python integer evaluator; no vectorized NumPy arithmetic."""
    if type(a) is not int or type(b) is not int or not(0<=a<=9 and 0<=b<=9):
        raise ValueError('标量输入必须为0—9的整数')
    if node == ('a',): return a
    if node == ('b',): return b
    if len(node)==2 and node[0]=='const' and type(node[1]) is int and node[1] in CONST:
        return node[1]
    if len(node)!=4 or node[0]!='binary' or node[1] not in BINARY or _node_size(node)>15:
        raise ValueError('不允许未登记的标量运算')
    op=node[1]
    x=eval_expr_scalar(node[2],a,b); y=eval_expr_scalar(node[3],a,b)
    if op=='add': result=x+y
    elif op=='sub': result=x-y
    elif op=='mul': result=x*y
    elif op=='absdiff': result=abs(x-y)
    elif op=='xor': result=x^y
    elif op=='min': result=min(x,y)
    elif op=='max': result=max(x,y)
    elif op=='equal': result=int(x==y)
    elif op=='less': result=int(x<y)
    elif op=='gcd': result=math.gcd(x,y)
    else: raise ValueError('未知运算')
    if abs(result)>2_000_000: raise ValueError('标量结果越界')
    return result


def _match(outputs: np.ndarray, target: np.ndarray, k: int, indices: np.ndarray) -> tuple[int, tuple[int, ...]]:
    """Optimal bijective class relabeling; preserves the original operator semantics."""
    c = np.bincount(k * outputs[indices] + target[indices], minlength=k * k).reshape(k, k)
    choices = np.array(list(itertools.permutations(range(k))), dtype=np.int64)
    values = c[np.arange(k)[None, :], choices].sum(axis=1)
    best = int(np.argmax(values))
    return int(len(indices) - values[best]), tuple(map(int, choices[best]))


@dataclass(frozen=True)
class FormulaCertificate:
    status: str
    formula: str | None
    expression: tuple | None
    class_mapping: tuple[int, ...] | None
    table_sha256: str
    training_pair_errors: int | None
    unseen_pair_errors: int | None
    whole_table_errors: int | None
    raw_table_bits: int
    formula_bits: int | None
    residual_patch_bits: int | None
    compressed_bits: int | None
    compression_ratio: float | None
    patches: tuple[tuple[int,int], ...]
    search_candidates: int
    input_pairs_train: int
    input_pairs_unseen: int
    limits: str

    def as_card(self):
        return {
            "status": self.status, "formula": self.formula,
            "expression_ast": self.expression, "class_mapping": self.class_mapping,
            "table_sha256": self.table_sha256,
            "train_pair_errors": self.training_pair_errors,
            "unseen_pair_errors": self.unseen_pair_errors,
            "whole_table_errors": self.whole_table_errors,
            "raw_table_bits": self.raw_table_bits,
            "formula_bits": self.formula_bits,
            "residual_patch_bits": self.residual_patch_bits,
            "compressed_bits": self.compressed_bits,
            "compression_ratio": self.compression_ratio,
            "patches": self.patches,
            "search_candidates": self.search_candidates,
            "input_pairs_train": self.input_pairs_train,
            "input_pairs_unseen": self.input_pairs_unseen,
            "limits": self.limits,
            "predictive_advantage": "NOT_ESTABLISHED",
            "grammar_version": GRAMMAR_VERSION,
        }


def search_formula(table: np.ndarray, *, seed: int = 17, beam_width: int = 24,
                   max_nodes: int = 7) -> FormulaCertificate:
    target = np.asarray(table)
    if target.shape != (10, 10) or not np.issubdtype(target.dtype, np.integer):
        raise ValueError("只接受10×10有限整数运算表")
    target = target.astype(np.int64).ravel()
    k = int(target.max()) + 1
    if k not in (3, 4) or not np.array_equal(np.unique(target), np.arange(k)):
        raise ValueError("输出必须覆盖0..k-1，其中k只能是3或4")
    if type(seed) is not int or not 0 <= seed < 2**32 or not 1 <= beam_width <= 80 or max_nodes not in (3, 5, 7):
        raise ValueError("符号搜索范围非法")
    rng = np.random.default_rng(seed)
    train = np.sort(rng.permutation(100)[:70]); unseen = np.setdiff1d(np.arange(100), train)
    bits_per_value = math.ceil(math.log2(k))
    raw_bits = 100 * bits_per_value
    sha = hashlib.sha256(target.astype(np.uint8).tobytes()).hexdigest()
    cache: dict[tuple, np.ndarray] = {}
    seen: set[bytes] = set()
    evaluated = 0
    scores: list[tuple[int, int, str, tuple, tuple[int, ...], np.ndarray]] = []
    
    def put(e: tuple):
        nonlocal evaluated
        if _node_size(e) > max_nodes: return
        try: values = eval_expr(e)
        except (ValueError, OverflowError): return
        out = np.mod(values, k).astype(np.int64)
        signature = out.tobytes()
        if signature in seen: return
        seen.add(signature)
        evaluated += 1
        err, mapping = _match(out, target, k, train)
        scores.append((err, _node_size(e), _node_expr(e), e, mapping, out))
        cache[e] = out

    atoms = [("a",), ("b",)] + [("const", n) for n in CONST]
    for a in atoms: put(a)
    # Layer 1: all small binary functions. Layer 2+: scored beam expansion.
    for left in atoms:
        for right in atoms:
            for op in BINARY:
                if op in COMMUTATIVE and _node_expr(left) > _node_expr(right): continue
                put(("binary", op, left, right))
    for _ in range((max_nodes - 3)//2):
        beam = sorted(scores, key=lambda r: (r[0], r[1], r[2]))[:beam_width]
        # Retain structurally distinct candidates to avoid collapsing exploration
        previous = len(scores)
        for _,_,_, parent,__,___ in beam:
            for atom in atoms:
                for op in BINARY:
                    for x,y in ((parent,atom),(atom,parent)):
                        if op in COMMUTATIVE and _node_expr(x) > _node_expr(y): continue
                        put(("binary",op,x,y))
        if len(scores) == previous: break

    # Candidate selection is based on TRAINING cells only. Holdout pairs are then
    # observed once, and cannot revise the selected formula.
    best = min(scores, key=lambda r: (r[0] * 10 + r[1], r[1], r[2]))
    err_train, size, display, expr, mapping, out = best
    mapped = np.array(mapping, dtype=np.int64)[out]
    unseen_errors = int(np.count_nonzero(mapped[unseen] != target[unseen]))
    all_errors = int(np.count_nonzero(mapped != target))
    formula_bits = size * 8 + len(CONST) + k * bits_per_value + 8
    # A patch needs an index (7 bits for 100 cells) and a class value.
    patch_bits = all_errors * (7 + bits_per_value)
    packed = formula_bits + patch_bits
    patches = tuple((int(i),int(target[i])) for i in np.where(mapped != target)[0])
    if all_errors == 0 and packed < raw_bits:
        status = "exact_symbolic"
    elif unseen_errors == 0 and packed < raw_bits:
        status = "lossless_formula_with_exceptions"
    else:
        status = "raw_table_preferred"
    if status == "raw_table_preferred":
        return FormulaCertificate(status, display, expr, mapping, sha, err_train,
            unseen_errors, all_errors, raw_bits, formula_bits, patch_bits, packed,
            packed / raw_bits, patches, evaluated, len(train), len(unseen),
            "符号近似不等于真值表可替换；原始100格查表保留为唯一执行语义")
    return FormulaCertificate(status, display+f" (mod {k})", expr, mapping, sha, err_train,
        unseen_errors, all_errors, raw_bits, formula_bits, patch_bits, packed,
        packed / raw_bits, patches, evaluated, len(train), len(unseen),
        "公式是有限域描述证书；即使100格全等，也不包含对未来开奖的预测证据")


def reconstruct_table(cert: FormulaCertificate) -> np.ndarray:
    """Decode an exact formula or a formula + verified exception patch table."""
    if cert.status not in ('exact_symbolic','lossless_formula_with_exceptions'):
        raise ValueError('随机性过高的真值表不得冒充可压缩公式')
    if cert.expression is None or cert.class_mapping is None: raise ValueError('缺少可执行公式证书')
    k=len(cert.class_mapping)
    vals = np.array(cert.class_mapping,dtype=np.uint8)[np.mod(eval_expr(cert.expression),k)]
    for index, cls in cert.patches:
        if not (0<=index<100 and 0<=cls<k):raise ValueError('补丁项超出范围')
        vals[index]=cls
    if hashlib.sha256(vals.tobytes()).hexdigest()!=cert.table_sha256:
        raise ValueError('公式/补丁未能重建原运算表')
    return vals.reshape(10,10)


def certify_formula(cert: FormulaCertificate, original_table: np.ndarray) -> bool:
    if cert.status != "exact_symbolic":
        raise ValueError("只有100格完全等价的公式才允许作为无补丁运算执行")
    table = np.asarray(original_table, dtype=np.uint8)
    if table.shape != (10, 10) or hashlib.sha256(table.tobytes()).hexdigest() != cert.table_sha256:
        raise ValueError("源算子真值表指纹不一致")
    calculated=reconstruct_table(cert).ravel()
    if not np.array_equal(calculated, table.ravel()):raise ValueError('公式与真值表不一致')
    k=len(cert.class_mapping)
    for a in range(10):
        for b in range(10):
            expected=cert.class_mapping[eval_expr_scalar(cert.expression,a,b)%k]
            if int(table[a,b])!=expected:
                raise ValueError(f'异构标量解释器发现错误输入对: {(a,b)}')
    return True



def structural_summary(table: np.ndarray) -> dict[str, Any]:
    """Label-aware structural diagnostics; no claim of temporal dependence."""
    t=np.asarray(table,dtype=np.uint8)
    if t.shape!=(10,10):raise ValueError('必须提供10×10运算表')
    k=int(t.max())+1
    if k not in (3,4):raise ValueError('运算输出类数无效')
    # Analyze one binary class-indicator matrix per symbol; numeric labels are
    # arbitrary and therefore not interpreted as geometric magnitudes.
    ranks=[]
    for symbol in range(k):
        indicator=(t==symbol).astype(float)
        sv=np.linalg.svd(indicator,compute_uv=False)
        energy=sv*sv
        ratio=np.cumsum(energy)/max(float(np.sum(energy)),1e-15)
        ranks.append(int(np.searchsorted(ratio,.95)+1))
    return {'symmetric':bool(np.array_equal(t,t.T)),
            'simultaneous_shift_invariant':bool(np.array_equal(t,np.roll(t,1,axis=(0,1)))),
            'class_95pct_energy_ranks':ranks,
            'class_histogram':np.bincount(t.ravel(),minlength=k).tolist(),
            'meaning':'按符号分别计算指示矩阵的SVD，95%能量秩只是结构复杂度，不是预测信息'}


def analyze_primitives(numbers: list[str], *, seed: int = 20261102, maximum: int = 8,
                       beam_width: int = 24, max_nodes: int = 5,
                       registry: str | Path | None = None) -> dict[str, Any]:
    data = history_array(numbers)
    # Do not include the last 110 observations in learned primitive induction.
    train_end = len(data) - 110
    if train_end < 120: raise ValueError("至少230期以留出独立历史验证和测试")
    ops, rejections = discover(data[:train_end], maximum=maximum)
    results = []
    for op in ops:
        cert = search_formula(op.table_array, seed=seed, beam_width=beam_width, max_nodes=max_nodes)
        item = {'operator_id':op.identity,'uacp':op.card(), 'symbolic':cert.as_card(),
                'equivalence_confirmed': bool(cert.status == 'exact_symbolic' and certify_formula(cert,op.table_array)),
                'table_structure':structural_summary(op.table_array),
                'research_only':True}
        results.append(item)
    rep = {'version':'pl5-v30-bounded-symbolic-regression','status':'research_only',
           'history_sha256':hashlib.sha256('|'.join(numbers).encode()).hexdigest(),
           'split':{'primitive_training_periods':train_end,'reserved_development_periods':60,
                    'reserved_unseen_periods':50},
           'grammar':GRAMMAR_VERSION,'generated':len(results),'items':results,
           'v29_rejections':rejections,
           'exact_symbolic_count':sum(x['symbolic']['status']=='exact_symbolic' for x in results),
           'no_false_promotion':True,
           'limitations':["不能从任意100格随机表提炼简短公式，可能正确拒绝压缩",
                          "公式对输入数字对的等价性不代表对未来开奖号码可预测",
                          "保留期未参与本次符号搜索；本模块不消耗它们来声称中奖优势"]}
    if registry: register_symbolic(rep, registry)
    return rep


def register_symbolic(report: dict, path: str | Path) -> int:
    dest = Path(path); dest.parent.mkdir(parents=True,exist_ok=True)
    inserted = 0
    with sqlite3.connect(dest) as db:
        db.execute("CREATE TABLE IF NOT EXISTS v30_symbolic (id TEXT PRIMARY KEY, card_json TEXT NOT NULL, status TEXT NOT NULL CHECK(status='research_only'), created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        for item in report['items']:
            j = json.dumps(item,ensure_ascii=False,sort_keys=True,allow_nan=False)
            key = hashlib.sha256(j.encode()).hexdigest()
            inserted += db.execute('INSERT OR IGNORE INTO v30_symbolic (id,card_json,status) VALUES(?, ?, ?)',(key,j,'research_only')).rowcount
    return inserted
