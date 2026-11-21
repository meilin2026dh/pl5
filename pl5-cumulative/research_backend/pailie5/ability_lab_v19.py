"""V1.9 goal-directed algorithm capability research laboratory.

No arbitrary Python/JavaScript source is evaluated. Research "programs" are a
bounded, typed JSON expression language interpreted by independent NumPy and
pure-Python evaluators. Engineering reproducibility != predictive advantage.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sqlite3
from typing import Any, Sequence
import numpy as np

from .capability_network import (
    N, Capability, CapabilityRegistry, canonical, check_numbers,
    metric_numpy, metric_python, predict_pattern, sha256,
)

GOALS = {
    'cross_position': '跨位置交互特征',
    'modular_structure': '模运算与数字组合特征',
    'sequential_geometry': '位置序列几何形态',
    'hybrid_features': '非线性混合指标',
}
BINARY = {'add', 'sub', 'mul', 'min', 'max'}
LEAVES = {'sum', 'span', 'odd', 'distinct', 'position', 'constant'}


def validate_expr(expr: Any, *, max_depth: int = 4, max_nodes: int = 31) -> dict:
    """Strict grammar, depth and size bounds; no dynamic access or code eval."""
    counter = 0
    def visit(node: Any, depth: int) -> None:
        nonlocal counter
        counter += 1
        if counter > max_nodes or depth > max_depth or not isinstance(node, dict):
            raise ValueError('表达式深度/节点数超限或格式错误')
        op = node.get('op')
        if op in {'sum','span','odd','distinct'}:
            if set(node) != {'op'}: raise ValueError('叶节点字段无效')
        elif op == 'position':
            if set(node) != {'op','index'} or type(node.get('index')) is not int or not 0 <= node['index'] < 5:
                raise ValueError('位置节点无效')
        elif op == 'constant':
            if set(node) != {'op','value'} or type(node.get('value')) is not int or not -20 <= node['value'] <= 20:
                raise ValueError('常量范围无效')
        elif op in BINARY:
            if set(node) != {'op','left','right'}: raise ValueError('二元节点无效')
            visit(node['left'], depth+1);visit(node['right'],depth+1)
        elif op == 'abs':
            if set(node) != {'op','arg'}:raise ValueError('绝对值节点无效')
            visit(node['arg'],depth+1)
        elif op == 'mod':
            if set(node) != {'op','arg','divisor'} or type(node.get('divisor')) is not int or not 2 <= node['divisor'] <= 29:
                raise ValueError('模数节点无效')
            visit(node['arg'],depth+1)
        else:raise ValueError('未登记的表达式运算符')
    visit(expr,0)
    return json.loads(canonical(expr))


def _digits_numpy(numbers: np.ndarray) -> np.ndarray:
    a=np.asarray(numbers)
    if a.dtype.kind in ('U','S','O'):
        if any(not isinstance(x,str) or len(x)!=5 or not x.isascii() or not x.isdigit() for x in a.tolist()):
            raise ValueError('需要五位数字号码')
        a=a.astype(np.int64)
    if a.dtype.kind not in ('i','u') or np.any((a<0)|(a>=N)):
        raise ValueError('号码必须属于00000—99999')
    return np.stack([(a//k)%10 for k in (10000,1000,100,10,1)],axis=1)


def expression_numpy(numbers: np.ndarray, expr: dict) -> np.ndarray:
    validate_expr(expr)
    d=_digits_numpy(numbers)
    def work(e):
        op=e['op']
        if op=='position':return d[:,e['index']]
        if op=='constant':return np.full(d.shape[0],e['value'],dtype=np.int64)
        if op=='sum':return d.sum(axis=1)
        if op=='span':return d.max(axis=1)-d.min(axis=1)
        if op=='odd':return (d%2).sum(axis=1)
        if op=='distinct':return 1+(np.diff(np.sort(d,axis=1),axis=1)!=0).sum(axis=1)
        if op=='abs':return np.abs(work(e['arg']))
        if op=='mod':return work(e['arg'])%e['divisor']
        a=work(e['left']);b=work(e['right'])
        if op=='add':return a+b
        if op=='sub':return a-b
        if op=='mul':return a*b
        if op=='min':return np.minimum(a,b)
        if op=='max':return np.maximum(a,b)
        raise AssertionError('invalid expression')
    out=np.asarray(work(expr),dtype=np.int64)
    if np.max(np.abs(out))>100_000_000:raise ValueError('输出幅度超限')
    return out


def expression_python(number: str, expr: dict) -> int:
    if not isinstance(number,str) or len(number)!=5 or not number.isascii() or not number.isdigit():
        raise ValueError('号码必须是五位字符串')
    validate_expr(expr)
    d=[int(x) for x in number]
    def work(e):
        op=e['op']
        if op=='position':return d[e['index']]
        if op=='constant':return e['value']
        if op=='sum':return sum(d)
        if op=='span':return max(d)-min(d)
        if op=='odd':return sum(v%2 for v in d)
        if op=='distinct':return len(set(d))
        if op=='abs':return abs(work(e['arg']))
        if op=='mod':return work(e['arg'])%e['divisor']
        a=work(e['left']);b=work(e['right'])
        return {'add':lambda:a+b,'sub':lambda:a-b,'mul':lambda:a*b,
                'min':lambda:min(a,b),'max':lambda:max(a,b)}[op]()
    result=work(expr)
    if abs(result)>100_000_000:raise ValueError('输出幅度超限')
    return result


def feature_signature(values: np.ndarray) -> str:
    """Partition signature: bijective relabellings count as the same feature."""
    _,first,inverse=np.unique(values,return_index=True,return_inverse=True)
    # Canonicalize by first appearance, not numeric label, so bijective
    # transformations do not masquerade as a genuinely different partition.
    order=np.argsort(first)
    ranks=np.empty(len(order),dtype=np.int32)
    ranks[order]=np.arange(len(order),dtype=np.int32)
    return hashlib.sha256(ranks[inverse].astype('<i4').tobytes()).hexdigest()


def propose_expr(goal: str, index: int) -> dict:
    if goal not in GOALS or type(index) is not int or not 0<=index<=500:
        raise ValueError('未知科研目标或提案序号')
    p=index%5;q=(p+1+index//5%4)%5
    if q==p:q=(p+2)%5
    x={'op':'position','index':p};y={'op':'position','index':q}
    s={'op':'sum'};o={'op':'odd'}; span={'op':'span'}
    k=2+(index//5)%13
    variant=(index//65)%4
    if goal=='cross_position':
        return ({'op':'mul','left':x,'right':y} if variant==0 else
                {'op':'abs','arg':{'op':'sub','left':x,'right':y}} if variant==1 else
                {'op':'add','left':{'op':'mul','left':x,'right':y},'right':span} if variant==2 else
                {'op':'mod','arg':{'op':'add','left':{'op':'mul','left':x,'right':y},'right':s},'divisor':k})
    if goal=='modular_structure':
        return ({'op':'mod','arg':{'op':'add','left':s,'right':x},'divisor':k} if variant==0 else
                {'op':'mod','arg':{'op':'mul','left':x,'right':y},'divisor':k} if variant==1 else
                {'op':'mod','arg':{'op':'add','left':{'op':'mul','left':x,'right':y},'right':o},'divisor':k} if variant==2 else
                {'op':'mod','arg':{'op':'sub','left':s,'right':x},'divisor':k})
    if goal=='sequential_geometry':
        return ({'op':'abs','arg':{'op':'sub','left':x,'right':y}} if variant==0 else
                {'op':'mul','left':{'op':'sub','left':x,'right':y},'right':{'op':'sub','left':x,'right':y}} if variant==1 else
                {'op':'add','left':{'op':'abs','arg':{'op':'sub','left':x,'right':y}},'right':span} if variant==2 else
                {'op':'mod','arg':{'op':'abs','arg':{'op':'sub','left':x,'right':y}},'divisor':k})
    return ({'op':'add','left':{'op':'mul','left':x,'right':o},'right':span} if variant==0 else
            {'op':'mod','arg':{'op':'mul','left':s,'right':span},'divisor':k} if variant==1 else
            {'op':'sub','left':{'op':'mul','left':x,'right':span},'right':o} if variant==2 else
            {'op':'mod','arg':{'op':'add','left':{'op':'mul','left':x,'right':y},'right':s},'divisor':k})


def backtest_anti(values: Sequence[int], full_values: np.ndarray, *, window: int=3, trials: int=40, pattern: str="repeat") -> dict:
    """Strictly prequential diagnostics; neither used to tune nor certify prognosis."""
    if window<3 or trials<1:raise ValueError('验证窗口无效')
    if len(values)<window+1:return {'status':'insufficient','periods':0,'reason':'历史样本不足'}
    unique, counts=np.unique(full_values,return_counts=True)
    frequencies={int(u):int(c) for u,c in zip(unique,counts)}
    selected=range(max(window,len(values)-trials),len(values))
    expected=0.0;observed=0;active=0
    for i in selected:
        pp={'name':pattern,'window':window}
        if pattern=='cycle':pp['lag']=2
        pred=predict_pattern(list(values[:i]),pp)
        if not pred['active']:continue
        active+=1
        expected+=frequencies.get(int(pred['predicted']),0)/N
        observed+=int(values[i]==pred['predicted'])
    return {'status':'exploratory','evaluated_periods':len(selected),'active_periods':active,
            'expected_exclusions_under_uniform':round(expected,8),
            'observed_exclusions':observed,
            'predictive_advantage':'NOT_ESTABLISHED',
            'selection_warning':'重复查看/研究选择污染留出集；仅供探索，不当作独立前向证据'}


@dataclass(frozen=True)
class Goal:
    kind: str
    maximum_new: int = 3
    source: str = 'PL5 V1.9 goal-driven discovery (not a source-paper reproduction)'
    pattern: str = 'repeat'
    window: int = 3

    def validate(self):
        if self.kind not in GOALS or type(self.maximum_new) is not int or not 1<=self.maximum_new<=12:
            raise ValueError('科研目标或每轮上限无效')
        if self.pattern not in {'repeat','arithmetic','alternate','cycle'} or type(self.window) is not int or not 3<=self.window<=12:
            raise ValueError('研究模式或窗口无效')
        if self.pattern=='alternate' and self.window<4:raise ValueError('交替模式至少4期')
        if self.pattern=='cycle' and self.window<4:raise ValueError('周期至少4期')
        if len(self.source)>300 or not self.source.strip():raise ValueError('来源标签无效')


class AbilityLab:
    def __init__(self, db_path: str|Path):
        self.path=Path(db_path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path)
        self.db.execute('''CREATE TABLE IF NOT EXISTS ability_proposals_v19(
          id TEXT PRIMARY KEY, goal TEXT NOT NULL, expression TEXT NOT NULL,
          feature_signature TEXT, status TEXT NOT NULL, report TEXT NOT NULL,
          source TEXT NOT NULL, created_at TEXT NOT NULL)''')
        self.db.execute('''CREATE TABLE IF NOT EXISTS ability_cycles_v19(
          key TEXT PRIMARY KEY, config_sha256 TEXT NOT NULL, report TEXT NOT NULL,
          created_at TEXT NOT NULL)''')
        self.db.commit()

    def __enter__(self):return self
    def __exit__(self,*_):self.close()
    def close(self):self.db.close()

    def latest(self,limit:int=20)->dict:
        rows=self.db.execute('SELECT id,goal,status,report FROM ability_proposals_v19 ORDER BY created_at DESC,id DESC LIMIT ?', (limit,)).fetchall()
        return {'total':self.db.execute('SELECT count(*) FROM ability_proposals_v19').fetchone()[0],
                'proposals':[{'id':i,'goal':g,'status':s,'report':json.loads(r)} for i,g,s,r in rows],
                'prediction_advantage':'UNVERIFIED'}

    def run(self, goal:Goal, *, history:Sequence[str]|None=None, cycle_key:str|None=None)->dict:
        goal.validate()
        history=list(history or [])
        if history:check_numbers(history)
        config={'goal':asdict(goal),'history_sha256':sha256(canonical(history))}
        cfg_sha=sha256(canonical(config))
        if cycle_key:
            if len(cycle_key)>128 or not cycle_key.strip():raise ValueError('周期标识无效')
            old=self.db.execute('SELECT config_sha256,report FROM ability_cycles_v19 WHERE key=?',(cycle_key,)).fetchone()
            if old:
                if old[0]!=cfg_sha:raise ValueError('已登记周期配置发生变化，拒绝覆盖')
                return json.loads(old[1])
        reg=CapabilityRegistry(self.path)
        try:
            existing=reg.all()
            # Include native AAN signatures so a new name cannot disguise an old feature.
            universe=np.arange(N,dtype=np.int64)
            fingerprints={}
            for cap in existing.values():
                if cap.op=='metric':
                    fp=feature_signature(metric_numpy(universe,cap.params))
                    fingerprints.setdefault(fp,cap.id)
            rows=[];new=0
            for i in range(501):
                if new>=goal.maximum_new:break
                expr=validate_expr(propose_expr(goal.kind,i))
                key='pl5.expr.'+sha256(canonical(expr))[:20]
                if key in existing:continue
                arr=expression_numpy(universe,expr)
                fp=feature_signature(arr)
                if fp in fingerprints:continue
                # True implementation independence: all 100k values must agree.
                pure=np.fromiter((expression_python(f'{j:05d}',expr) for j in range(N)),dtype=np.int64,count=N)
                if not np.array_equal(arr,pure):raise RuntimeError('双实现差异：禁止入库')
                fingerprints[fp]=key
                metric=Capability(id=key,name='自主生成指标·'+goal.kind,
                    version='1.0.0',op='metric',requires=(),params={'metric':'expr','expr':expr},
                    origin=goal.source,status='research')
                reg.add(metric);existing[key]=metric
                suffix=goal.pattern+'_'+str(goal.window)+(('_2') if goal.pattern=='cycle' else '')
                pattern_key=key+'.pattern_'+suffix
                filter_key=key+'.anti_'+suffix
                pp={'name':goal.pattern,'window':goal.window}
                if goal.pattern=='cycle':pp['lag']=2
                cap_p=Capability(pattern_key,'新指标模式识别', '1.0.0','pattern',(key,),pp,goal.source)
                cap_f=Capability(filter_key,'新指标反延续实验刀', '1.0.0','anti_filter',(key,pattern_key),{},goal.source)
                reg.add(cap_p);reg.add(cap_f)
                existing[pattern_key]=cap_p;existing[filter_key]=cap_f
                hist_vals=expression_numpy(np.asarray(history),expr).tolist() if history else []
                report={'id':key,'filter_id':filter_key,'goal':goal.kind,'expression':expr,
                        'feature_signature':fp,'distinct_values':int(np.unique(arr).size),
                        'full_space_parity':True,'evaluated_numbers':N,
                        'historical_exploration':backtest_anti(hist_vals,arr,window=goal.window,pattern=goal.pattern) if history else {'status':'no_history'},
                        'status':'engineered_research_only','approval':'NOT_AUTOMATIC',
                        'predictive_advantage':'NOT_ESTABLISHED','source':goal.source}
                self.db.execute('INSERT INTO ability_proposals_v19 VALUES (?,?,?,?,?,?,?,?)',
                    (key,goal.kind,canonical(expr),fp,'engineered_research_only',canonical(report),goal.source,
                     datetime.now(timezone.utc).isoformat()))
                self.db.commit()
                new+=1;rows.append({'id':key,'filter_id':filter_key,'feature_signature':fp})
            result={'goal':goal.kind,'created':rows,'count':new,'available_capabilities':len(reg.all()),
                    'cycle_key':cycle_key,'approval':'NOT_AUTOMATIC','predictive_advantage':'NOT_ESTABLISHED',
                    'independence_note':'双实现工程复核不构成中奖彩票预测优势的统计证据'}
            if cycle_key:
                self.db.execute('INSERT INTO ability_cycles_v19 VALUES (?,?,?,?)',
                    (cycle_key,cfg_sha,canonical(result),datetime.now(timezone.utc).isoformat()))
                self.db.commit()
            return result
        finally:reg.close()


def plan_goal(db_path:str|Path, goal:Goal)->dict:
    goal.validate()
    with AbilityLab(db_path) as lab:
        existing=lab.db.execute('SELECT id FROM ability_proposals_v19 WHERE goal=?',(goal.kind,)).fetchall()
        gaps={'existing_engineered':len(existing),'novel_metric_needed':True,
              'requires':['typed_metric_expression','pattern_prediction','anti_filter','independent_validation'],
              'unsupported':['automatic_prediction_certification','arbitrary_external_python_without_container']}
    return {'goal':asdict(goal),'gaps':gaps,'candidate_families':GOALS[goal.kind],
            'execution_policy':'bounded_dsl_independent_implementations_then_research_only',
            'predicted_benefit':'algorithm-diversity_only_not_lottery_probability'}
