"""V0.6 safe algorithm DSL. Never evals model-generated code.

Expressions are typed JSON trees interpreted twice (NumPy and independent scalar
Python).  The emitted Python is a review artifact ONLY; it is never imported or
executed.  This is a deliberately bounded auto-invention MVP.
"""
from __future__ import annotations
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from typing import Any
import numpy as np
from pailie5.pattern_rules import indicator_table

METRICS = ('sum','span','odd_count','unique_count','adjacent_equal','head_sum',
           'tail_sum','max_frequency','mirror_pairs','digit_1','digit_2','digit_3',
           'digit_4','digit_5')
OPS = ('add','sub','absdiff','min','max','mod','mul')
PATTERNS = ('constant','arithmetic','period2','strict_up','strict_down')


def _canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False)


def validate_expr(node:dict,depth=0,count=None):
    if count is None:count=[0]
    count[0]+=1
    if count[0]>15 or depth>3:raise ValueError('公式树超过安全复杂度限制')
    if not isinstance(node,dict) or set(node)-{'kind','name','op','args','value'}:
        raise ValueError('公式节点字段非法')
    if node.get('kind')=='metric':
        if set(node)!={'kind','name'} or node['name'] not in METRICS:
            raise ValueError('指标未授权')
    elif node.get('kind')=='const':
        if set(node)!={'kind','value'} or type(node['value']) is not int or not 1<=node['value']<=17:
            raise ValueError('常量只允许1..17')
    elif node.get('kind')=='op':
        if set(node)!={'kind','op','args'} or node['op'] not in OPS or not isinstance(node['args'],list) or len(node['args'])!=2:
            raise ValueError('运算符不受支持')
        for child in node['args']:validate_expr(child,depth+1,count)
        if node['op']=='mod' and node['args'][1].get('kind')!='const':
            raise ValueError('取模除数必须是正整数常量')
    else:raise ValueError('公式节点类型非法')
    return node


def _calculate(op,a,b):
    if op=='add':return a+b
    if op=='sub':return a-b
    if op=='absdiff':return np.abs(a-b)
    if op=='min':return np.minimum(a,b)
    if op=='max':return np.maximum(a,b)
    if op=='mod':return a % b
    if op=='mul':return a*b
    raise ValueError('未知运算符')


def vector_eval(expr, ids=None):
    validate_expr(expr)
    table=indicator_table()
    def impl(node):
        kind=node['kind']
        if kind=='const':return int(node['value'])
        if kind=='metric':return table[node['name']].astype(np.int64)
        a,b=(impl(x) for x in node['args'])
        return _calculate(node['op'],a,b)
    result=impl(expr)
    if np.isscalar(result):result=np.full(100000,int(result),dtype=np.int64)
    if ids is not None:result=result[np.asarray(ids,dtype=np.int64)]
    return np.asarray(result,dtype=np.int64)


def scalar_eval(expr, number:int)->int:
    """Independent implementation: no NumPy indicator table and no vector evaluator."""
    validate_expr(expr)
    if not 0<=int(number)<100000:raise ValueError('号码索引越界')
    d=[int(x) for x in f'{int(number):05d}']
    counts=[d.count(i) for i in range(10)]
    metrics={
        'sum':sum(d),'span':max(d)-min(d),'odd_count':sum(x%2 for x in d),
        'unique_count':len(set(d)),'adjacent_equal':sum(d[i]==d[i+1] for i in range(4)),
        'head_sum':sum(d[:2]),'tail_sum':sum(d[-2:]),'max_frequency':max(counts),
        'mirror_pairs':int(d[0]==d[4])+int(d[1]==d[3]),
        **{f'digit_{i+1}':d[i] for i in range(5)}}
    def impl(node):
        if node['kind']=='metric':return metrics[node['name']]
        if node['kind']=='const':return node['value']
        a,b=(impl(x) for x in node['args']);op=node['op']
        return {'add':lambda:a+b,'sub':lambda:a-b,'absdiff':lambda:abs(a-b),
                'min':lambda:min(a,b),'max':lambda:max(a,b),'mod':lambda:a%b,
                'mul':lambda:a*b}[op]()
    return int(impl(expr))


