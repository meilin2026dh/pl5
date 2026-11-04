"""V0.8 open Python hypothesis lab.

Untrusted candidate code NEVER executes in the PL5 host Python interpreter.
A Docker container is mandatory for execution; without it the experiment fails closed.
The registry is for research only, distinct from production ranking/approvals.
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tempfile
from typing import Any

MAX_SOURCE = 12000
MAX_CASES = 24
MAX_HISTORY = 1200
N = 100_000
ALLOWED_MATH = {"sqrt", "log", "log1p", "exp", "fabs", "floor", "ceil", "isfinite"}
BANNED_NAMES = {"eval", "exec", "compile", "open", "input", "__import__", "getattr", "setattr",
                "delattr", "globals", "locals", "vars", "dir", "help", "breakpoint", "memoryview",
                "classmethod", "staticmethod", "property", "object", "type", "super", "exit", "quit"}
BANNED_NODE_TYPES = (ast.ImportFrom, ast.ClassDef, ast.AsyncFunctionDef, ast.With, ast.AsyncWith,
                     ast.Try, ast.Raise, ast.Global, ast.Nonlocal, ast.Lambda, ast.Yield, ast.YieldFrom,
                     ast.Await, ast.Delete, ast.NamedExpr)


def json_canon(obj:Any)->str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def utc_now()->str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def inspect_python_source(source:str)->dict:
    """Conservative static triage; NOT a security sandbox. The container is mandatory."""
    if not isinstance(source,str) or not (40<=len(source.encode('utf-8'))<=MAX_SOURCE):
        raise ValueError('算法Python代码长度必须在40B至12KB之间')
    if '\x00' in source:raise ValueError('不允许NUL字符')
    tree=ast.parse(source,filename='candidate.py',mode='exec')
    defs=[]
    for statement in tree.body:
        if isinstance(statement,ast.Import):
            if len(statement.names)!=1 or statement.names[0].name!='math' or statement.names[0].asname:
                raise ValueError('仅允许 import math')
        elif isinstance(statement,ast.FunctionDef):
            defs.append(statement.name)
        else:
            raise ValueError('模块顶层只允许 import math 和函数定义')
    if defs != ['score_batch']:
        raise ValueError('必须且只能定义 score_batch(history, candidates)')
    f=next(x for x in tree.body if isinstance(x,ast.FunctionDef))
    if [x.arg for x in f.args.args] != ['history','candidates'] or f.args.kwonlyargs or f.args.vararg or f.args.kwarg or f.args.defaults:
        raise ValueError('函数签名必须是 score_batch(history, candidates)')
    if not any(isinstance(n,ast.Return) for n in ast.walk(f)):
        raise ValueError('函数必须显式 return')
    nodes=list(ast.walk(tree))
    if len(nodes)>1500:raise ValueError('代码语法树过大')
    for node in nodes:
        if isinstance(node,BANNED_NODE_TYPES):raise ValueError(f'不支持的代码结构: {type(node).__name__}')
        if isinstance(node,ast.Import) and node not in tree.body:
            raise ValueError('函数内部禁止import')
        if isinstance(node,ast.Attribute):
            if not (isinstance(node.value,ast.Name) and (
                (node.value.id=='math' and node.attr in ALLOWED_MATH) or
                (node.value.id!='math' and node.attr in {'append','extend'})
            )):
                raise ValueError('不允许访问对象属性（只允许math白名单函数和列表append/extend）')
        if isinstance(node,ast.Name) and (node.id.startswith('__') or node.id in BANNED_NAMES):
            raise ValueError(f'危险或不支持的名称: {node.id}')
        if isinstance(node,ast.arg) and node.arg.startswith('__'):
            raise ValueError('不允许双下划线形参')
    return {'source_sha256':sha256(source.encode()).hexdigest(), 'ast_nodes':len(nodes),
            'function':'score_batch', 'warning':'静态检查不能证明安全；执行仍需独立容器'}


# Trusted runner is copied into the container together with untrusted candidate code.
# It does not import PL5 modules or touch user records. Only candidate *ranked output* escapes.
RUNNER = r'''import contextlib
import hashlib
import io
import json
import math
import runpy
import sys


def main():
    request=json.load(sys.stdin)
    with contextlib.redirect_stdout(io.StringIO()):
        candidate=runpy.run_path('/work/candidate.py')
    scorer=candidate['score_batch']
    results=[]
    for case in request['cases']:
        history=case['history']
        numbers=case['candidates']
        with contextlib.redirect_stdout(io.StringIO()):
            values=scorer(history,numbers)
        if not isinstance(values,list) or len(values)!=len(numbers):
            raise ValueError('score_batch必须返回与candidates相同长度的list')
        if any(not isinstance(s,(float,int)) or isinstance(s,bool) or not math.isfinite(s) or abs(s)>1e100 for s in values):
            raise ValueError('评分必须为有限数值')
        k=case['k']
        ix=sorted(range(len(numbers)),key=lambda i:(-float(values[i]),numbers[i]))[:k]
        results.append([numbers[i] for i in ix])
    print(json.dumps({'ranked':results},separators=(',',':'),ensure_ascii=False))
if __name__=='__main__':
    main()
'''


def docker_available()->bool:
    exe=shutil.which('docker')
    if not exe:return False
    try:
        probe=subprocess.run([exe,'info','--format','{{.ServerVersion}}'],capture_output=True,
                             text=True,timeout=6,check=False)
        return probe.returncode==0 and bool(probe.stdout.strip())
    except (OSError,subprocess.TimeoutExpired):return False


def _validate_cases(cases:list[dict])->None:
    if not isinstance(cases,list) or not 1<=len(cases)<=MAX_CASES:
        raise ValueError('一次沙箱实验只接受1至24个样本')
    for case in cases:
        history=case.get('history');candidates=case.get('candidates');k=case.get('k')
        if not isinstance(history,list) or len(history)>MAX_HISTORY or not all(isinstance(n,str) and re.fullmatch(r'\d{5}',n) for n in history):
            raise ValueError('历史必须为最多1200个5位号码')
        if not isinstance(candidates,list) or not 1<=len(candidates)<=N or len(set(candidates))!=len(candidates):
            raise ValueError('候选集为空、超限或有重复')
        if not all(isinstance(n,str) and re.fullmatch(r'\d{5}',n) for n in candidates):
            raise ValueError('候选集号码不合法')
        if not isinstance(k,int) or not 1<=k<=min(100,len(candidates)):
            raise ValueError('K必须介于1至min(100,候选数)')


def docker_command(mount_dir:str,image:str='python:3.12-alpine')->list[str]:
    if not re.fullmatch(r'python:3\.12-alpine(?:@[a-z0-9:]+)?',image):
        raise ValueError('只允许预设Python 3.12 alpine运行时（可用digest固定）')
    exe=shutil.which('docker')
    if not exe:raise RuntimeError('缺少Docker；禁止在本机直接执行未知算法')
    return [exe,'run','--rm','-i','--network','none','--read-only',
            '--cap-drop','ALL','--security-opt','no-new-privileges=true',
            '--pids-limit','32','--memory','512m','--cpus','1.0',
            '--user','65534:65534',
            '--tmpfs','/tmp:rw,nosuid,nodev,size=16m',
            '--mount',f'type=bind,source={mount_dir},target=/work,readonly',
            '--workdir','/tmp',image,'python','-I','-B','/work/runner.py']


def run_in_docker(source:str,cases:list[dict],*,timeout=90,image='python:3.12-alpine',run=subprocess.run)->dict:
    static=inspect_python_source(source)
    _validate_cases(cases)
    if not docker_available():
        raise RuntimeError('Docker引擎不可用：拒绝执行外部算法；先安装并启动Docker Desktop')
    if not 5<=timeout<=180:raise ValueError('超时必须介于5至180秒')
    with tempfile.TemporaryDirectory(prefix='pl5_v08_') as d:
        p=Path(d)
        (p/'candidate.py').write_text(source,encoding='utf-8')
        (p/'runner.py').write_text(RUNNER,encoding='utf-8')
        os.chmod(p,0o755)
        os.chmod(p/'candidate.py',0o644)
        os.chmod(p/'runner.py',0o644)
        request=json_canon({'cases':cases})
        command=docker_command(str(p),image)
        proc=run(command,input=request,text=True,capture_output=True,timeout=timeout,check=False)
        if proc.returncode!=0:
            raise RuntimeError(f'隔离实验失败(code={proc.returncode}): '+proc.stderr[-900:])
        if len(proc.stdout)>500_000:raise RuntimeError('沙箱响应超限')
        try:result=json.loads(proc.stdout)
        except json.JSONDecodeError as exc:raise RuntimeError('隔离输出不是有效JSON') from exc
        expected=len(cases)
        if not isinstance(result,dict) or not isinstance(result.get('ranked'),list) or len(result['ranked'])!=expected:
            raise RuntimeError('沙箱输出结构不合格')
        for a,case in zip(result['ranked'],cases):
            if not isinstance(a,list) or len(a)!=case['k'] or len(set(a))!=len(a) or not set(a).issubset(set(case['candidates'])):
                raise RuntimeError('沙箱排名结果不合法')
        return {'ranked':result['ranked'],'static':static,'runtime':image,'container_network':'none',
                'note':'Docker沙箱降低风险，但不等于对恶意代码的绝对安全保证'}


ALL_NUMBERS = [f'{i:05d}' for i in range(N)]


def build_walkforward_cases(draws:list[str],*,k=100,eval_size=8,lookback=200)->list[dict]:
    if not 1<=k<=100 or not 2<=eval_size<=24 or not 20<=lookback<=1200:
        raise ValueError('实验参数超限')
    if not isinstance(draws,list) or len(draws)<eval_size+20 or not all(isinstance(n,str) and re.fullmatch(r'\d{5}',n) for n in draws):
        raise ValueError('开奖历史不够长或格式有误')
    return [{'history':draws[max(0,i-lookback):i], 'candidates':ALL_NUMBERS,'k':k}
            for i in range(len(draws)-eval_size,len(draws))]


def audit_python_candidate(source:str,draws:list[str],*,k=100,eval_size=8,
                           docker_run=run_in_docker)->dict:
    """Experimental rolling holdout only. Repeated search invalidates its confirmatory use."""
    cases=build_walkforward_cases(draws,k=k,eval_size=eval_size)
    result=docker_run(source,cases)
    duplicate=docker_run(source,cases)
    if result['ranked']!=duplicate['ranked']:
        raise RuntimeError('同一输入两次隔离运行输出不一致，复现失败')
    actual=draws[-eval_size:]
    hits=[int(n in chosen) for n,chosen in zip(actual,result['ranked'])]
    expected=eval_size*k/N
    # exact binomial tail for observed hits at fixed horizon
    observed=sum(hits);p=k/N
    tail=sum(math.comb(eval_size,j)*(p**j)*(1-p)**(eval_size-j) for j in range(observed,eval_size+1))
    return {'status':'exploratory_only','source_sha256':sha256(source.encode()).hexdigest(),
            'number_of_draws':eval_size, 'k':k,'hits':observed,'hit_by_draw':hits,
            'expected_fair_hits':expected,'unadjusted_fixed_horizon_p':tail,
            'two_runs_identical':True, 'scored_all_100k':True,
            'must_not_use_as_proof':True,
            'notes':['实验区间可以被重复使用；不是独立封存的前向验证',
                     '没有进行跨算法/搜索次数的多重检验校正',
                     '同一份Python代码的两次运行只检验确定性，不是两套独立实现',
                     '拒绝任何自动加入正式预测引擎的操作']}


class PythonResearchStore:
    def __init__(self,db:sqlite3.Connection):
        self.db=db
        self.db.row_factory=sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS v08_python_candidates (
          id TEXT PRIMARY KEY,document_key TEXT NOT NULL,source TEXT NOT NULL,
          origin TEXT NOT NULL,method_claim TEXT NOT NULL,
          source_sha256 TEXT NOT NULL,created_at TEXT NOT NULL,
          state TEXT NOT NULL DEFAULT 'draft');
        CREATE TABLE IF NOT EXISTS v08_proposal_attempts (
          document_key TEXT NOT NULL,method TEXT NOT NULL,completed_at TEXT NOT NULL,
          PRIMARY KEY(document_key,method));
        CREATE TABLE IF NOT EXISTS v08_source_links (
          document_key TEXT NOT NULL,code_id TEXT NOT NULL,
          PRIMARY KEY(document_key,code_id));
        CREATE TABLE IF NOT EXISTS v08_python_audits (
          id INTEGER PRIMARY KEY AUTOINCREMENT,code_id TEXT NOT NULL,
          data_sha256 TEXT NOT NULL,report_json TEXT NOT NULL,
          report_sha256 TEXT NOT NULL,created_at TEXT NOT NULL);
        ''')
        self.db.commit()

    def add(self,*,document_key:str,source:str,origin:str,method_claim:str):
        if not 1<=len(document_key)<=200:raise ValueError('文献标识缺失')
        if origin not in ('offline_template','llm_opt_in','human','compiler_v22'):
            raise ValueError('未知算法来源')
        if not 10<=len(method_claim)<=1500:raise ValueError('必须说明算法假设与论文复现限制')
        static=inspect_python_source(source)
        cid=static['source_sha256']
        prev=self.db.execute('SELECT document_key,origin FROM v08_python_candidates WHERE id=?',(cid,)).fetchone()
        if not prev:
            self.db.execute('''INSERT INTO v08_python_candidates(id,document_key,source,origin,method_claim,
             source_sha256,created_at) VALUES (?,?,?,?,?,?,?)''',
             (cid,document_key,source,origin,method_claim,cid,utc_now()))
        self.db.execute('INSERT OR IGNORE INTO v08_source_links(document_key,code_id) VALUES(?,?)',
                        (document_key,cid))
        self.db.commit()
        return {'code_id':cid,'new':not bool(prev),'state':'draft','static':static}

    def get(self,cid:str):
        row=self.db.execute('SELECT * FROM v08_python_candidates WHERE id=?',(cid,)).fetchone()
        if row is None:raise KeyError('代码不存在')
        x=dict(row)
        if sha256(x['source'].encode()).hexdigest()!=cid:
            raise ValueError('注册算法内容与SHA256不一致')
        return x

    def has_proposal_attempt(self,document_key:str,method:str)->bool:
        return bool(self.db.execute('SELECT 1 FROM v08_proposal_attempts WHERE document_key=? AND method=?',
                                    (document_key,method)).fetchone())

    def register_proposal_attempt(self,document_key:str,method:str):
        if method not in ('offline_template','llm_opt_in'):
            raise ValueError('不支持的提案模式')
        self.db.execute('INSERT OR IGNORE INTO v08_proposal_attempts VALUES(?,?,?)',
                        (document_key,method,utc_now()))
        self.db.commit()

    def list(self,limit=50):
        return [dict(r) for r in self.db.execute('''SELECT id,document_key,origin,method_claim,
             created_at,state FROM v08_python_candidates ORDER BY created_at DESC LIMIT ?''',(max(1,min(limit,100)),))]

    def audit(self,cid:str,draws:list[str],*,data_digest:str,k=100,eval_size=8,
              official_source='',runner=audit_python_candidate):
        if not re.fullmatch(r'[a-f0-9]{64}',data_digest):raise ValueError('数据摘要不合法')
        candidate=self.get(cid)
        # Fail before container execution on duplicate dataset/evaluation parameters.
        seen=self.db.execute('''SELECT id FROM v08_python_audits WHERE code_id=? AND data_sha256=?''',
                             (cid,data_digest)).fetchone()
        if seen:raise ValueError('同一算法已经针对该历史文件实验，禁止自动重复筛选；请查看已有审计')
        report=runner(candidate['source'],draws,k=k,eval_size=eval_size)
        report['data_source_declaration']=official_source or 'unverified_for_development'
        payload=json_canon(report);d=sha256(payload.encode()).hexdigest()
        self.db.execute('''INSERT INTO v08_python_audits(code_id,data_sha256,report_json,report_sha256,created_at)
                           VALUES(?,?,?,?,?)''',(cid,data_digest,payload,d,utc_now()))
        self.db.execute("UPDATE v08_python_candidates SET state='development_audited' WHERE id=?",(cid,))
        self.db.commit()
        return {'code_id':cid,'report':report,'report_sha256':d,'auto_activated':False}
