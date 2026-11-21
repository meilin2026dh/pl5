"""PL5 V1.8 Algorithmic Ability Network (AAN).

A versioned, typed, *non-executing* algorithm capability registry. Discovery
proposes bounded compositions of approved built-in operators; it never imports
untrusted code or promotes prediction claims.  All results are experimental.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import hashlib
import json
import re
import sqlite3

import numpy as np

N = 100_000
VALID_OPS = {"metric", "pattern", "anti_filter", "merge_masks"}
METRICS = {"sum", "span", "odd_count", "distinct_count", "sum_mod", "position_digit", "position_diff", "inversions", "expr", "learned_primitive"}
PATTERNS = {"repeat", "arithmetic", "alternate", "cycle"}
STATUS = {"research", "engineered", "review_pending", "revoked"}
OUTPUTS = {"metric": "series<int>", "pattern": "pattern_prediction", "anti_filter": "mask<100000>", "merge_masks": "mask<100000>"}


def canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf8")).hexdigest()


def check_numbers(numbers: Iterable[str]) -> list[str]:
    values = list(numbers)
    if not values or len(values) > 10_000:
        raise ValueError("历史号码必须有1—10000条")
    if any(not isinstance(x, str) or re.fullmatch(r"[0-9]{5}", x) is None for x in values):
        raise ValueError("历史号码必须是保留前导零的五位数字")
    return values


def _params(op: str, params: dict) -> dict:
    if not isinstance(params, dict):
        raise ValueError("算法参数必须是对象")
    if op == "metric":
        metric = params.get("metric")
        if metric not in METRICS:
            raise ValueError("指标运算符未登记")
        allowed = {"metric"}
        if metric == "learned_primitive":
            allowed |= {"positions", "levels", "table", "train_count", "train_fingerprint"}
            pos, levels, table = params.get("positions"), params.get("levels"), params.get("table")
            if (not isinstance(pos,list) or len(pos)!=2 or any(type(x) is not int for x in pos)
                or not 0<=pos[0]<pos[1]<=4 or type(levels) is not int or levels not in (3,4)
                or not isinstance(table,list) or len(table)!=100
                or any(type(x) is not int or not 0<=x<levels for x in table)
                or len(set(table))!=levels or type(params.get("train_count")) is not int
                or not 120<=params["train_count"]<=5000
                or not isinstance(params.get("train_fingerprint"),str)
                or re.fullmatch(r"[0-9a-f]{64}", params["train_fingerprint"]) is None):
                raise ValueError("学习型二元算子需要已校验的10×10有限运算表")
        if metric == "expr":
            from .ability_lab_v19 import validate_expr
            validate_expr(params.get("expr"))
            allowed.add("expr")
        if metric == "sum_mod":
            m = params.get("mod")
            if type(m) is not int or not 2 <= m <= 29:
                raise ValueError("模数必须为2—29的整数")
            allowed.add("mod")
        if metric in {"position_digit", "position_diff"}:
            p = params.get("position")
            if type(p) is not int or not 0 <= p < 5:
                raise ValueError("位置必须为0—4")
            allowed.add("position")
        if metric == "position_diff":
            p2 = params.get("other_position")
            if type(p2) is not int or not 0 <= p2 < 5 or p2 == params["position"]:
                raise ValueError("第二位置必须不同且属于0—4")
            allowed.add("other_position")
        if set(params) != allowed:
            raise ValueError("指标参数字段不符")
    elif op == "pattern":
        name = params.get("name")
        window = params.get("window")
        if name not in PATTERNS or type(window) is not int or not 3 <= window <= 20:
            raise ValueError("模式类型或观察窗口无效")
        if name == "alternate" and window < 4:
            raise ValueError("交替模式至少4期")
        if name == "cycle":
            lag = params.get("lag")
            if type(lag) is not int or not 2 <= lag <= 6 or window < 2 * lag:
                raise ValueError("周期检测需要至少2个完整周期")
            if set(params) != {"name", "window", "lag"}:
                raise ValueError("周期参数无效")
        elif set(params) != {"name", "window"}:
            raise ValueError("模式参数无效")
    elif op in {"anti_filter", "merge_masks"}:
        if params:
            raise ValueError("组合运算不允许额外参数")
    else:
        raise ValueError("运算符不受支持")
    return params.copy()


@dataclass(frozen=True)
class Capability:
    id: str
    name: str
    version: str
    op: str
    requires: tuple[str, ...]
    params: dict
    origin: str
    status: str = "research"
    evidence: str = "unverified"
    limitations: str = "仅供实验；未证实优于公平随机基线"

    @property
    def output_type(self) -> str:
        return OUTPUTS[self.op]

    def card(self) -> dict:
        return {
            **asdict(self), "requires": list(self.requires),
            "output_type": self.output_type,
            "input_type": {"metric": "history<five_digits>", "pattern": "series<int>",
                           "anti_filter": "series<int> + pattern_prediction", "merge_masks": "mask[]"}[self.op],
            "execution_policy": "allowlisted_builtin_only",
            "predictive_status": "UNVERIFIED",
        }


def validate(cap: Capability, existing: dict[str, Capability]) -> None:
    if not isinstance(cap, Capability) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,119}", cap.id):
        raise ValueError("能力ID格式不正确")
    if not cap.name or len(cap.name) > 120 or cap.version != "1.0.0":
        raise ValueError("名称或协议版本无效")
    if cap.op not in VALID_OPS or cap.status not in STATUS:
        raise ValueError("运算类型或状态不合法")
    if not cap.origin or len(cap.origin) > 300 or cap.evidence != "unverified":
        raise ValueError("来源必须存在，预测证据不得自我认证")
    if not cap.limitations or len(cap.limitations) > 500:
        raise ValueError("必须声明算法限制")
    _params(cap.op, cap.params)
    if cap.id in existing:
        if cap.card() == existing[cap.id].card():
            return
        raise ValueError("同名能力已存在且内容不同，必须另建版本")
    if len(cap.requires) != len(set(cap.requires)):
        raise ValueError("依赖不能重复")
    if any(dep not in existing for dep in cap.requires):
        raise ValueError("缺少依赖，或依赖含有循环/未来节点")
    kinds = [existing[r].op for r in cap.requires]
    if cap.op == "metric" and kinds:
        raise ValueError("指标为独立原子运算，不依赖其他算法")
    if cap.op == "pattern" and kinds != ["metric"]:
        raise ValueError("模式必须恰好依赖一个指标")
    if cap.op == "anti_filter" and (len(kinds) != 2 or kinds != ["metric", "pattern"] or
                                     existing[cap.requires[1]].requires != (cap.requires[0],)):
        raise ValueError("反延续必须依赖同源指标和其模式")
    if cap.op == "merge_masks" and (len(kinds) < 2 or any(k not in ("anti_filter", "merge_masks") for k in kinds)):
        raise ValueError("组合过滤至少依赖两条掩码")
    # Semantic duplicate detection, without claiming same output -> same mathematics.
    fingerprint = sha256(canonical([cap.op, cap.params, list(cap.requires)]))
    for other in existing.values():
        if sha256(canonical([other.op, other.params, list(other.requires)])) == fingerprint:
            raise ValueError("已有相同运算能力：" + other.id)


class CapabilityRegistry:
    """Versioned SQLite catalog. Existing entries are append-only and never executable scripts."""
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS capabilities(
            id TEXT PRIMARY KEY, payload TEXT NOT NULL, sha256 TEXT NOT NULL,
            registered_at TEXT NOT NULL)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS runs(
            id TEXT PRIMARY KEY, target TEXT NOT NULL, history_sha256 TEXT NOT NULL,
            report_json TEXT NOT NULL, created_at TEXT NOT NULL)""")
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def all(self) -> dict[str, Capability]:
        result = {}
        for key, raw, digest in self.db.execute("SELECT id,payload,sha256 FROM capabilities ORDER BY id"):
            if sha256(raw) != digest:
                raise RuntimeError("算法说明书内容完整性检查失败：" + key)
            payload = json.loads(raw)
            payload["requires"] = tuple(payload["requires"])
            result[key] = Capability(**payload)
        return result

    def add(self, cap: Capability) -> bool:
        entries = self.all()
        validate(cap, entries)
        if cap.id in entries:
            return False
        raw = canonical(asdict(cap))
        self.db.execute("INSERT INTO capabilities VALUES(?,?,?,?)",
                        (cap.id, raw, sha256(raw), datetime.now(timezone.utc).isoformat()))
        self.db.commit()
        return True

    def graph(self) -> dict:
        items = self.all()
        return {
            "count": len(items),
            "nodes": [x.card() for x in items.values()],
            "edges": [{"from": dep, "to": cap.id} for cap in items.values() for dep in cap.requires],
            "status": "experimental_catalog_only",
        }

    def plan(self, target: str) -> list[Capability]:
        caps = self.all()
        if target not in caps:
            raise KeyError("能力未登记：" + target)
        seen, ordered = set(), []
        def visit(key: str):
            if key in seen:
                return
            seen.add(key)
            for dep in caps[key].requires:
                visit(dep)
            ordered.append(caps[key])
        visit(target)
        return ordered

    def gaps(self, target_op: str) -> dict:
        if target_op not in VALID_OPS:
            raise ValueError("未知目标能力")
        items = self.all()
        return {"target_op": target_op,
                "available": [x.id for x in items.values() if x.op == target_op],
                "missing": not any(x.op == target_op for x in items.values()),
                "proposal": "使用受限运算符组合创建实验能力，不自动批准或执行外部源码"}

    def save_run(self, target: str, history: list[str], report: dict) -> str:
        h = sha256(canonical(history))
        key = sha256(canonical([target, h, report["mask_sha256"]]))
        self.db.execute("INSERT OR IGNORE INTO runs VALUES (?,?,?,?,?)",
                        (key, target, h, canonical(report), datetime.now(timezone.utc).isoformat()))
        self.db.commit()
        return key


