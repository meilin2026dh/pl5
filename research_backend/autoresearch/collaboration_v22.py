"""PL5 V2.2: bounded multi-role algorithm authoring and falsifiable cross-runtime checks.

No generated/untrusted source is executed in this host interpreter. The compiler
only emits audited finite-family templates. Actual runtime checks require two
separate Docker containers (CPython and Node), explicit consent, and are NOT a
faithful reproduction of source papers nor evidence of lottery predictability.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import math
import re
import shutil
import sqlite3
import subprocess
import tempfile
from typing import Callable

from .council_v21 import ResearchCouncil
from .paper_factory_v20 import _canon, _digest
from .python_lab_v08 import inspect_python_source

FAMILIES = ('digit_sum', 'span', 'adjacent_energy', 'lag_overlap', 'digit_frequency')
CAPACITY = 100_000
IMAGE_PY = 'python:3.12-alpine'
IMAGE_JS = 'node:24-alpine'
MAX_STDOUT = 4_000_000


def _source_pair(family: str) -> tuple[str, str, str]:
    """Two structurally distinct Python encodings + one JS implementation.

    Formulas were independently specified by developers, not copied from a paper.
    Source is kept in the evidence record and must not be considered novel.
    """
    if family not in FAMILIES:
        raise ValueError('不支持的研究能力类型；不能凭空捏造论文方法')
    py_primary = {
        'digit_sum': '''def score_batch(history, candidates):
    return [sum(int(ch) for ch in number) for number in candidates]
''',
        'span': '''def score_batch(history, candidates):
    result = []
    for number in candidates:
        digits = [int(ch) for ch in number]
        result.append(max(digits) - min(digits))
    return result
''',
        'adjacent_energy': '''def score_batch(history, candidates):
    result = []
    for number in candidates:
        d = [int(ch) for ch in number]
        result.append(sum(abs(d[i] - d[i - 1]) for i in range(1, 5)))
    return result
''',
        'lag_overlap': '''def score_batch(history, candidates):
    if not history:
        return [0 for n in candidates]
    previous = history[-1]
    return [sum(1 for i in range(5) if n[i] == previous[i]) for n in candidates]
''',
        'digit_frequency': '''def score_batch(history, candidates):
    table = [[1 for d in range(10)] for p in range(5)]
    for n in history[-120:]:
        for p in range(5):
            table[p][int(n[p])] += 1
    return [sum(table[p][int(n[p])] for p in range(5)) for n in candidates]
''',
    }[family]
    py_secondary = {
        'digit_sum': '''def score_batch(history, candidates):
    scores = []
    for n in candidates:
        acc = 0
        for j in range(5):
            acc = acc + ord(n[j]) - 48
        scores.append(acc)
    return scores
''',
        'span': '''def score_batch(history, candidates):
    output = []
    for n in candidates:
        lo = 10
        hi = -1
        for c in n:
            x = ord(c) - 48
            if x < lo:
                lo = x
            if x > hi:
                hi = x
        output.append(hi - lo)
    return output
''',
        'adjacent_energy': '''def score_batch(history, candidates):
    scores = []
    for n in candidates:
        amount = 0
        old = ord(n[0]) - 48
        for i in range(1, 5):
            new = ord(n[i]) - 48
            amount += abs(old - new)
            old = new
        scores.append(amount)
    return scores
''',
        'lag_overlap': '''def score_batch(history, candidates):
    output = []
    for n in candidates:
        if len(history) == 0:
            output.append(0)
            continue
        hits = 0
        for j in range(5):
            if history[len(history) - 1][j] == n[j]:
                hits += 1
        output.append(hits)
    return output
''',
        'digit_frequency': '''def score_batch(history, candidates):
    counts = [[1] * 10 for i in range(5)]
    for n in history[max(0, len(history) - 120):]:
        for j in range(5):
            digit = ord(n[j]) - 48
            counts[j][digit] = counts[j][digit] + 1
    output = []
    for n in candidates:
        value = 0
        for j in range(5):
            value += counts[j][ord(n[j]) - 48]
        output.append(value)
    return output
''',
    }[family]
    js = {
        'digit_sum': '''function scoreBatch(history, candidates) {
  return candidates.map(n => [...n].reduce((total, c) => total + Number(c), 0));
}''',
        'span': '''function scoreBatch(history, candidates) {
  return candidates.map(n => { const d = Array.from(n, Number); return Math.max(...d) - Math.min(...d); });
}''',
        'adjacent_energy': '''function scoreBatch(history, candidates) {
  return candidates.map(n => {let total=0; for(let j=1;j<5;j++) total+=Math.abs(Number(n[j])-Number(n[j-1])); return total;});
}''',
        'lag_overlap': '''function scoreBatch(history, candidates) {
  const prev=history.length ? history[history.length-1] : null;
  return candidates.map(n => {if(!prev) return 0;let hits=0;for(let i=0;i<5;i++){if(n[i]===prev[i])hits++;}return hits;});
}''',
        'digit_frequency': '''function scoreBatch(history, candidates) {
  const counts = Array.from({length:5},()=>Array(10).fill(1));
  for(const value of history.slice(-120)) for(let j=0;j<5;j++) counts[j][Number(value[j])]++;
  return candidates.map(n => {let score=0;for(let j=0;j<5;j++)score+=counts[j][Number(n[j])];return score;});
}''',
    }[family]
    inspect_python_source(py_primary)
    inspect_python_source(py_secondary)
    if sha256(py_primary.encode()).digest() == sha256(py_secondary.encode()).digest():
        raise AssertionError('主/参考代码重复')
    return py_primary, py_secondary, js


def suggest_family(method: str) -> str | None:
    """Heuristic lead classification, not a claim that a paper uses this method."""
    txt = method.lower()
    if any(x in txt for x in ('markov', 'transition', '时序', '转移', 'lag', '依赖')):
        return 'lag_overlap'
    if any(x in txt for x in ('frequency', 'dirichlet', '频次', '频率', '热度')):
        return 'digit_frequency'
    if any(x in txt for x in ('difference', 'adjacent', '相邻差', '差分')):
        return 'adjacent_energy'
    if any(x in txt for x in ('spread', 'span', '跨度')):
        return 'span'
    if any(x in txt for x in ('digit sum', '和值', 'sum')):
        return 'digit_sum'
    return None


PY_RUNNER = '''import json,math,runpy,sys,contextlib,io
req=json.load(sys.stdin)
with contextlib.redirect_stdout(io.StringIO()):
    scorer=runpy.run_path('/work/algorithm.py')['score_batch']
output=[]
for case in req['cases']:
    with contextlib.redirect_stdout(io.StringIO()):
        s=scorer(case['history'],case['candidates'])
    if not isinstance(s,list) or len(s)!=len(case['candidates']):
        raise ValueError('invalid scores shape')
    if any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>1e9 for x in s):
        raise ValueError('invalid scores values')
    output.append(s)
print(json.dumps({'scores':output},separators=(',',':'),allow_nan=False))
'''
JS_RUNNER = '''const fs=require('node:fs');
const req=JSON.parse(fs.readFileSync(0,'utf8'));
const {scoreBatch}=require('/work/algorithm.cjs');
const result=[];
for(const c of req.cases){
 const values=scoreBatch(c.history,c.candidates);
 if(!Array.isArray(values)||values.length!==c.candidates.length||values.some(x=>typeof x!=='number'||!Number.isFinite(x)||Math.abs(x)>1e9)) throw Error('bad scores');
 result.push(values);
}
process.stdout.write(JSON.stringify({scores:result}));
'''


def _validate_cases(cases: list[dict]) -> None:
    if not isinstance(cases, list) or not 1 <= len(cases) <= 12:
        raise ValueError('每次只允许1—12组反例')
    total = 0
    for c in cases:
        h, n = c.get('history'), c.get('candidates')
        if not isinstance(h, list) or len(h) > 1200 or not isinstance(n, list) or not 1 <= len(n) <= CAPACITY:
            raise ValueError('历史或候选规模越界')
        if (not all(type(x) is str and re.fullmatch('[0-9]{5}', x) for x in h+n)
                or len(set(n)) != len(n)):
            raise ValueError('号码格式不正确或候选有重复')
        total += len(n)
    if total > 130_000:
        raise ValueError('反例总候选数量超过130000')


def _run_container(source: str, cases: list[dict], language: str, *, timeout: int = 90) -> list[list[float]]:
    _validate_cases(cases)
    if not 5 <= timeout <= 180:
        raise ValueError('沙箱超时限制无效')
    if language not in ('python','node'):
        raise ValueError('不支持的沙箱语言')
    exe = shutil.which('docker')
    if not exe:
        raise RuntimeError('没有Docker：禁止在宿主机执行生成代码')
    probe = subprocess.run([exe,'info','--format','{{.ServerVersion}}'],capture_output=True,text=True,timeout=8)
    if probe.returncode or not probe.stdout.strip():
        raise RuntimeError('Docker引擎不可用：未执行代码')
    with tempfile.TemporaryDirectory(prefix='pl5_v22_') as temp:
        folder = Path(temp)
        if language == 'python':
            inspect_python_source(source)
            (folder/'algorithm.py').write_text(source,encoding='utf8')
            (folder/'runner.py').write_text(PY_RUNNER,encoding='utf8')
            image, command = IMAGE_PY, ['python','-I','-B','/work/runner.py']
        else:
            # JS is emitted ONLY from the five compiler-owned templates.
            if source not in (_source_pair(f)[2] for f in FAMILIES):
                raise ValueError('拒绝执行非模板Node算法源码')
            (folder/'algorithm.cjs').write_text(source+'\nmodule.exports={scoreBatch};\n',encoding='utf8')
            (folder/'runner.cjs').write_text(JS_RUNNER,encoding='utf8')
            image, command = IMAGE_JS, ['node','/work/runner.cjs']
        folder.chmod(0o755)
        for file in folder.iterdir():file.chmod(0o644)
        args=[exe,'run','--rm','-i','--network','none','--read-only','--cap-drop','ALL',
              '--security-opt','no-new-privileges=true','--pids-limit','32',
              '--memory','512m','--cpus','1.0','--user','65534:65534',
              '--tmpfs','/tmp:rw,nosuid,nodev,size=16m',
              '--mount',f'type=bind,source={folder},target=/work,readonly',
              '--workdir','/tmp',image,*command]
        p=subprocess.run(args,input=_canon({'cases':cases}),text=True,capture_output=True,
                         timeout=timeout,check=False)
        if p.returncode:
            raise RuntimeError(f'{language}容器运行失败(code={p.returncode}): '+p.stderr[-450:])
        if len(p.stdout.encode()) > MAX_STDOUT:
            raise RuntimeError('容器输出超过限制')
        try: res=json.loads(p.stdout)
        except json.JSONDecodeError as exc: raise RuntimeError('沙箱输出无法解析') from exc
        if not isinstance(res,dict) or not isinstance(res.get('scores'),list) or len(res['scores'])!=len(cases):
            raise ValueError('沙箱输出缺少分数')
        return res['scores']


def counterexample_cases(*, complete_domain=False) -> tuple[list[dict], dict]:
    """Pinned exploratory red-team fixtures; no draw from a future data source."""
    numbers = [f'{n:05d}' for n in range(0,450)]
    reverse = list(reversed(numbers))
    cases=[
        {'history':[], 'candidates':numbers},
        {'history':['00000','99999','00001'], 'candidates':numbers},
        {'history':['12345']*60, 'candidates':numbers},
        {'history':['54321','01234','99999','00000'], 'candidates':numbers},
        {'history':['00000','99999','00001'], 'candidates':reverse},
        {'history':['00000','99999','00001'], 'candidates':['00000','00001','99999','09876','12345','98765']},
    ]
    if complete_domain:
        cases.append({'history':['01234','98765','00000'], 'candidates':[f'{n:05d}' for n in range(CAPACITY)]})
    return cases, {'permutation': [1,4], 'full_domain':bool(complete_domain),
                   'future_leakage_guard':'all cases contain history prefix only; no hidden targets passed to scorer'}


def _compare(a: list, b: list, cases: list[dict], *, atol: float=1e-9) -> dict:
    if not isinstance(a,list) or len(a)!=len(cases) or not isinstance(b,list) or len(b)!=len(cases):
        raise ValueError('异构输出组数不一致')
    maximum=0.0; errors=0
    for k,c in enumerate(cases):
        if (not isinstance(a[k],list) or not isinstance(b[k],list) or len(a[k])!=len(c['candidates']) or len(b[k])!=len(c['candidates'])):
            raise ValueError('异构输出长度不一致')
        for x,y in zip(a[k],b[k]):
            if type(x) not in (int,float) or type(y) not in (int,float) or not math.isfinite(x) or not math.isfinite(y):
                raise ValueError('异构分数必须为有限数值')
            diff=abs(x-y);maximum=max(maximum,diff)
            if diff>atol:errors+=1
    return {'equal':errors==0, 'mismatches':errors, 'max_abs_error':maximum}



def _mathematical_reference(family: str, history: list[str], candidates: list[str]) -> list[int]:
    """Trusted specification oracle; never evaluates submitted Python/JS."""
    if family == 'digit_sum':
        return [sum(map(int, n)) for n in candidates]
    if family == 'span':
        return [max(map(int, n)) - min(map(int, n)) for n in candidates]
    if family == 'adjacent_energy':
        return [sum(abs(int(n[i]) - int(n[i-1])) for i in range(1, 5)) for n in candidates]
    if family == 'lag_overlap':
        return [sum(a == b for a,b in zip(n, history[-1])) if history else 0 for n in candidates]
    if family == 'digit_frequency':
        table = [[1] * 10 for _ in range(5)]
        for n in history[-120:]:
            for p, digit in enumerate(n):table[p][int(digit)] += 1
        return [sum(table[p][int(d)] for p,d in enumerate(n)) for n in candidates]
    raise ValueError('算法类型不正确')


def _permutation_stable(values: list[list[float]], cases: list[dict]) -> bool:
    normal={n:s for n,s in zip(cases[1]['candidates'],values[1])}
    return all(normal[n]==s for n,s in zip(cases[4]['candidates'],values[4]))


class V22ResearchLab:
    def __init__(self, db: sqlite3.Connection):
        self.db=db
        self.db.row_factory=sqlite3.Row
        self.council=ResearchCouncil(db)
        db.executescript('''
        CREATE TABLE IF NOT EXISTS v22_generated(
          project_id TEXT PRIMARY KEY, family TEXT NOT NULL, code_json TEXT NOT NULL,
          sha256 TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS v22_evaluations(
          project_id TEXT PRIMARY KEY, input_sha TEXT NOT NULL, report_json TEXT NOT NULL,
          report_sha TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS v22_generated_no_update BEFORE UPDATE ON v22_generated
          BEGIN SELECT RAISE(ABORT,'immutable_generated'); END;
        CREATE TRIGGER IF NOT EXISTS v22_generated_no_delete BEFORE DELETE ON v22_generated
          BEGIN SELECT RAISE(ABORT,'immutable_generated'); END;
        CREATE TRIGGER IF NOT EXISTS v22_evaluations_no_update BEFORE UPDATE ON v22_evaluations
          BEGIN SELECT RAISE(ABORT,'immutable_evaluation'); END;
        CREATE TRIGGER IF NOT EXISTS v22_evaluations_no_delete BEFORE DELETE ON v22_evaluations
          BEGIN SELECT RAISE(ABORT,'immutable_evaluation'); END;
        ''')
        db.commit()

    def _generated(self,project_id: str) -> dict | None:
        row=self.db.execute('SELECT * FROM v22_generated WHERE project_id=?',(project_id,)).fetchone()
        if not row: return None
        item=dict(row)
        if sha256(item['code_json'].encode()).hexdigest()!=item['sha256']:
            raise ValueError('V2.2生成源码完整性验证失败')
        return {'project_id':item['project_id'], 'family':item['family'],
                **json.loads(item['code_json']), 'sha256':item['sha256']}

    def generate(self,project_id: str,*,family: str | None=None) -> dict:
        self.council.plan(project_id)
        old=self._generated(project_id)
        if old:
            if family and old['family']!=family:raise ValueError('已封存算法族不可变更，请新建项目')
            return {'created':False,**{k:v for k,v in old.items() if k not in ('primary','reference','node')}}
        bp=self.council.paper.get_blueprint(self.council._project(project_id)['blueprint_id'])
        # Only method title: broad evidence text must not smuggle an instruction.
        family=family or suggest_family(bp['blueprint']['method_name'])
        if not family:
            return {'created':False,'project_id':project_id,'status':'requires_explicit_method_review',
                    'reason':'文献没有可明确识别的受限数学方法，不能假装已经复现'}
        first,second,node=_source_pair(family)
        for role,src in (('primary',first),('reference',second)):
            self.council.submit_code(project_id,role=role,source=src,origin='compiler_v22')
        self.council.red_team(project_id)
        artifact={'family':family,'primary':first,'reference':second,'node':node,
                  'compiler':'pl5-checked-templates-v2.2',
                  'claim':'独立提出的通用研究特征；未复现论文原算法，未证实预测价值',
                  'runtime_executed':False,'requires_docker':True}
        raw=_canon(artifact); digest=sha256(raw.encode()).hexdigest()
        self.db.execute('INSERT INTO v22_generated VALUES(?,?,?,?,?)',
                        (project_id,family,raw,digest,datetime.now(timezone.utc).isoformat()))
        self.db.commit()
        return {'created':True,'project_id':project_id,'family':family,'sha256':digest,
                'python_sources':2,'node_sources':1,'containers_started':0,'automatic_approval':False}

    def status(self,project_id: str) -> dict:
        self.council.state(project_id)  # hash-chain check
        proposed=self._generated(project_id)
        row=self.db.execute('SELECT * FROM v22_evaluations WHERE project_id=?',(project_id,)).fetchone()
        result=None
        if row:
            if sha256(row['report_json'].encode()).hexdigest()!=row['report_sha']:
                raise ValueError('V2.2实验报告完整性验证失败')
            result=json.loads(row['report_json'])
        return {'project_id':project_id,'generated':bool(proposed),
                'family':proposed['family'] if proposed else None,
                'evaluated':bool(result), 'report':result,
                'uacp':({'capability':'pl5.research.'+proposed['family'],
                         'inputs':['draws_before_target','candidate_numbers'],
                         'outputs':['per_candidate_numeric_score'],
                         'implementation_runtimes':['python3.12','node24'],
                         'validation':'engineering_only' if result and result['engineering_pass'] else 'unverified',
                         'production_allowed':False} if proposed else None),
                'automatic_release':False,'prediction_advantage':'NOT_ESTABLISHED'}

    def evaluate(self,project_id: str,*,allow_docker=False,complete_domain=False,
                 executor: Callable | None=None) -> dict:
        if not allow_docker:
            raise PermissionError('必须显式选择--allow-docker才能运行隔离实验')
        proposed=self._generated(project_id)
        if not proposed:raise ValueError('请先生成受约束的算法源码')
        if self.db.execute('SELECT 1 FROM v22_evaluations WHERE project_id=?',(project_id,)).fetchone():
            raise ValueError('实验已封存，不能反复使用同一项目试验；请新建研究项目')
        cases,attack=counterexample_cases(complete_domain=complete_domain)
        _validate_cases(cases)
        run=executor or _run_container
        first=run(proposed['primary'],cases,'python')
        second=run(proposed['reference'],cases,'python')
        js=run(proposed['node'],cases,'node')
        again=run(proposed['primary'],cases,'python')
        independent_spec=[_mathematical_reference(proposed['family'], c['history'], c['candidates']) for c in cases]
        checks={'spec_conformance':_compare(first,independent_spec,cases),
                'python_pair':_compare(first,second,cases),
                'python_node':_compare(first,js,cases),
                'repeat_run':_compare(first,again,cases),
                'candidate_permutation':_permutation_stable(first,cases),
                'leading_zero_preserved':all(re.fullmatch('[0-9]{5}',n) for n in cases[5]['candidates']),
                'empty_history_handled':len(first[0])==len(cases[0]['candidates'])}
        passed=(all(ch['equal'] for ch in (checks['spec_conformance'],checks['python_pair'],checks['python_node'],checks['repeat_run']))
                and checks['candidate_permutation'] and checks['leading_zero_preserved'] and checks['empty_history_handled'])
        report={'version':'2.2.0','project_id':project_id,'family':proposed['family'],
                'generated_sha':proposed['sha256'],'cases':len(cases),
                'compared_score_values':sum(len(c['candidates']) for c in cases),
                'checks':checks,'attacks':attack,
                'engineering_pass':bool(passed),
                'predictive_advantage':'NOT_ESTABLISHED',
                'statistical_null':'independent_uniform_5_digit_draw',
                'fair_draw_top100_chance':0.001,
                'no_future_draws_used':True,
                'heterogeneous_runtime_certificate':'python_3_12_vs_node_24_experimental',
                'cross_language_not_independent_paper_replication':True,
                'executed_in_host_python':False,
                'research_only':True,'esse_auto_activate':False,
                'note':'比较分数而非仅Top-K；有限模板的工程交叉实现不能证明原论文算法或预测效果'}
        raw=_canon(report)
        self.db.execute('INSERT INTO v22_evaluations VALUES(?,?,?,?,?)',
                        (project_id,_digest({'cases':cases,'engine':proposed['sha256']}),raw,
                         sha256(raw.encode()).hexdigest(),datetime.now(timezone.utc).isoformat()))
        self.db.commit()
        return report

    def auto_generate(self,maximum=3) -> dict:
        if type(maximum) is not int or not 1<=maximum<=12:
            raise ValueError('数量限制为1—12')
        rows=self.db.execute('SELECT id FROM v21_projects ORDER BY created_at DESC,id DESC LIMIT 80').fetchall()
        new=[];skipped=[]
        for row in rows:
            pid=row['id']
            if self._generated(pid):continue
            r=self.generate(pid)
            if r['created']:new.append({'project_id':pid,'family':r['family']})
            else:skipped.append({'project_id':pid,'reason':r.get('status','unknown')})
            if len(new)>=maximum:break
        return {'new':new,'created':len(new),'unmatched':skipped[:20],
                'paid_model_calls':0,'containers_started':0,
                'automatic_release':False}
