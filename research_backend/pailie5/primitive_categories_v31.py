"""PL5 V3.1: discover new *finite-domain operator categories* from a frozen table.

This system learns operation semantics (a quotient table or a cyclic orbit
lookup) rather than only assembling pre-existing arithmetic symbols. The new
operation is a versioned executable capability, not a mathematical theorem or
an estimate of a lottery outcome probability.

Design invariants:
- No eval, exec, imports from learned strings, or network access.
- Every candidate is exact for ALL 100 domain pairs before registration.
- Reconstruct and independently evaluate the operation, then check SHA256.
- MDL is a *specified coding proxy*; comparisons must not be represented as
  actual compressed file sizes or prospective prediction evidence.
- Failed/non-compressible operators stay as raw finite lookup tables.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import sqlite3
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .primitive_invention_v29 import Primitive, discover, history_array, DIGITS
from .symbolic_operators_v30 import search_formula

VERSION = "v31-operator-category-1"
ALLOWED = ("row_column_quotient", "cyclic_difference", "cyclic_sum")
GRID_A, GRID_B = np.indices((10, 10))


def _validated_table(table: np.ndarray) -> tuple[np.ndarray, int]:
    raw = np.asarray(table)
    if raw.shape != (10, 10) or not np.issubdtype(raw.dtype, np.integer):
        raise ValueError("有限算子输入须为10×10整数表")
    if np.any(raw < 0) or np.any(raw > 3):
        raise ValueError("输出类别必须为0—3")
    vals = raw.astype(np.uint8)
    k = int(vals.max()) + 1
    if k not in (3, 4) or not np.array_equal(np.unique(vals), np.arange(k)):
        raise ValueError("当前仅支持恰好3或4个连续输出类别")
    return vals, k


def _sha(t: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(t, dtype=np.uint8).tobytes()).hexdigest()


def _bin(n: int) -> int:
    return max(1, (n - 1).bit_length())


def _row_column(t: np.ndarray, k: int) -> dict:
    # Equivalence relation: two rows/columns are identical *for every input*
    # of the opposite argument. Quotient labels follow first occurrence.
    rows: dict[tuple[int, ...], int] = {}
    cols: dict[tuple[int, ...], int] = {}
    ra, cb = [], []
    for a in range(10):
        key = tuple(int(x) for x in t[a, :])
        if key not in rows: rows[key] = len(rows)
        ra.append(rows[key])
    for b in range(10):
        key = tuple(int(x) for x in t[:, b])
        if key not in cols: cols[key] = len(cols)
        cb.append(cols[key])
    r, c = len(rows), len(cols)
    core = [[None] * c for _ in range(r)]
    for a in range(10):
        for b in range(10):
            idx_r, idx_c = ra[a], cb[b]
            old = core[idx_r][idx_c]
            val = int(t[a, b])
            if old is not None and old != val:
                raise AssertionError("商类不是合法的全域等价划分")
            core[idx_r][idx_c] = val
    if any(v is None for row in core for v in row): raise AssertionError("存在缺失的商类")
    # Explicit proxy code: family/header 24 bits, 10 row and 10 col labels,
    # and one output symbol per quotient cell. No claim of compressor optimality.
    bits = 24 + 10 * _bin(r) + 10 * _bin(c) + r * c * _bin(k)
    return {"family": ALLOWED[0], "payload": {"row_labels": ra, "column_labels": cb, "core": core},
            "bits": bits, "basis_size": r * c, "substructure": f"{r} row classes × {c} column classes"}


def _cyclic(t: np.ndarray, k: int, family: str) -> dict | None:
    if family not in ALLOWED[1:]: raise ValueError("不支持的周期轨道类别")
    orbit: list[int | None] = [None] * 10
    for a in range(10):
        for b in range(10):
            index = (a - b) % 10 if family == "cyclic_difference" else (a + b) % 10
            val = int(t[a, b])
            if orbit[index] is not None and orbit[index] != val:
                return None
            orbit[index] = val
    if any(x is None for x in orbit): raise AssertionError("周期轨道覆盖不完整")
    bits = 24 + 10 * _bin(k)
    return {"family": family, "payload": {"orbit": orbit}, "bits": bits,
            "basis_size": 10, "substructure": "10-element cyclic quotient orbit"}


def _evaluate_scalar(family: str, payload: dict, a: int, b: int) -> int:
    if type(a) is not int or type(b) is not int or not (0 <= a <= 9 and 0 <= b <= 9):
        raise ValueError("新算子的输入必须为0—9的整数")
    if family == "row_column_quotient":
        return payload["core"][payload["row_labels"][a]][payload["column_labels"][b]]
    if family == "cyclic_difference": return payload["orbit"][(a - b) % 10]
    if family == "cyclic_sum": return payload["orbit"][(a + b) % 10]
    raise ValueError("未知算子类别")


def _validate_payload(family: str, payload: dict, k: int):
    if type(payload) is not dict or family not in ALLOWED or k not in (3, 4):
        raise ValueError("算子描述不合法")
    if family == "row_column_quotient":
        if set(payload) != {"row_labels", "column_labels", "core"}: raise ValueError("商类描述字段错误")
        a, b, core = payload["row_labels"], payload["column_labels"], payload["core"]
        if type(a) is not list or type(b) is not list or len(a) != 10 or len(b) != 10:
            raise ValueError("商类索引必须覆盖10个输入")
        if not all(type(v) is int and 0 <= v <= 9 for v in a+b): raise ValueError("商类索引类型非法")
        r, c = len(set(a)), len(set(b))
        if set(a) != set(range(r)) or set(b) != set(range(c)):
            raise ValueError("商类标签必须连续")
        if type(core) is not list or len(core) != r or any(type(row) is not list or len(row) != c for row in core):
            raise ValueError("压缩运算表尺寸错误")
        vals = [v for row in core for v in row]
    else:
        if set(payload) != {"orbit"} or type(payload["orbit"]) is not list or len(payload["orbit"]) != 10:
            raise ValueError("轨道表必须含10个符号")
        vals = payload["orbit"]
    if not all(type(v) is int and 0 <= v < k for v in vals):
        raise ValueError("输出符号越界")


def _evaluate_vector(family: str, payload: dict, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    if family == "row_column_quotient":
        ra = np.array(payload["row_labels"], dtype=np.int64)
        cb = np.array(payload["column_labels"], dtype=np.int64)
        core = np.asarray(payload["core"], dtype=np.uint8)
        return core[ra[a], cb[b]]
    orbit = np.asarray(payload["orbit"], dtype=np.uint8)
    return orbit[(a - b) % 10 if family == "cyclic_difference" else (a + b) % 10]


def _frozen_payload(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class InventedCategory:
    id: str
    family: str
    payload: dict
    levels: int
    source_table_sha256: str
    raw_bits: int
    representation_bits: int
    basis_size: int
    source_id: str
    version: str = VERSION

    def __post_init__(self):
        _validate_payload(self.family, self.payload, self.levels)
        if type(self.raw_bits) is not int or self.raw_bits != 100 * _bin(self.levels):
            raise ValueError("原始编码比特数错误")
        if type(self.representation_bits) is not int or self.representation_bits < 1:
            raise ValueError("描述长度错误")
        if not isinstance(self.source_table_sha256, str) or len(self.source_table_sha256) != 64:
            raise ValueError("缺失原始表指纹")
        canonical = {"family": self.family, "payload": self.payload, "levels": self.levels,
                     "table_sha256": self.source_table_sha256, "version": self.version}
        hid = hashlib.sha256(_frozen_payload(canonical).encode()).hexdigest()[:24]
        if self.id != "pl5.category." + hid:
            raise ValueError("算子ID与能力定义不一致")

    def call(self, a: int, b: int) -> int:
        return _evaluate_scalar(self.family, self.payload, a, b)

    def vector(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        x, y = np.asarray(a), np.asarray(b)
        if x.shape != y.shape or not np.issubdtype(x.dtype, np.integer) or not np.issubdtype(y.dtype, np.integer):
            raise ValueError("批量输入形状或类型错误")
        if np.any(x < 0) or np.any(x > 9) or np.any(y < 0) or np.any(y > 9):
            raise ValueError("输入包含非法数字")
        return _evaluate_vector(self.family, self.payload, x.astype(np.int64), y.astype(np.int64))

    def table(self) -> np.ndarray:
        return self.vector(GRID_A, GRID_B)

    def certify(self) -> dict:
        v = self.table()
        if _sha(v) != self.source_table_sha256: raise ValueError("重建真值表的SHA256不符")
        for a in range(10):
            for b in range(10):
                if int(v[a, b]) != self.call(a, b): raise ValueError("独立标量验证失败")
        return {"checked_pairs": 100, "independent_scalar_check": True,
                "table_sha256": self.source_table_sha256, "status": "passed"}

    def card(self) -> dict:
        return {"uacp_version": "v1", "id": self.id, "version": self.version,
                "kind": "learned_finite_operator_category", "family": self.family,
                "inputs": ["digit_0_to_9", "digit_0_to_9"],
                "output": f"category_0_to_{self.levels-1}",
                "payload": self.payload, "source_id": self.source_id,
                "source_table_sha256": self.source_table_sha256,
                "representation_bits_proxy": self.representation_bits,
                "raw_bits_proxy": self.raw_bits,
                "compression_ratio_proxy": self.representation_bits / self.raw_bits,
                "basis_size": self.basis_size, "proof": self.certify(),
                "execution": "frozen_primitive_safe_no_eval", "status": "research_only",
                "prediction_advantage": "not_established",
                "limits": "全表等价证明不等于对未来开奖号码的预测优势；MDL是固定编码代理"}


def invent_categories(table: np.ndarray, *, source_id: str = "unknown", min_saved_bits: int = 1) -> tuple[list[InventedCategory], list[dict]]:
    """Invent finite operations by searching *category* decompositions.

    Unlike a formula grammar, the discovered quotient labels and orbit values
    are data-derived. A table that cannot be compressed is explicitly rejected.
    """
    t, k = _validated_table(table)
    if type(min_saved_bits) is not int or not 1 <= min_saved_bits <= 200:
        raise ValueError("最小压缩位数必须是1—200的整数")
    candidates = [_row_column(t, k)]
    for kind in ALLOWED[1:]:
        item = _cyclic(t, k, kind)
        if item is not None: candidates.append(item)
    sha = _sha(t)
    accepted, rejected = [], []
    seen = set()
    for proposal in sorted(candidates, key=lambda r: (r["bits"], r["family"])):
        family = proposal["family"]
        if proposal["bits"] > 100 * _bin(k) - min_saved_bits:
            rejected.append({"family": family, "reason": "压缩收益不足", "bits": proposal["bits"]})
            continue
        canonical = {"family": family, "payload": proposal["payload"], "levels": k,
                     "table_sha256": sha, "version": VERSION}
        identity = "pl5.category." + hashlib.sha256(_frozen_payload(canonical).encode()).hexdigest()[:24]
        if identity in seen: continue
        op = InventedCategory(identity, family, proposal["payload"], k, sha,
                              100 * _bin(k), proposal["bits"], proposal["basis_size"], source_id)
        op.certify()
        accepted.append(op)
        seen.add(identity)
    if not accepted:
        rejected.append({"family": "all", "reason": "未发现能全域重建且节约编码长度的算子类别；保留原表"})
    return accepted, rejected


def category_gap_report(table: np.ndarray, *, source_id: str = "unknown") -> dict:
    t, k = _validated_table(table)
    inventions, rejected = invent_categories(t, source_id=source_id)
    raw = 100 * _bin(k)
    return {"source_id": source_id, "table_sha256": _sha(t),
            "status": "category_found" if inventions else "language_gap_open",
            "raw_bits": raw,
            "invented_count": len(inventions),
            "best_description_bits": min((x.representation_bits for x in inventions), default=raw),
            "invented_families": [x.family for x in inventions], "rejections": rejected,
            "next_hypothesis": ("通过已发现的商类或周期轨道算子开展结构和协同实验" if inventions else
                                "提出受约束新类别假设（分段轨道/递归状态/有限自动机），需逐项全表核验和MDL审计"),
            "prediction_advantage": "not_established"}


def run_operator_on_100k(op: InventedCategory, positions=(0, 1), allowed_symbols=(0,)) -> dict:
    """Expose as experimental ESSE Boolean mask; never auto-activate."""
    if not (isinstance(positions, tuple) and len(positions) == 2 and all(type(p) is int for p in positions)
            and 0 <= positions[0] < positions[1] <= 4):
        raise ValueError("选择两个不同的号码位置，按递增顺序")
    if not isinstance(allowed_symbols, (tuple, list)) or not allowed_symbols or not all(type(i) is int and 0 <= i < op.levels for i in allowed_symbols):
        raise ValueError("必须选择合法类别")
    op.certify()
    codes = op.vector(DIGITS[:, positions[0]], DIGITS[:, positions[1]])
    mask = np.isin(codes, np.array(allowed_symbols, dtype=np.uint8)).astype(np.uint8)
    return {"operator_id": op.id, "positions": list(positions),
            "allowed_symbols": sorted(set(allowed_symbols)), "total": len(mask),
            "retained": int(mask.sum()), "removed": len(mask) - int(mask.sum()),
            "mask_sha256": _sha(mask), "mask": mask,
            "status": "research_only_not_auto_activated", "probability_under_uniform": float(mask.mean())}


class CategoryRegistry:
    """Append-only research registry with integrity verification on read."""
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS v31_categories (
                 id TEXT PRIMARY KEY, table_sha256 TEXT NOT NULL,
                 record_json TEXT NOT NULL, status TEXT NOT NULL CHECK(status='research_only'),
                 created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

    def register(self, op: InventedCategory) -> bool:
        record = {"id": op.id, "family": op.family, "payload": op.payload,
                  "levels": op.levels, "source_table_sha256": op.source_table_sha256,
                  "raw_bits": op.raw_bits, "representation_bits": op.representation_bits,
                  "basis_size": op.basis_size, "source_id": op.source_id, "version": op.version}
        op.certify()
        with sqlite3.connect(self.path) as db:
            existing = db.execute("SELECT record_json FROM v31_categories WHERE id=?", (op.id,)).fetchone()
            txt = _frozen_payload(record)
            if existing:
                prior = json.loads(existing[0])
                # One mathematical ability may be rediscovered by different source studies.
                # Provenance of the first registered discovery stays immutable; do not
                # reject an identical mathematical definition merely for a new source ID.
                if any(prior[key] != record[key] for key in record if key != "source_id"):
                    raise ValueError("重复ID已关联不同的定义，拒绝覆写")
                return False
            db.execute("INSERT INTO v31_categories (id,table_sha256,record_json,status) VALUES(?,?,?,?)",
                       (op.id,op.source_table_sha256,txt,"research_only"))
        return True

    def get(self, identity: str) -> InventedCategory:
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT record_json,table_sha256,status FROM v31_categories WHERE id=?", (identity,)).fetchone()
        if not row: raise KeyError(identity)
        if row[2] != "research_only": raise ValueError("不允许读取未经审核的状态")
        d = json.loads(row[0])
        op = InventedCategory(**d)
        if op.source_table_sha256 != row[1]: raise ValueError("持久化索引SHA不一致")
        op.certify()
        return op

    def summary(self):
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT id,table_sha256,record_json FROM v31_categories ORDER BY created_at,id").fetchall()
        result = []
        for id, sha, _ in rows:
            op = self.get(id)
            if sha != op.source_table_sha256: raise ValueError("持久化记录已损坏")
            result.append({"id": id, "family": op.family, "description_bits": op.representation_bits,
                           "source_id": op.source_id, "status": "research_only"})
        return result


def analyze_v29_primitives(numbers: list[str], *, maximum: int = 8, registry: str | Path | None = None) -> dict:
    history = history_array(numbers)
    cutoff = len(history) - 110
    if cutoff < 120: raise ValueError("必须留出110期非训练数据")
    ops, old_rejections = discover(history[:cutoff], maximum=maximum)
    database = CategoryRegistry(registry) if registry else None
    cards, gaps = [], []
    for old in ops:
        found, rejected = invent_categories(old.table_array, source_id=old.identity)
        # Consult the earlier symbolic search first: a new ability is valuable
        # only when its representation differs or reduces description complexity.
        symbolic = search_formula(old.table_array, beam_width=8, max_nodes=3)
        existing_bits = (symbolic.compressed_bits if symbolic.status in
                         ("exact_symbolic", "lossless_formula_with_exceptions") else 100 * _bin(old.levels))
        gap = category_gap_report(old.table_array, source_id=old.identity)
        gap["v30_symbolic_status"] = symbolic.status
        gap["v30_bits_proxy"] = existing_bits
        gaps.append(gap)
        for child in found:
            adds_new_value = child.representation_bits < existing_bits
            accepted = database.register(child) if database and adds_new_value else None
            cards.append({"operator_id": old.identity, "category": child.card(),
                          "source_v30_status": symbolic.status,
                          "new_coding_value": adds_new_value,
                          "inserted": accepted, "induction_train_periods": cutoff,
                          "reserved_development_periods": 60, "reserved_final_periods": 50})
    return {"version": VERSION, "source": "caller_supplied_history_unverified",
            "training_history_sha256": hashlib.sha256(history[:cutoff].tobytes()).hexdigest(),
            "total_history_periods": len(history), "generated": len(cards),
            "cards": cards, "language_gaps": gaps, "prior_rejections": old_rejections,
            "record_state": "research_only", "predictive_advantage": "not_established",
            "limitations": ["发现的类别压缩的是100格运算表，不是中奖彩票的概率分布",
                            "本阶段没有把留出110期的开奖用作择模或预测优势检验",
                            "每个正式过滤算法仍须经独立时间外及前向验证和人工批准"]}


def compose_abilities(program: dict, abilities: Mapping[str, InventedCategory],
                      digits: np.ndarray = DIGITS) -> dict:
    """Execute a bounded AAN program using newly learned primitives as operators.

    Program JSON: {"apply": "pl5.category...", "args": [{"digit":0},{"digit":1}]}.
    Nesting is supported, but arbitrary function calls or Python expressions are not.
    All outputs remain in 0..9 so one invented operation can feed another.
    """
    matrix = np.asarray(digits)
    if matrix.ndim != 2 or matrix.shape[1] != 5 or not np.issubdtype(matrix.dtype, np.integer):
        raise ValueError("候选号码必须是五列的数字矩阵")
    if np.any(matrix < 0) or np.any(matrix > 9) or len(matrix) > 100000:
        raise ValueError("号码域或计算预算越界")
    count = 0
    visited = []

    def evaluate(node: dict, depth: int) -> np.ndarray:
        nonlocal count
        count += 1
        if depth > 4 or count > 31 or type(node) is not dict:
            raise ValueError("能力协同树超出安全限额")
        if set(node) == {"digit"}:
            p = node["digit"]
            if type(p) is not int or not 0 <= p <= 4: raise ValueError("无效的号码位置")
            return matrix[:, p].astype(np.uint8)
        if set(node) == {"const"}:
            v = node["const"]
            if type(v) is not int or not 0 <= v <= 9: raise ValueError("常数仅允许0—9")
            return np.full(len(matrix), v, dtype=np.uint8)
        if set(node) != {"apply", "args"} or type(node["apply"]) is not str:
            raise ValueError("禁止外部代码或未支持的协同节点")
        oid = node["apply"]
        if oid not in abilities: raise ValueError("未注册的数学能力")
        op = abilities[oid]
        op.certify()
        args = node["args"]
        if type(args) is not list or len(args) != 2:
            raise ValueError("二元算子必须具有两个输入能力")
        lhs, rhs = evaluate(args[0], depth+1), evaluate(args[1], depth+1)
        visited.append(oid)
        return op.vector(lhs, rhs)

    vals = evaluate(program, 0)
    return {"outputs": vals, "output_sha256": _sha(vals), "number_count": len(vals),
            "used_operator_ids": sorted(set(visited)), "program": program,
            "status": "research_only_not_auto_activated"}