def metric_numpy(numbers: np.ndarray, params: dict) -> np.ndarray:
    """Compute over either a list of five-digit strings or full integer IDs."""
    n = np.asarray(numbers)
    if n.dtype.kind in ('U','S','O'):
        if any(not isinstance(x, str) or not re.fullmatch(r'[0-9]{5}',x) for x in n.tolist()):
            raise ValueError('无效的五位号码')
        n = n.astype(np.int64)
    if n.dtype.kind not in ('i','u') or np.any((n < 0) | (n >= N)):
        raise ValueError('号码范围无效')
    d = np.stack([(n // (10**p)) % 10 for p in (4,3,2,1,0)],axis=1)
    metric = params['metric']
    if metric == 'sum': return d.sum(axis=1)
    if metric == 'span': return d.max(axis=1)-d.min(axis=1)
    if metric == 'odd_count': return (d % 2).sum(axis=1)
    if metric == 'distinct_count': return 1 + (np.diff(np.sort(d,axis=1),axis=1) != 0).sum(axis=1)
    if metric == 'sum_mod': return d.sum(axis=1) % params['mod']
    if metric == 'position_digit': return d[:,params['position']]
    if metric == 'position_diff': return d[:,params['position']] - d[:,params['other_position']]
    if metric == 'inversions': return sum((d[:,i] > d[:,j]).astype(np.int64)
                                           for i in range(5) for j in range(i+1,5))
    if metric == 'learned_primitive':
        p,q=params['positions']
        table=np.asarray(params['table'],dtype=np.uint8).reshape(10,10)
        return table[d[:,p],d[:,q]]
    if metric == 'expr':
        from .ability_lab_v19 import expression_numpy
        return expression_numpy(numbers, params['expr'])
    raise ValueError('未支持的指标')


def metric_python(number: str, params: dict) -> int:
    d = [int(x) for x in number]
    m = params['metric']
    if m == 'sum': return sum(d)
    if m == 'span': return max(d)-min(d)
    if m == 'odd_count': return sum(x%2 for x in d)
    if m == 'distinct_count': return len(set(d))
    if m == 'sum_mod': return sum(d)%params['mod']
    if m == 'position_digit': return d[params['position']]
    if m == 'position_diff': return d[params['position']] - d[params['other_position']]
    if m == 'inversions': return sum(d[i]>d[j] for i in range(5) for j in range(i+1,5))
    if m == 'learned_primitive':
        p,q=params['positions']
        return params['table'][int(number[p])*10+int(number[q])]
    if m == 'expr':
        from .ability_lab_v19 import expression_python
        return expression_python(number, params['expr'])
    raise ValueError('指标不存在')


def predict_pattern(values: list[int], params: dict) -> dict:
    w, typ = params['window'], params['name']
    if len(values) < w:
        return {"active":False,"reason":"insufficient_history", "predicted":None}
    seq = values[-w:]
    predicted = None
    if typ == 'repeat' and len(set(seq)) == 1:
        predicted=seq[-1]
    elif typ == 'arithmetic':
        diff=seq[1]-seq[0]
        if diff != 0 and all(seq[i]-seq[i-1]==diff for i in range(2,w)):
            predicted=seq[-1]+diff
    elif typ == 'alternate' and seq[0]!=seq[1] and all(seq[i]==seq[i%2] for i in range(w)):
        predicted=seq[w%2]
    elif typ == 'cycle':
        lag=params['lag']
        if all(seq[i]==seq[i-lag] for i in range(lag,w)) and len(set(seq[:lag]))>1:
            predicted=seq[-lag]
    return {"active":predicted is not None,"reason":typ if predicted is not None else "pattern_absent",
            "predicted":predicted,"observed":seq}


def run_pipeline(registry: CapabilityRegistry, target: str, history: Iterable[str],
                 *, audit_samples: int = 200, return_mask: bool = False) -> dict:
    rows = check_numbers(history)
    plan = registry.plan(target)
    products: dict[str,Any] = {}
    universal = np.arange(N, dtype=np.int64)
    diagnostics=[]
    for item in plan:
        if item.status == 'revoked':
            raise ValueError('已撤销能力不得执行：'+item.id)
        if item.op == 'metric':
            if item.params['metric']=='learned_primitive':
                train_count=item.params['train_count']
                if len(rows)<train_count:
                    raise ValueError('此新算子的学习截止期晚于本次历史回放截止，禁止前视泄漏')
                prefix=np.array([[ord(c)-48 for c in num] for num in rows[:train_count]],dtype=np.uint8)
                if hashlib.sha256(prefix.tobytes()).hexdigest()!=item.params['train_fingerprint']:
                    raise ValueError('研究数据前缀与训练时不一致，禁止复用新算子')
            values = metric_numpy(np.asarray(rows), item.params).tolist()
            if audit_samples:
                pick=np.linspace(0,N-1,min(audit_samples,N),dtype=int)
                predicted=metric_numpy(pick,item.params)
                independently=[metric_python(f'{int(n):05d}', item.params) for n in pick]
                if not np.array_equal(predicted,independently):
                    raise RuntimeError('NumPy/纯Python指标复现不一致')
            products[item.id] = values
            diagnostics.append({'id':item.id,'op':'metric','series_tail':values[-10:]})
        elif item.op == 'pattern':
            pred=predict_pattern(products[item.requires[0]],item.params)
            products[item.id] = pred
            diagnostics.append({'id':item.id,'op':'pattern',**pred})
        elif item.op == 'anti_filter':
            metric_id,pattern_id=item.requires
            pred=products[pattern_id]
            mask=(metric_numpy(universal,registry.all()[metric_id].params)==pred['predicted']) if pred['active'] else np.zeros(N,dtype=bool)
            products[item.id] = mask
            diagnostics.append({'id':item.id,'op':'anti_filter','excluded':int(mask.sum())})
        elif item.op == 'merge_masks':
            mask=np.logical_or.reduce([products[d] for d in item.requires])
            products[item.id]=mask
            diagnostics.append({'id':item.id,'op':'merge_masks','excluded':int(mask.sum())})
    if plan[-1].op not in ('anti_filter','merge_masks'):
        return {'target':target,'kind':plan[-1].op,'output':products[target], 'steps':diagnostics,
                'predictive_advantage':'NOT_ESTABLISHED'}
    mask=products[target]
    packed=np.packbits(mask.astype(np.uint8),bitorder='little').tobytes()
    report={'target':target,'execution_plan':[x.id for x in plan],
            'excluded':int(mask.sum()),'kept':N-int(mask.sum()),
            'mask_sha256':hashlib.sha256(packed).hexdigest(),
            'fair_random_coverage':1-float(mask.mean()),'steps':diagnostics,
            'predictive_advantage':'NOT_ESTABLISHED',
            'qualification':'历史模式反延续是待检验假设，不能将随机模式罕见性直接解释为下一期概率更小'}
    report['receipt_id']=registry.save_run(target,rows,report)
    if return_mask:
        report['_excluded_mask']=np.array(mask,dtype=bool,copy=True)
    return report


def bootstrap(registry: CapabilityRegistry) -> list[str]:
    created=[]
    for metric,params in [('sum',{}),('span',{}),('odd_count',{}),('distinct_count',{}),
                          ('sum_mod',{'mod':3}),('position_digit',{'position':0}),
                          ('position_diff',{'position':0,'other_position':4}),('inversions',{})]:
        key='pl5.metric.'+metric+('_'+str(params.get('mod')) if 'mod' in params else '')
        cap=Capability(key,'基础指标：'+metric,'1.0.0','metric',(),{'metric':metric,**params},'PL5内置/五序指标研究')
        if registry.add(cap):created.append(key)
    return created


def grow(registry: CapabilityRegistry, *, limit: int=5) -> list[dict]:
    """Deterministic bounded capability creation; avoids duplicating prior proposals."""
    if type(limit) is not int or not 1<=limit<=100:
        raise ValueError('单轮增长额度1—100')
    bootstrap(registry)
    accepted=[]
    existing=registry.all()
    # Expand the finite, reviewable metric grammar only after core candidates are exhausted.
    if all(f'{c.id}.anti_{name}_{window}'+(f'_{lag}' if lag else '') in existing
           for c in existing.values() if c.op=='metric'
           for name,window,lag in [('repeat',3,None),('arithmetic',3,None),('alternate',4,None),('cycle',4,2),('repeat',5,None),('arithmetic',4,None)]):

        # New variants are not automatically granted predictive standing.
        proposals = []
        for mod in range(2,30):
            proposals.append((f'pl5.metric.sum_mod_{mod}', {'metric':'sum_mod','mod':mod}))
        for pos in range(5):
            proposals.append((f'pl5.metric.position_digit_{pos}', {'metric':'position_digit','position':pos}))
        for pos in range(5):
            for other in range(5):
                if pos != other:
                    proposals.append((f'pl5.metric.position_diff_{pos}_{other}',
                                      {'metric':'position_diff','position':pos,'other_position':other}))
        for key, params in proposals:
            if key in existing or any(x.op=='metric' and x.params==params for x in existing.values()):
                continue
            c=Capability(key,'衍生指标：'+key.rsplit('.',1)[-1],'1.0.0','metric',(),params,'AAN受限参数化创新')
            registry.add(c)
            existing[key]=c
            break  # At most one new primitive family per research cycle.
    metrics=sorted((c for c in existing.values() if c.op=='metric'),
                   key=lambda x: (['sum','span','odd_count','distinct_count','sum_mod',
                                   'position_digit','position_diff','inversions','expr','learned_primitive'].index(x.params['metric']), x.id))
    for metric in metrics:
        for name,window,lag in [('repeat',3,None),('arithmetic',3,None),('alternate',4,None),('cycle',4,2),('repeat',5,None),('arithmetic',4,None)]:
            if len(accepted)>=limit: return accepted
            suffix=f'{name}_{window}'+(f'_{lag}' if lag else '')
            pid=metric.id+'.pattern_'+suffix
            fid=metric.id+'.anti_'+suffix
            if fid in existing:continue
            ps={'name':name,'window':window}
            if lag:ps['lag']=lag
            p=Capability(pid,f'{metric.name}·{name}({window}期)','1.0.0','pattern',(metric.id,),ps,'AAN受限自创策略')
            f=Capability(fid,f'{metric.name}·{name}反延续','1.0.0','anti_filter',(metric.id,pid),{},'AAN受限自创策略')
            if pid not in existing:
                registry.add(p);existing[pid]=p
            registry.add(f);existing[fid]=f
            accepted.append({'id':fid,'depends_on':[metric.id,pid],'research_only':True})
    return accepted


def research_knife(registry: CapabilityRegistry, target: str, history: Iterable[str]):
    """Experimental-only ESSE knife, requiring explicit `mode='explore'`.

    Deliberately does not return an approval token and cannot set strict mode.
    """
    from .sculpting import Knife
    report=run_pipeline(registry,target,history,return_mask=True)
    excluded=report.pop('_excluded_mask')
    return Knife(key=target,label=target,excluded=excluded,group='aan-experimental',
                 source='AAN-experiment',evidence='unverified'),report
