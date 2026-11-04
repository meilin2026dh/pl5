"""V3.2: data-guided generation of finite-operator category hypotheses.

Each learned family must provide an *exact* 10x10 reconstruction, a scalar
reference evaluator independent of the vector evaluator, and a predeclared
code-length proxy. Search results are mathematical representations ONLY; no
future-draw probability is inferred. All abilities remain research_only.

No dynamic Python execution, eval, external imports, or untrusted expressions.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping

import numpy as np

from .primitive_categories_v31 import (
    _validated_table, _sha, _bin, invent_categories, GRID_A, GRID_B,
    compose_abilities, run_operator_on_100k,
)
from .primitive_invention_v29 import discover, history_array

VERSION = "v32-learned-category-hypotheses-1"
FAMILIES = ("affine_orbit", "piecewise_orbit", "sparse_orbit_exceptions")


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _axis(a: int, b: int, u: int, v: int) -> int:
    return (u * a + v * b) % 10


def _validate_payload(family: str, p: dict, levels: int) -> None:
    if family not in FAMILIES or type(p) is not dict or levels not in (3, 4):
        raise ValueError("不支持的类别/参数")
    if family == "affine_orbit":
        if set(p) != {"u", "v", "orbit"}:
            raise ValueError("仿射轨道描述字段错误")
        values = p["orbit"]
        if not (type(p["u"]) is int and type(p["v"]) is int and
                1 <= p["u"] <= 9 and 1 <= p["v"] <= 9):
            raise ValueError("仿射系数非法")
    elif family == "piecewise_orbit":
        if set(p) != {"orientation", "row_classes", "orbits"}:
            raise ValueError("分段轨道描述字段错误")
        if p["orientation"] not in ("difference", "sum"):
            raise ValueError("分段轨道方向非法")
        cl = p["row_classes"]
        values = p["orbits"]
        if (type(cl) is not list or len(cl) != 10 or not all(type(c) is int for c in cl)
                or type(values) is not list or not 2 <= len(values) <= 3
                or set(cl) != set(range(len(values)))):
            raise ValueError("分段轨道类索引非法")
        if any(type(row) is not list or len(row) != 10 for row in values):
            raise ValueError("分段轨道长度非法")
    else:
        if set(p) != {"u", "v", "orbit", "exceptions"}:
            raise ValueError("稀疏修补描述字段错误")
        values = p["orbit"]
        if (type(values) is not list or len(values) != 10 or
                not all(type(z) is int and 0 <= z < levels for z in values)):
            raise ValueError("稀疏轨道表非法")
        if not (type(p["u"]) is int and type(p["v"]) is int
                and 1 <= p["u"] <= 9 and 1 <= p["v"] <= 9):
            raise ValueError("稀疏修补系数非法")
        exc = p["exceptions"]
        if type(exc) is not list or not 1 <= len(exc) <= 6:
            raise ValueError("例外点数量非法")
        if any(type(z) is not list or len(z) != 3 or any(type(i) is not int for i in z)
               or not (0 <= z[0] <= 9 and 0 <= z[1] <= 9 and 0 <= z[2] < levels) for z in exc):
            raise ValueError("例外点格式非法")
        coords = [(z[0], z[1]) for z in exc]
        if coords != sorted(set(coords)):
            raise ValueError("例外点必须唯一且顺序规范")
        if any(z[2] == values[_axis(z[0], z[1], p["u"], p["v"])] for z in exc):
            raise ValueError("冗余例外点非法")
    flattened = [x for row in values for x in row] if family == "piecewise_orbit" else values
    if (type(values) is not list or (family != "piecewise_orbit" and len(values) != 10)
            or not all(type(x) is int and 0 <= x < levels for x in flattened)):
        raise ValueError("轨道表类别非法")


def _code_bits(family: str, p: dict, k: int) -> int:
    if family == "affine_orbit":
        return 24 + 8 + 10*_bin(k)
    if family == "piecewise_orbit":
        r = len(p["orbits"])
        return 24 + 1 + 10*_bin(r) + r*10*_bin(k)
    if family == "sparse_orbit_exceptions":
        return 24 + 8 + 10*_bin(k) + len(p["exceptions"])*(7 + _bin(k))
    raise ValueError("未知类别")


def _scalar(family: str, p: dict, a: int, b: int) -> int:
    if type(a) is not int or type(b) is not int or not (0 <= a <= 9 and 0 <= b <= 9):
        raise ValueError("只能输入0—9的两整数")
    if family == "affine_orbit":
        return p["orbit"][_axis(a, b, p["u"], p["v"])]
    if family == "piecewise_orbit":
        idx = (a-b) % 10 if p["orientation"] == "difference" else (a+b) % 10
        return p["orbits"][p["row_classes"][a]][idx]
    if family == "sparse_orbit_exceptions":
        for x, y, value in p["exceptions"]:
            if a == x and b == y:
                return value
        return p["orbit"][_axis(a, b, p["u"], p["v"])]
    raise ValueError("未知数学类别")


def _vector(family: str, p: dict, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    if family == "piecewise_orbit":
        idx = (a-b) % 10 if p["orientation"] == "difference" else (a+b) % 10
        rows = np.asarray(p["orbits"], dtype=np.uint8)
        classes = np.asarray(p["row_classes"], dtype=np.uint8)
        return rows[classes[a], idx]
    orbit = np.asarray(p["orbit"], dtype=np.uint8)
    out = orbit[(p["u"]*a+p["v"]*b) % 10]
    if family == "sparse_orbit_exceptions":
        out = out.copy()
        for x, y, z in p["exceptions"]:
            out[(a == x) & (b == y)] = z
    return out


@dataclass(frozen=True)
class CategoryHypothesis:
    id: str
    family: str
    payload: dict
    levels: int
    source_table_sha256: str
    representation_bits: int
    raw_bits: int
    source_id: str
    comparison_bits: int
    version: str = VERSION

    def __post_init__(self):
        _validate_payload(self.family, self.payload, self.levels)
        if self.version != VERSION or type(self.source_id) is not str or not self.source_id or len(self.source_id) > 1024:
            raise ValueError("版本或来源信息不合法")
        if self.representation_bits != _code_bits(self.family, self.payload, self.levels):
            raise ValueError("描述长度与能力定义不匹配")
        if (type(self.representation_bits) is not int or type(self.raw_bits) is not int
                or self.raw_bits != 100*_bin(self.levels)
                or not 0 < self.representation_bits < self.raw_bits):
            raise ValueError("无效的描述长度")
        if type(self.comparison_bits) is not int or not self.representation_bits < self.comparison_bits <= self.raw_bits:
            raise ValueError("没有发现优于V3.1的紧凑表示")
        if (type(self.source_table_sha256) is not str
                or len(self.source_table_sha256) != 64
                or any(c not in "0123456789abcdef" for c in self.source_table_sha256)):
            raise ValueError("无效的原始表指纹")
        signature = {"family":self.family,"payload":self.payload,"levels":self.levels,
                     "table_sha256":self.source_table_sha256,"version":self.version}
        if self.id != "pl5.v32." + hashlib.sha256(canonical(signature).encode()).hexdigest()[:24]:
            raise ValueError("能力ID不匹配")

    def call(self, a: int, b: int) -> int:
        return _scalar(self.family,self.payload,a,b)

    def vector(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        x, y = np.asarray(a), np.asarray(b)
        if (x.shape != y.shape or not np.issubdtype(x.dtype, np.integer)
                or not np.issubdtype(y.dtype, np.integer)
                or np.any(x < 0) or np.any(x > 9) or np.any(y < 0) or np.any(y > 9)):
            raise ValueError("批量输入形状/类型/数字域错误")
        return _vector(self.family,self.payload,x.astype(np.int64),y.astype(np.int64))

    def table(self) -> np.ndarray:
        return self.vector(GRID_A,GRID_B)

    def certify(self) -> dict:
        reconstructed = self.table()
        if _sha(reconstructed) != self.source_table_sha256:
            raise ValueError("全域真值表SHA不匹配")
        for a in range(10):
            for b in range(10):
                if int(reconstructed[a,b]) != self.call(a,b):
                    raise ValueError("异构标量与向量实现不一致")
        return {"checked_pairs":100,"scalar_numpy_agree":True,"table_sha256":self.source_table_sha256,
                "status":"exact_mathematical_reconstruction"}

    def card(self) -> dict:
        return {"id":self.id,"uacp_version":"v1","version":self.version,
                "kind":"learned_category_hypothesis","family":self.family,
                "description":"自动归纳的有限域数学结构；不代表独立数学公理发明",
                "input_schema":"digit(0..9) x digit(0..9)","output_schema":f"category(0..{self.levels-1})",
                "payload":self.payload,"source_id":self.source_id,
                "source_table_sha256":self.source_table_sha256,
                "description_bits_proxy":self.representation_bits,
                "v31_best_bits_proxy":self.comparison_bits,
                "raw_bits_proxy":self.raw_bits,
                "proof":self.certify(),"status":"research_only",
                "predictive_advantage":"unverified",
                "limitations":"MDL仅为固定代理；表等价不产生彩票开奖的预测信息；禁止自动启用"}


def _hypotheses(t: np.ndarray, levels: int, max_exceptions: int = 5) -> tuple[list[dict], list[dict]]:
    """Generate hypotheses from observed row profiles and modular residuals.

    No expression templates are executed; the family descriptors are learned
    from data and all rejected candidates remain in an auditable trial list.
    """
    proposed, trials = [], []
    for direction in ("difference", "sum"):
        by_profile: dict[tuple[int,...],int] = {}
        row_classes, orbits = [], []
        for a in range(10):
            profile = tuple(int(t[a,(a-j)%10] if direction == "difference" else t[a,(j-a)%10]) for j in range(10))
            if profile not in by_profile:
                by_profile[profile] = len(orbits)
                orbits.append(list(profile))
            row_classes.append(by_profile[profile])
        r = len(orbits)
        # A state-dependent orbit represents a row-driven finite-state transducer.
        bits = 24+1+10*_bin(r)+r*10*_bin(levels)
        trials.append({"hypothesis":"piecewise_orbit","direction":direction,"observed_row_states":r,"bits":bits})
        if 2 <= r <= 3:
            proposed.append({"family":"piecewise_orbit", "payload":{
                "orientation":direction,"row_classes":row_classes,"orbits":orbits},
                "bits":bits,"diagnostic":f"从对齐轨道自动聚类得到{r}种行状态"})
    # Explore a compact family of modular projections, not just the 2 older +/- hypotheses.
    for u in range(1,10):
        for v in range(1,10):
            sums = [[int(t[a,b]) for a in range(10) for b in range(10) if _axis(a,b,u,v)==i]
                    for i in range(10)]
            if not all(sums):
                continue  # non-surjective projection can't be certified as an exact 10-symbol orbit.
            orbit = [max(range(levels),key=lambda z:(row.count(z),-z)) for row in sums]
            mistakes = [(a,b,int(t[a,b])) for a in range(10) for b in range(10)
                        if int(t[a,b]) != orbit[_axis(a,b,u,v)]]
            e = len(mistakes)
            if e == 0:
                proposed.append({"family":"affine_orbit","payload":{"u":u,"v":v,"orbit":orbit},
                                 "bits":24+8+10*_bin(levels),"diagnostic":"归纳广义线性模轨道，精确重建"})
            elif e <= max_exceptions:
                proposed.append({"family":"sparse_orbit_exceptions","payload":{
                    "u":u,"v":v,"orbit":orbit,"exceptions":[list(z) for z in mistakes]},
                    "bits":24+8+10*_bin(levels)+e*(7+_bin(levels)),
                    "diagnostic":f"模轨道加{e}个精确例外点"})
    trials.append({"hypothesis":"affine_and_residual_projections","projections_examined":81,
                   "exact_or_sparse_proposals":sum(p['family'] != 'piecewise_orbit' for p in proposed),
                   "maximum_repair_exceptions":max_exceptions})
    return proposed,trials


def infer_new_categories(table: np.ndarray, *, source_id="unknown", min_saved_bits=1,
                         max_exceptions=5) -> dict:
    t,k = _validated_table(table)
    if type(min_saved_bits) is not int or not 1 <= min_saved_bits <= 200:
        raise ValueError("压缩位数下限非法")
    if type(max_exceptions) is not int or not 0 <= max_exceptions <= 6:
        raise ValueError("最大例外点数非法")
    old,_ = invent_categories(t)
    incumbent = min([100*_bin(k)]+[v.representation_bits for v in old])
    proposals,diagnostics = _hypotheses(t,k,max_exceptions)
    found,discarded = [],[]
    seen_payloads=set()
    for p in sorted(proposals,key=lambda x:(x['bits'],x['family'],canonical(x['payload']))):
        family,desc = p['family'],p['payload']
        if p['bits'] >= incumbent - min_saved_bits + 1:
            discarded.append({"family":family,"reason":"未优于旧类别最简表示或压缩阈值", "bits":p['bits']})
            continue
        # One frozen 100-table can have many mathematically redundant decompositions.
        # Register only the best per discovered family in one study, without discarding logs.
        if family in seen_payloads:
            discarded.append({"family":family,"reason":"同类较长/等价描述被去重", "bits":p['bits']})
            continue
        canonical_desc={"family":family,"payload":desc,"levels":k,"table_sha256":_sha(t),"version":VERSION}
        oid="pl5.v32."+hashlib.sha256(canonical(canonical_desc).encode()).hexdigest()[:24]
        op=CategoryHypothesis(oid,family,desc,k,_sha(t),p['bits'],100*_bin(k),source_id,incumbent)
        op.certify()
        found.append(op)
        seen_payloads.add(family)
    status="compressed_new_family" if found else "no_verified_new_family"
    return {"version":VERSION,"source_id":source_id,"source_sha256":_sha(t),
            "status":status,"raw_bits":100*_bin(k),"old_best_bits":incumbent,
            "hypotheses_tested":len(proposals),"trials":diagnostics,
            "abilities":found,"rejected_summary":{
                "not_better_or_duplicate":len(discarded),
                "examples":discarded[:12]},
            "next_research_task":(None if found else
                "当前候选类别未改善表示：研究新的分组不变量、变换族或对照；不得放宽全表等价门槛"),
            "prediction_advantage":"not_established"}


class HypothesisRegistry:
    """Append-only application-level registry, not a cryptographically trusted timestamp."""
    def __init__(self,path: str|Path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS v32_hypotheses
                         (id TEXT PRIMARY KEY, json TEXT NOT NULL,
                          source_sha TEXT NOT NULL, status TEXT NOT NULL CHECK(status='research_only'),
                          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")

    def register(self,op:CategoryHypothesis)->bool:
        op.certify()
        fields={k:v for k,v in op.__dict__.items()}
        raw=canonical(fields)
        with sqlite3.connect(self.path) as db:
            existing=db.execute("SELECT json FROM v32_hypotheses WHERE id=?",(op.id,)).fetchone()
            if existing:
                previous=json.loads(existing[0])
                if any(v!=previous.get(k) for k,v in fields.items() if k!='source_id'):
                    raise ValueError("重复ID对应不同数学能力定义")
                return False
            db.execute("INSERT INTO v32_hypotheses(id,json,source_sha,status) VALUES(?,?,?,?)",
                       (op.id,raw,op.source_table_sha256,'research_only'))
        return True

    def get(self,oid:str)->CategoryHypothesis:
        with sqlite3.connect(self.path) as db:
            row=db.execute('SELECT json,source_sha,status FROM v32_hypotheses WHERE id=?',(oid,)).fetchone()
        if row is None:raise KeyError(oid)
        if row[2]!='research_only':raise ValueError('未经批准的运行状态')
        op=CategoryHypothesis(**json.loads(row[0]))
        if op.source_table_sha256!=row[1]:raise ValueError('数据记录指纹冲突')
        op.certify()
        return op

    def summary(self)->list[dict]:
        with sqlite3.connect(self.path) as db:
            ids=[x[0] for x in db.execute('SELECT id FROM v32_hypotheses ORDER BY created_at,id')]
        return [{"id":op.id,"family":op.family,"bits":op.representation_bits,
                 "status":"research_only"} for op in (self.get(oid) for oid in ids)]


def study_historical_operators(numbers:list[str], *, maximum=8,
                                registry: str|Path|None=None) -> dict:
    arr=history_array(numbers)
    cutoff=len(arr)-110
    if cutoff<120:raise ValueError("需要至少230期记录：训练前缀和110期未触碰数据")
    original,_=discover(arr[:cutoff],maximum=maximum)
    db=HypothesisRegistry(registry) if registry else None
    cards=[]
    for op in original:
        result=infer_new_categories(op.table_array,source_id=op.identity)
        for ability in result['abilities']:
            cards.append({"parent":op.identity,"card":ability.card(),"inserted":db.register(ability) if db else None})
    return {"version":VERSION,"training_history_sha256":hashlib.sha256(arr[:cutoff].tobytes()).hexdigest(),
            "training_periods":cutoff,"reserved_periods":110,"operators_visited":len(original),
            "new_abilities":len(cards),"abilities":cards,"status":"research_only",
            "prediction_advantage":"not_established"}


def synthetic_fixtures(seed=20261102)->dict[str,np.ndarray]:
    a,b=np.indices((10,10))
    orbit=np.array([0,2,1,2,0,2,1,0,1,2],dtype=np.uint8)
    part1=np.array([1,0,2,0,2,1,1,0,2,1],dtype=np.uint8)
    piece=np.where((a%2)==0,orbit[(a-b)%10],part1[(a-b)%10]).astype(np.uint8)
    affine=orbit[(a+2*b)%10]
    sparse=orbit[(a-b)%10].copy();sparse[1,4]=(int(sparse[1,4])+1)%3;sparse[6,2]=(int(sparse[6,2])+2)%3
    rng=np.random.default_rng(seed)
    noise=rng.integers(0,4,(10,10),dtype=np.uint8)
    noise.ravel()[:4]=np.arange(4)
    return {"two_state_piecewise":piece,"affine_modular":affine,
            "sparse_exception":sparse,"unstructured_random":noise}