def emit_review_code(expr):
    """Produce non-executed review text. Never imported or exec'd by platform."""
    validate_expr(expr)
    def emit(n):
        if n['kind']=='metric':return f'metrics[{n["name"]!r}]'
        if n['kind']=='const':return str(n['value'])
        a,b=(emit(x) for x in n['args']); op=n['op']
        return {'add':f'({a}+{b})','sub':f'({a}-{b})','absdiff':f'abs({a}-{b})',
                'min':f'min({a},{b})','max':f'max({a},{b})','mod':f'({a}%{b})',
                'mul':f'({a}*{b})'}[op]
    return '# REVIEW ONLY: DO NOT EXECUTE UNTRUSTED GENERATED CODE\n'+'def candidate_indicator(metrics):\n    return '+emit(expr)+'\n'

@dataclass(frozen=True)
class InventedAlgorithm:
    formula:dict
    pattern:str
    window:int
    origin:str
    method_note:str

    def validate(self):
        validate_expr(self.formula)
        if self.pattern not in PATTERNS:raise ValueError('不支持的模式')
        if type(self.window) is not int or not 3<=self.window<=8:raise ValueError('窗口不合法')
        if self.pattern=='period2' and self.window<4:raise ValueError('周期2至少需要四期')
        if not isinstance(self.origin,str) or not self.origin or len(self.origin)>200:raise ValueError('来源无效')
        if not isinstance(self.method_note,str) or len(self.method_note)>1500:raise ValueError('研究方法描述无效')
        return self

    def fingerprint(self):
        self.validate()
        return hashlib.sha256(_canonical({'formula':self.formula,'pattern':self.pattern,
                                           'window':self.window}).encode()).hexdigest()[:24]
    def to_dict(self):return asdict(self)


def _metric(name):return {'kind':'metric','name':name}
def _const(value):return {'kind':'const','value':value}
def _op(op,a,b):return {'kind':'op','op':op,'args':[a,b]}


def invent_from_text(text:str,source_key:str,*,limit:int=6)->list[InventedAlgorithm]:
    """Deterministic bounded grammar search based on topic cues, not faithful paper reproduction.

    This is an auto-generated *adaptation hypothesis*, never a claim that the
    cited paper proposes a lottery prediction algorithm.
    """
    if not 1<=limit<=24:raise ValueError('自动生成数量限额1..24')
    if not isinstance(text,str) or not isinstance(source_key,str) or not source_key:raise ValueError('研究材料无效')
    lower=text.lower()[:100000]
    group=(['span','unique_count','max_frequency','mirror_pairs'] if any(x in lower for x in ('graph','network','combinat','entropy'))
           else ['sum','odd_count','head_sum','digit_3','tail_sum'] if any(x in lower for x in ('sequence','time','online','sequential','change'))
           else list(METRICS))
    seed=int(hashlib.sha256((source_key+'|'+lower[:4000]).encode()).hexdigest()[:16],16)
    rng=np.random.default_rng(seed)
    made=[];seen=set()
    for i in range(limit*10):
        x,y=rng.choice(group,size=2,replace=False)
        operation=str(rng.choice(('add','sub','absdiff','min','max','mod','mul')))
        right=_const(int(rng.choice((2,3,5,7,10,11,17)))) if operation=='mod' else _metric(str(y))
        formula=_op(operation,_metric(str(x)),right)
        if i%3==0:
            formula=_op('mod',formula,_const(int(rng.choice((3,5,7,11,17)))))
        pattern=str(rng.choice(PATTERNS));window=int(rng.integers(3,7))
        if pattern=='period2':window=max(4,window)
        algo=InventedAlgorithm(formula,pattern,window,source_key,
            '自动文法组合产生的待证伪迁移假设，来源只提供研究启发；未复现原论文的科学结论')
        fid=algo.fingerprint()
        if fid not in seen:made.append(algo);seen.add(fid)
        if len(made)>=limit:break
    return made
