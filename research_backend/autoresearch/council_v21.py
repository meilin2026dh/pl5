"""V2.1 research council: bounded, append-only, cooperative research workflow.

Every role produces inspectable, immutable artifacts.  This is a workflow
coordinator, NOT a claim that independent LLMs, faithful paper reproduction,
or predictive advantage have been demonstrated. Untrusted code runs only via
V2.0's explicit Docker gate, never inside this orchestration process.
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
import sqlite3
from typing import Any

from .paper_factory_v20 import PaperFactory, _canon, _digest
from .python_lab_v08 import inspect_python_source

STAGES = ('literature', 'hypothesis', 'ability_gap', 'engineer_primary',
          'engineer_reference', 'adversarial_review', 'sandbox_audit', 'decision')
MAX_ARTIFACT_BYTES = 24_000


def _time() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _tree_signature(source: str) -> str:
    """Advisory structural copy check; never called proof of independence."""
    tree = ast.parse(source)
    norm = ast.dump(tree, annotate_fields=True, include_attributes=False)
    return sha256(norm.encode()).hexdigest()


class ResearchCouncil:
    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.db.row_factory = sqlite3.Row
        self.paper = PaperFactory(db)
        db.executescript('''
        CREATE TABLE IF NOT EXISTS v21_projects(
            id TEXT PRIMARY KEY, blueprint_id TEXT NOT NULL, goal TEXT NOT NULL,
            config_json TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS v21_events(
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL, stage TEXT NOT NULL, actor TEXT NOT NULL,
            payload_json TEXT NOT NULL, payload_sha TEXT NOT NULL,
            previous_sha TEXT NOT NULL, event_sha TEXT NOT NULL, created_at TEXT NOT NULL,
            UNIQUE(project_id,stage));
        CREATE INDEX IF NOT EXISTS idx_v21_events_project ON v21_events(project_id,event_id);
        CREATE TRIGGER IF NOT EXISTS v21_projects_no_update BEFORE UPDATE ON v21_projects
            BEGIN SELECT RAISE(ABORT,'immutable_project'); END;
        CREATE TRIGGER IF NOT EXISTS v21_projects_no_delete BEFORE DELETE ON v21_projects
            BEGIN SELECT RAISE(ABORT,'immutable_project'); END;
        CREATE TRIGGER IF NOT EXISTS v21_events_no_update BEFORE UPDATE ON v21_events
            BEGIN SELECT RAISE(ABORT,'immutable_event'); END;
        CREATE TRIGGER IF NOT EXISTS v21_events_no_delete BEFORE DELETE ON v21_events
            BEGIN SELECT RAISE(ABORT,'immutable_event'); END;
        ''')
        db.commit()

    def create(self, blueprint_id: str, *, goal: str, budget: int = 100,
               periods: int = 8) -> dict:
        b = self.paper.get_blueprint(blueprint_id)
        if not isinstance(goal, str) or not 10 <= len(goal.strip()) <= 500:
            raise ValueError('研究目标必须明确（10—500字符）')
        if type(budget) is not int or not 1 <= budget <= 100 or type(periods) is not int or not 2 <= periods <= 24:
            raise ValueError('科研预算或回测期数无效')
        config = {'budget': budget, 'periods': periods, 'protocol': 'uacp-research-v2.1',
                  'automatic_release': False, 'paid_llm': False}
        pid = _digest({'blueprint_id': blueprint_id, 'goal': goal.strip(), 'config': config})
        existed = bool(self.db.execute('SELECT 1 FROM v21_projects WHERE id=?',(pid,)).fetchone())
        self.db.execute('INSERT OR IGNORE INTO v21_projects VALUES(?,?,?,?,?)',
                        (pid, blueprint_id, goal.strip(), _canon(config), _time()))
        self.db.commit()
        return {'project_id': pid, 'created': not existed,
                'blueprint_source_verified': bool(b['document_sha']), 'state': self.state(pid)['state']}

    def _project(self, project_id: str) -> dict:
        row = self.db.execute('SELECT * FROM v21_projects WHERE id=?',(project_id,)).fetchone()
        if not row: raise KeyError('科研项目不存在')
        out = dict(row)
        out['config'] = json.loads(out.pop('config_json'))
        self.paper.get_blueprint(out['blueprint_id'])  # verify pinned source is unchanged
        return out

    def _events(self, project_id: str) -> list[dict]:
        return [dict(r) for r in self.db.execute('SELECT * FROM v21_events WHERE project_id=? ORDER BY event_id', (project_id,))]

    def _append(self, project_id: str, stage: str, payload: dict,
                actor: str, *, prerequisite: str | None = None) -> dict:
        self._project(project_id)
        if stage not in STAGES or not isinstance(payload, dict) or not isinstance(actor, str) or not 2 <= len(actor) <= 80:
            raise ValueError('研究阶段或角色不正确')
        raw = _canon(payload)
        if len(raw.encode()) > MAX_ARTIFACT_BYTES:
            raise ValueError('单份科研产物超过24KB')
        events = self._events(project_id)
        existing = next((e for e in events if e['stage'] == stage), None)
        payload_sha = sha256(raw.encode()).hexdigest()
        if existing:
            if existing['payload_sha'] == payload_sha: return {'created': False, 'stage': stage, 'sha256': existing['event_sha']}
            raise ValueError('阶段研究产物已经封存；不得事后覆盖。新假设需创建新项目')
        if prerequisite and prerequisite not in {e['stage'] for e in events}:
            raise ValueError('研究流程缺少必要前置阶段：'+prerequisite)
        previous = events[-1]['event_sha'] if events else '0'*64
        event_sha = sha256(_canon({'project':project_id,'stage':stage,'actor':actor,
                                   'payload_sha':payload_sha,'previous':previous}).encode()).hexdigest()
        self.db.execute('INSERT INTO v21_events(project_id,stage,actor,payload_json,payload_sha,previous_sha,event_sha,created_at) VALUES(?,?,?,?,?,?,?,?)',
                        (project_id,stage,actor,raw,payload_sha,previous,event_sha,_time()))
        self.db.commit()
        return {'created': True, 'stage':stage,'sha256':event_sha}

    def _artifact(self, project_id: str, stage: str) -> dict | None:
        row = self.db.execute('SELECT payload_json FROM v21_events WHERE project_id=? AND stage=?',
                              (project_id,stage)).fetchone()
        return json.loads(row['payload_json']) if row else None

    def plan(self, project_id: str) -> dict:
        project = self._project(project_id)
        b = self.paper.get_blueprint(project['blueprint_id'])
        p = b['blueprint']
        paper = {'document_key': b['document_key'], 'document_sha': b['document_sha'],
                 'quote': p['excerpt'], 'locator': p['locator'],
                 'method_name': p['method_name'], 'method_type':p['method_type'],
                 'source_untrusted': True, 'paper_reproduced':False}
        a = self._append(project_id,'literature',paper,'literature_reader')
        h = {'goal':project['goal'], 'hypothesis':p['transfer_hypothesis'],
             'assumptions':p['assumptions'], 'mechanism':p['mechanism'],
             'falsification_plan':p['falsification_plan'],
             'null_model':'five independent uniform digits', 'forecast_advantage':'not_established'}
        b1 = self._append(project_id,'hypothesis',h,'hypothesis_designer',prerequisite='literature')
        gap = {'required_inputs':['historic_draws_cutoff','five_digit_candidate_domain'],
               'expected_output':'ranked_candidates',
               'existing_interface':'score_batch(history,candidates)',
               'missing_capabilities':['independent_reference_implementation',
                                       'sandbox_cross_check', 'prespecified_null_controls'],
               'can_run_untrusted_code_in_host':False,
               'requires_manual_approval_for_release':True}
        c = self._append(project_id,'ability_gap',gap,'ability_network_planner',prerequisite='hypothesis')
        return {'project_id':project_id,'literature':a,'hypothesis':b1,'gap':c,
                'state':self.state(project_id)['state']}

    def submit_code(self, project_id: str, *, role: str, source: str,
                    origin='human') -> dict:
        if role not in ('primary','reference'):
            raise ValueError('算法工程角色不合法')
        self.plan(project_id)
        inspect_python_source(source) # explicitly NOT execution
        bid = self._project(project_id)['blueprint_id']
        stage = 'engineer_'+role
        other_role = 'reference' if role=='primary' else 'primary'
        other = self._artifact(project_id, 'engineer_'+other_role)
        signature = _tree_signature(source)
        if other and other['structural_signature'] == signature:
            raise ValueError('两路实现AST结构完全相同，无法视为独立工程方案')
        result = self.paper.link_code(bid,source,role=role,origin=origin)
        payload = {'role':role,'source_sha256':result['code_id'],
                   'structural_signature':signature,'origin':origin,
                   'static_checked':True,'runtime_executed':False,
                   'independence_verified':False}
        a = self._append(project_id,stage,payload,'engineer_'+role,prerequisite='ability_gap')
        return {'event':a,'code_id':result['code_id'],'status':self.state(project_id)['state']}

    def red_team(self, project_id: str) -> dict:
        self.plan(project_id)
        p = self._project(project_id)
        primary = self._artifact(project_id,'engineer_primary')
        reference = self._artifact(project_id,'engineer_reference')
        if not primary or not reference:
            raise ValueError('红队审查前必须提交两套代码')
        issues = [
            {'name':'lookahead_leakage', 'test':'每个目标只读取开奖前历史；改变目标及未来记录不得改变前缀输出'},
            {'name':'random_null', 'test':'公平随机模拟与随机种子对照，不把压缩数量当预测能力'},
            {'name':'multitest', 'test':'记录所有模型、规则、窗口、种子试验，冻结最后测试集'},
            {'name':'representation_attack', 'test':'不同历史前缀、前导零、重复号码及边界输入'},
            {'name':'provenance', 'test':'方法原文锚点存在；代码不等于原论文的忠实复现'},
        ]
        report={'issues':issues,'checks_implemented_as_tests':False,
                'potential_copy':primary['structural_signature']==reference['structural_signature'],
                'source_sha_different':primary['source_sha256']!=reference['source_sha256'],
                'zero_predictive_claim':True,'requires_docker':True,
                'requires_future_validation':True,'prespecified_null':p['config']}
        event=self._append(project_id,'adversarial_review',report,'skeptical_reviewer',
                           prerequisite='engineer_reference')
        return {'event':event,'review':report}

    def audit(self, project_id: str, draws: list[str], *, allow_docker=False, runner=None) -> dict:
        if not allow_docker: raise PermissionError('真实Docker隔离测试必须显式授权')
        self.red_team(project_id)
        p=self._project(project_id)
        k=p['config']['budget']; periods=p['config']['periods']
        if not isinstance(draws,list) or len(draws)<periods+2 or len(draws)>1200 or any(not isinstance(n,str) or not re.fullmatch('[0-9]{5}',n) for n in draws):
            raise ValueError('历史记录必须是保留前导零的有序五位开奖数据')
        if self._artifact(project_id,'sandbox_audit'):
            raise ValueError('本项目已使用测试数据，不能重复开封')
        kwargs={'budget':k,'periods':periods,'allow_docker':True}
        if runner is not None:kwargs['runner']=runner # test dependency injection only
        report=self.paper.study(p['blueprint_id'],draws,**kwargs)
        artifact={'engineering_cross_check':report['engineering_cross_check'],
                  'same_top_k_all_periods':report['same_top_k_all_periods'],
                  'repeat_execution_stable':report['repeat_execution_stable'],
                  'paper_reproduction_proven':False,
                  'sample_use':'REUSED_EXPLORATORY_HISTORY',
                  'data_sha256':_digest(draws),
                  'tests':{'periods':periods,'budget':k,'actual_hits':report['actual_historical_hits'],
                           'uniform_expected_hits':report['uniform_expected_historical_hits']},
                  'prediction_advantage_proven':False}
        a=self._append(project_id,'sandbox_audit',artifact,'sandbox_verifier',
                       prerequisite='adversarial_review')
        return {'event':a,'report':artifact,'status':self.state(project_id)['state']}

    def decision(self, project_id: str) -> dict:
        self._project(project_id)
        if not self._artifact(project_id,'sandbox_audit'):
            raise ValueError('未通过沙箱验证，不允许提交决策')
        report=self._artifact(project_id,'sandbox_audit')
        accepted=report['engineering_cross_check'] and report['same_top_k_all_periods']
        d={'research_engineering_status':'manual_review_candidate' if accepted else 'needs_new_experiment',
           'prediction_advantage':'NOT_ESTABLISHED', 'official_approval':False,
           'automatic_esse_activation':False,'release_requires_new_project':not accepted,
           'reason':'工程一致性仅代表重复执行和排名一致，不能证明源论文或预测优势'}
        a=self._append(project_id,'decision',d,'scientific_gatekeeper',prerequisite='sandbox_audit')
        return {'event':a,'decision':d,'status':self.state(project_id)['state']}

    def state(self, project_id: str) -> dict:
        p=self._project(project_id)
        rows=self._events(project_id)
        prev='0'*64
        for e in rows:
            if (e['previous_sha']!=prev or
                e['payload_sha']!=sha256(e['payload_json'].encode()).hexdigest() or
                e['event_sha']!=sha256(_canon({'project':project_id,'stage':e['stage'],
                    'actor':e['actor'],'payload_sha':e['payload_sha'],
                    'previous':e['previous_sha']}).encode()).hexdigest()):
                raise ValueError('科研审计链校验失败')
            prev=e['event_sha']
        stages=[e['stage'] for e in rows]
        next_stage=next((s for s in STAGES if s not in stages),None)
        return {'project_id':project_id, 'goal':p['goal'], 'completed':stages,
                'next_stage':next_stage, 'state':'research_review_pending' if next_stage is None else 'in_progress',
                'event_count':len(rows), 'last_event_sha':prev,
                'experimental_only':True,'algorithm_auto_promotion':False,
                'prediction_advantage':'NOT_ESTABLISHED'}

    def auto_plan(self, maximum=3) -> dict:
        """Create *research-only* role plans from pinned V2.0 paper cards.

        Does not generate, download, import, execute, or approve Python code.
        Designed for bounded unattended scheduling after V2.0 auto-extract.
        """
        if type(maximum) is not int or not 1 <= maximum <= 12:
            raise ValueError('单轮新协同科研计划数量应为1—12')
        created=[]
        rows=self.db.execute('SELECT id FROM v20_blueprints ORDER BY created_at DESC,id DESC LIMIT 150').fetchall()
        for row in rows:
            bid=row['id']
            bp=self.paper.get_blueprint(bid)['blueprint']
            goal='独立评估研究方法并明确可复现能力缺口：'+bp['method_name'][:150]
            result=self.create(bid,goal=goal)
            if not result['created']:continue
            plan=self.plan(result['project_id'])
            created.append({'project_id':result['project_id'],'source_blueprint':bid,
                            'next_stage':self.state(result['project_id'])['next_stage']})
            if len(created)>=maximum:break
        return {'created':created,'count':len(created),'paid_model_calls':0,
                'untrusted_code_executed':False,'automatic_approval':False}

    def status(self, limit=20) -> dict:
        if type(limit) is not int or not 1<=limit<=100:raise ValueError('limit无效')
        rows=self.db.execute('SELECT id FROM v21_projects ORDER BY created_at DESC,id DESC LIMIT ?',(limit,)).fetchall()
        return {'version':'2.1.0', 'projects':[self.state(r['id']) for r in rows],
                'total':self.db.execute('SELECT COUNT(*) FROM v21_projects').fetchone()[0],
                'automatic_execution':False,'auto_publish':False,
                'research_only':True}
