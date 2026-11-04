"""V0.9: transparent provenance, research protocol, and independent reference kernels.

Faithful paper reproduction is never inferred from mere similarity to a paper.
Only audited human attestation can mark a protocol as 'author-method-verified'.
Only *trusted* built-in examples are executed in-process; untrusted code remains Docker-only.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
import json
import math
import re
import sqlite3
import numpy as np
from typing import Any

ALLOWED_METHODS={'digit_sum','odd_count','transition_count'}

def canon(x:Any)->str:
    return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)

def hash_obj(x:Any)->str:
    return sha256(canon(x).encode('utf-8')).hexdigest()

def _utc()->str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def _check_numbers(items:list[str]):
    if not isinstance(items,list) or len(items)==0 or len(items)>100000:
        raise ValueError('候选号码数量必须为1..100000')
    if any(not isinstance(x,str) or re.fullmatch(r'[0-9]{5}',x) is None for x in items):
        raise ValueError('必须是合法五位号码字符串')


def pure_python_reference(method:str,numbers:list[str])->list[int]:
    """Trusted separately written scalar implementation, NOT generated code."""
    if method not in ALLOWED_METHODS:raise ValueError('未知内置数学方法')
    _check_numbers(numbers)
    answers=[]
    for item in numbers:
        if method=='digit_sum':
            total=0
            for c in item:total+=int(c)
        elif method=='odd_count':
            total=0
            for c in item:
                if int(c)%2: total+=1
        else:
            total=0
            for j in range(4):
                if item[j]!=item[j+1]:total+=1
        answers.append(total)
    return answers


def numpy_reference(method:str,numbers:list[str])->list[int]:
    """Trusted independent vectorized implementation; array arithmetic is distinct from scalar loops."""
    if method not in ALLOWED_METHODS:raise ValueError('未知内置数学方法')
    _check_numbers(numbers)
    data=np.frombuffer(''.join(numbers).encode('ascii'),dtype=np.uint8).reshape(-1,5)-48
    if method=='digit_sum':result=data.sum(axis=1,dtype=np.int64)
    elif method=='odd_count':result=np.count_nonzero(data%2,axis=1)
    else:result=np.count_nonzero(data[:,1:]!=data[:,:-1],axis=1)
    return [int(x) for x in result]


def verify_independent_kernels(method:str,*,exhaustive:bool=True,sample:int=10000)->dict:
    if method not in ALLOWED_METHODS:raise ValueError('未知方法')
    if not 1<=sample<=100000:raise ValueError('样本大小不合法')
    numbers=[f'{i:05d}' for i in range(100000)] if exhaustive else [f'{(i*9973)%100000:05d}' for i in range(sample)]
    py=pure_python_reference(method,numbers)
    npy=numpy_reference(method,numbers)
    failures=[{'number':n,'scalar':a,'numpy':b} for n,a,b in zip(numbers,py,npy) if a!=b][:5]
    return {'method':method,'tested':len(numbers),'equivalent':not failures,'mismatches':failures,
            'result_sha256':hash_obj(py),'independent_implementations':['scalar_Python','NumPy_vectorized'],
            'claim_scope':'Only this built-in feature definition; NOT reproduction of a research paper'}


class ReplicationRegistry:
    def __init__(self,db:sqlite3.Connection):
        self.db=db
        self.db.row_factory=sqlite3.Row
        db.executescript('''
        CREATE TABLE IF NOT EXISTS v09_protocols(
            protocol_id TEXT PRIMARY KEY, document_key TEXT NOT NULL,code_id TEXT NOT NULL,
            method_name TEXT NOT NULL, method_type TEXT NOT NULL,
            paper_locator TEXT NOT NULL, math_assumptions TEXT NOT NULL,
            procedure TEXT NOT NULL, expected_fixture_json TEXT NOT NULL,
            protocol_json TEXT NOT NULL, created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'research_proposed');
        CREATE TABLE IF NOT EXISTS v09_reproductions(
            id INTEGER PRIMARY KEY AUTOINCREMENT, protocol_id TEXT NOT NULL,
            verifier TEXT NOT NULL, result_json TEXT NOT NULL,
            created_at TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS v09_protocol_no_update BEFORE UPDATE ON v09_protocols
        BEGIN SELECT RAISE(ABORT,'immutable_protocol');END;
        CREATE TRIGGER IF NOT EXISTS v09_protocol_no_delete BEFORE DELETE ON v09_protocols
        BEGIN SELECT RAISE(ABORT,'immutable_protocol');END;
        CREATE TRIGGER IF NOT EXISTS v09_reproduction_no_update BEFORE UPDATE ON v09_reproductions
        BEGIN SELECT RAISE(ABORT,'immutable_reproduction');END;
        CREATE TRIGGER IF NOT EXISTS v09_reproduction_no_delete BEFORE DELETE ON v09_reproductions
        BEGIN SELECT RAISE(ABORT,'immutable_reproduction');END;
        ''')
        db.commit()

    def create(self,*,document_key:str,code_id:str,method_name:str,method_type:str,
               paper_locator:str,math_assumptions:str,procedure:str,expected_fixture:dict)->dict:
        if method_type not in ('method_adaptation','claimed_author_reproduction'):
            raise ValueError('必须明确区分迁移假设和论文原方法复现声明')
        if not all(isinstance(x,str) and x.strip() for x in
                   [document_key,code_id,method_name,paper_locator,math_assumptions,procedure]):
            raise ValueError('方法、出处、假设、步骤不能为空')
        if not re.fullmatch(r'[a-f0-9]{64}',code_id):raise ValueError('代码指纹不合法')
        if len(paper_locator)>1200 or len(math_assumptions)>5000 or len(procedure)>5000:
            raise ValueError('研究协议描述超限')
        if not isinstance(expected_fixture,dict):raise ValueError('需要登记参考样例')
        vals=expected_fixture.get('numbers');answers=expected_fixture.get('expected')
        _check_numbers(vals)
        if len(vals)>1000 or not isinstance(answers,list) or len(answers)!=len(vals) or any(
            not isinstance(x,int) or isinstance(x,bool) for x in answers):
            raise ValueError('参考样例需提供数量一致的整数输出')
        if not self.db.execute('SELECT 1 FROM v08_python_candidates WHERE id=?',(code_id,)).fetchone():
            raise ValueError('必须先在V0.8登记待研究算法代码')
        data={'document_key':document_key,'code_id':code_id,'method_name':method_name,
              'method_type':method_type,'paper_locator':paper_locator,
              'math_assumptions':math_assumptions,'procedure':procedure,'expected_fixture':expected_fixture}
        protocol_id=hash_obj(data)
        self.db.execute('''INSERT OR IGNORE INTO v09_protocols
           (protocol_id,document_key,code_id,method_name,method_type,paper_locator,math_assumptions,
             procedure,expected_fixture_json,protocol_json,created_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
           (protocol_id,document_key,code_id,method_name,method_type,paper_locator,
            math_assumptions,procedure,canon(expected_fixture),canon(data),_utc()))
        self.db.commit()
        return {'protocol_id':protocol_id,'status':'research_proposed','faithful_paper_reproduced':False}

    def get(self,protocol_id:str):
        row=self.db.execute('SELECT * FROM v09_protocols WHERE protocol_id=?',(protocol_id,)).fetchone()
        if not row:raise KeyError('研究协议不存在')
        data=dict(row)
        if hash_obj(json.loads(data['protocol_json']))!=protocol_id:
            raise ValueError('研究协议SHA256完整性校验失败')
        return data

    def verify_builtin(self,protocol_id:str,*,exhaustive:bool=True)->dict:
        p=self.get(protocol_id)
        method=p['method_name']
        if method not in ALLOWED_METHODS:raise ValueError('当前仅能自动复现内置方法，任意论文方法需独立人工审查')
        fixture=json.loads(p['expected_fixture_json'])
        expected=fixture['expected']
        first=pure_python_reference(method,fixture['numbers'])
        second=numpy_reference(method,fixture['numbers'])
        match=expected==first==second
        across=verify_independent_kernels(method,exhaustive=exhaustive)
        result={'protocol_id':protocol_id,'fixture_match':match,
                'fixture_expected':expected,'fixture_scalar':first,'fixture_numpy':second,
                'cross_check':across,'engineering_reproduced':bool(match and across['equivalent']),
                'faithful_paper_reproduced':False,
                'limitations':['验证内置特征定义与参考样例；并未运行论文作者的源代码',
                   '未将已登记的开放Python算法与内置特征逐分值比较',
                   '论文的数学假设/数据集/参数仍需要独立核查']}
        self.db.execute('INSERT INTO v09_reproductions(protocol_id,verifier,result_json,created_at) VALUES(?,?,?,?)',
                        (protocol_id,'scalar_vs_numpy',canon(result),_utc()))
        self.db.commit()
        return result

    def list(self,limit:int=30)->list[dict]:
        return [dict(x) for x in self.db.execute('''SELECT protocol_id,document_key,method_name,method_type,
                    status,created_at FROM v09_protocols ORDER BY created_at DESC LIMIT ?''',(min(100,max(1,limit)),))]
