"""PL5 V1.0 durable, conservative research coordinator.

Bounded research workflow from source metadata -> hypothesis -> safe algorithm
proposals -> developmental falsification -> evidence overview. At-least-once
execution with idempotent subordinate stores. No LLM, betting or untrusted
code execution; no approval/promotion. A local SQLite file is not a trusted
remote clock or tamper-proof audit record.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Callable

from .collectors import Paper, collect_all, DEFAULT_TOPICS
from .lab import propose, relevance_score
from .registry_v06 import ResearchRegistry
from .formulas import invent_from_text
from .proposals_v08 import offline_proposals
from .python_lab_v08 import PythonResearchStore
from .evidence_v09 import EvidenceLedger
from .verification import full_audit

STAGES = ('discover', 'hypothesize', 'ingest', 'invent', 'propose_python', 'audit', 'review')
CODE_FILES=('integrated_v10.py','lab.py','formulas.py','registry_v06.py','proposals_v08.py','python_lab_v08.py')


def pipeline_code_hash():
    folder=Path(__file__).resolve().parent
    return sha256(''.join(sha256((folder/x).read_bytes()).hexdigest() for x in CODE_FILES).encode()).hexdigest()


def canon(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def sha(v):
    return sha256(canon(v).encode('utf-8')).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


class ResearchCoordinator:
    """Connection supplied by LabStore, one SQLite DB for all metadata and state."""
    def __init__(self, store):
        self.store = store
        self.db = store.db
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS v10_runs (
           run_id TEXT PRIMARY KEY, config_json TEXT NOT NULL, config_sha256 TEXT NOT NULL,
           status TEXT NOT NULL, started_at TEXT NOT NULL, updated_at TEXT NOT NULL,
           last_error TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS v10_steps (
           run_id TEXT NOT NULL, step TEXT NOT NULL, state TEXT NOT NULL,
           started_at TEXT NOT NULL, finished_at TEXT, result_json TEXT,
           result_sha256 TEXT, error TEXT NOT NULL DEFAULT '', attempts INTEGER NOT NULL DEFAULT 0,
           PRIMARY KEY(run_id, step));
        CREATE TABLE IF NOT EXISTS v10_budgets (
           run_id TEXT NOT NULL, resource TEXT NOT NULL, quantity REAL NOT NULL,
           recorded_at TEXT NOT NULL, PRIMARY KEY(run_id, resource));
        ''')
        self.db.commit()

    @staticmethod
    def normalize_config(config):
        cfg = dict(config)
        if cfg.get('mode') not in ('offline', 'live'):
            raise ValueError('必须明确选择 offline 或 live')
        cfg.setdefault('topics', DEFAULT_TOPICS[:2])
        cfg.setdefault('providers', ['openalex', 'arxiv'])
        cfg.setdefault('days', 21)
        cfg.setdefault('per_query', 3)
        cfg.setdefault('max_requests', 12)
        cfg.setdefault('max_documents', 3)
        cfg.setdefault('max_formulas', 2)
        cfg.setdefault('max_code_proposals', 2)
        cfg.setdefault('enable_development_audit', False)
        cfg.setdefault('eval_size', 12)
        cfg.setdefault('null_sequences', 2)
        cfg.setdefault('k', 100)
        cfg.setdefault('pipeline_code_sha256', pipeline_code_hash())
        cfg.setdefault('dataset_sha256', None)
        cfg.setdefault('official_source', None)
        if not isinstance(cfg['topics'], list) or not 1 <= len(cfg['topics']) <= 6 or any(not isinstance(t,str) or not 2 <= len(t) <= 100 for t in cfg['topics']):
            raise ValueError('主题必须是1-6个合法字符串')
        if not isinstance(cfg['providers'], list) or not 1 <= len(cfg['providers']) <= 3 or any(p not in ('openalex', 'arxiv', 'github') for p in cfg['providers']):
            raise ValueError('未知数据源')
        for key,lo,hi in [('days',1,365),('per_query',1,10),('max_requests',1,30),('max_documents',1,10),('max_formulas',1,6),('max_code_proposals',1,5),('eval_size',5,100),('null_sequences',1,10),('k',1,100)]:
            if type(cfg[key]) is not int or not lo <= cfg[key] <= hi:
                raise ValueError(f'{key}超出范围')
        if cfg['mode']=='offline' and 'fixture' not in cfg:
            raise ValueError('离线模式必须提供fixture来源')
        if cfg['mode']=='live' and 'fixture' in cfg:
            raise ValueError('在线模式不得混入fixture')
        if cfg['enable_development_audit'] and (not cfg.get('dataset_sha256') or not cfg.get('official_source')):
            raise ValueError('开发回测必须声明已核对的数据摘要及来源')
        if cfg['enable_development_audit'] and not str(cfg['official_source']).startswith(('official:', 'https://')):
            raise ValueError('历史来源必须有核对说明')
        # No paid LLM or external generated Python in this orchestrator.
        if cfg.get('paid_llm') or cfg.get('auto_execute_generated_code') or cfg.get('auto_approve'):
            raise PermissionError('V1.0无人值守任务禁止付费模型、外部Python运行与算法自动批准')
        return cfg

    def create(self, config, *, run_id=None):
        cfg=self.normalize_config(config)
        run_id=run_id or 'run_'+uuid.uuid4().hex[:20]
        if not isinstance(run_id,str) or not run_id.startswith('run_') or len(run_id)>100:
            raise ValueError('不合法的run_id')
        signature=sha(cfg)
        row=self.db.execute('SELECT config_sha256 FROM v10_runs WHERE run_id=?',(run_id,)).fetchone()
        if row:
            if row['config_sha256']!=signature:raise ValueError('同一run_id的参数不可变更')
            return run_id
        self.db.execute('INSERT INTO v10_runs(run_id,config_json,config_sha256,status,started_at,updated_at) VALUES(?,?,?,?,?,?)',
                        (run_id, canon(cfg), signature,'pending',utc(),utc()))
        self.db.commit()
        return run_id

    def _record_budget(self,run_id,resource,quantity,limit):
        if quantity>limit:
            raise PermissionError(f'{resource}预算超限：{quantity}>{limit}')
        self.db.execute('INSERT OR IGNORE INTO v10_budgets VALUES(?,?,?,?)',(run_id,resource,quantity,utc()))
        self.db.commit()

    def _step(self,run_id,stage,fn:Callable):
        row=self.db.execute('SELECT * FROM v10_steps WHERE run_id=? AND step=?',(run_id,stage)).fetchone()
        if row and row['state']=='done':
            result=json.loads(row['result_json'])
            if sha(result)!=row['result_sha256']:
                raise RuntimeError('步骤存档摘要校验失败')
            return result
        attempts=(int(row['attempts']) if row else 0)+1
        self.db.execute('''INSERT INTO v10_steps(run_id,step,state,started_at,attempts) VALUES(?,?,?,?,?)
          ON CONFLICT(run_id,step) DO UPDATE SET state='running',started_at=excluded.started_at,
          finished_at=NULL,error='',attempts=excluded.attempts''',
          (run_id,stage,'running',utc(),attempts))
        self.db.execute("UPDATE v10_runs SET status='running',updated_at=?,last_error='' WHERE run_id=?",(utc(),run_id))
        self.db.commit()
        try:
            result=fn()
            result_json=canon(result)
            self.db.execute('''UPDATE v10_steps SET state='done',finished_at=?,result_json=?,result_sha256=?,error=''
                WHERE run_id=? AND step=?''',(utc(),result_json,sha(result),run_id,stage))
            self.db.commit()
            return result
        except Exception as exc:
            err=(type(exc).__name__+': '+str(exc))[:600]
            self.db.execute('UPDATE v10_steps SET state=?,finished_at=?,error=? WHERE run_id=? AND step=?',
                            ('failed',utc(),err,run_id,stage))
            self.db.execute('UPDATE v10_runs SET status=?,updated_at=?,last_error=? WHERE run_id=?',
                            ('failed',utc(),err,run_id))
            self.db.commit()
            raise

    def run(self,run_id,*,fixture_papers=None,history_numbers=None):
        row=self.db.execute('SELECT * FROM v10_runs WHERE run_id=?',(run_id,)).fetchone()
        if not row:raise KeyError('任务不存在')
        cfg=json.loads(row['config_json'])
        if cfg.get('pipeline_code_sha256')!=pipeline_code_hash():
            raise RuntimeError('当前研究引擎源码与任务创建时不一致；禁止跨版本静默续跑')
        if sha(cfg)!=row['config_sha256']:
            raise RuntimeError('任务参数遭到篡改')
        if cfg['mode']=='offline':
            if fixture_papers is None:raise ValueError('离线执行必须提供实际fixture对象')
            digest=sha([p.to_dict() for p in fixture_papers])
            if digest != cfg['fixture']:
                raise ValueError('离线研究资料摘要与创建任务时不同')
        if cfg['enable_development_audit']:
            if not history_numbers or sha(history_numbers)!=cfg['dataset_sha256']:
                raise ValueError('历史序列和任务冻结的数据摘要不匹配')
        queries=len(cfg['topics'])*len(cfg['providers'])
        self._record_budget(run_id,'metadata_requests_max',queries,cfg['max_requests'])
        self._record_budget(run_id,'paid_model_calls',0,0)
        results={}
        def discovery():
            if cfg['mode']=='offline':
                papers=list(fixture_papers);errors=[]
            else:
                papers,errors=collect_all(cfg['topics'],days=cfg['days'],limit=cfg['per_query'],providers=tuple(cfg['providers']))
            if len(papers)>cfg['max_requests']*cfg['per_query']:
                papers=papers[:cfg['max_requests']*cfg['per_query']]
            if cfg['mode']=='live' and not papers and errors:
                raise RuntimeError('所有外部信息源失败；保留失败状态供下次重试')
            added=self.store.upsert_papers(papers,relevance_score)
            ordered=sorted(papers,key=lambda p:(-relevance_score(p),p.key))
            keys=list(dict.fromkeys(x.key for x in ordered))[:cfg['max_documents']]
            return {'fetched':len(papers),'new_papers':added,'paper_keys':keys,'provider_failures':errors,
                    'live_network':cfg['mode']=='live','untrusted_metadata_only':True}
        results['discover']=self._step(run_id,'discover',discovery)

        def hypotheses():
            n=0
            for key in results['discover']['paper_keys']:
                row=self.db.execute('SELECT * FROM papers WHERE key=?',(key,)).fetchone()
                if row is None or row['score']<2:continue
                p=Paper(row['key'],row['source'],row['title'],row['abstract'],row['url'],row['published'],row['topic'],row['authors'])
                for spec in propose(p):
                    n+=int(self.store.add_hypothesis(spec,p.key))
            return {'new_hypotheses':n,'independent_predictive_evidence':False}
        results['hypothesize']=self._step(run_id,'hypothesize',hypotheses)

        def ingest():
            registry=ResearchRegistry(self.db)
            seen=[]
            for key in results['discover']['paper_keys']:
                p=self.db.execute('SELECT * FROM papers WHERE key=?',(key,)).fetchone()
                if p is None or p['score']<2 or len(p['abstract'].strip())<30:continue
                k='lead:'+p['key']
                registry.add_document(k,p['title'] or p['key'],p['abstract'],url=p['url'],kind='abstract')
                seen.append(k)
            return {'document_keys':seen,'full_papers_reproduced':0}
        results['ingest']=self._step(run_id,'ingest',ingest)

        def invent():
            registry=ResearchRegistry(self.db)
            outcome=[]
            for key in results['ingest']['document_keys']:
                doc=registry.get_document(key)
                for algo in invent_from_text(doc['text_excerpt'],key,limit=cfg['max_formulas']):
                    rec=registry.add_algorithm(algo,key)
                    outcome.append({'fingerprint':rec['fingerprint'],'new':rec['new'],'doc_key':key})
            return {'formulas':outcome,'auto_approved':False}
        results['invent']=self._step(run_id,'invent',invent)

        def propose_python():
            registry=ResearchRegistry(self.db)
            lab=PythonResearchStore(self.db)
            outcome=[]
            for key in results['ingest']['document_keys']:
                doc=registry.get_document(key)
                # Offline templates only, untrusted literature never becomes executable instructions.
                for p in offline_proposals(doc)[:cfg['max_code_proposals']]:
                    rec=lab.add(document_key=key,**p)
                    outcome.append({'code_sha256':rec['code_id'],'new':rec.get('new'), 'origin':'offline_template'})
            return {'python_candidates':outcome,'code_executed':False,'auto_approved':False}
        results['propose_python']=self._step(run_id,'propose_python',propose_python)

        def audit():
            if not cfg['enable_development_audit']:
                return {'status':'skipped_no_official_data','reason':'不使用演示数据验证真实预测优势'}
            registry=ResearchRegistry(self.db)
            outcome=[]
            for item in results['invent']['formulas'][:cfg['max_documents']*cfg['max_formulas']]:
                f=item['fingerprint']
                old=registry.has_audit(f,cfg['dataset_sha256'])
                if old:
                    outcome.append({'fingerprint':f,'audit_id':old,'already_audited':True})
                    continue
                report=full_audit(registry.get_algorithm(f),history_numbers,k=cfg['k'],
                                  eval_size=cfg['eval_size'],null_sequences=cfg['null_sequences'],
                                  attempts=registry.audit_attempts())
                record=registry.add_audit(f,cfg['dataset_sha256'],report)
                outcome.append({'fingerprint':f,'audit_id':record['audit_id'],'engineering_ok':report['engineering_reproduced'],
                                'exploratory_only':True,'predictive_edge_proven':False})
            return {'status':'development_only','audits':outcome,'official_source_declaration':cfg['official_source']}
        results['audit']=self._step(run_id,'audit',audit)

        def review():
            ledger=EvidenceLedger(self.db)
            return {'registered_model_count':ledger.family_report()['models_registered'],
                    'new_formulas':len(results['invent']['formulas']),
                    'new_python_candidates':len(results['propose_python']['python_candidates']),
                    'automatic_formal_admission':False,'auto_predictive_claim':False,
                    'note':'文献和代码只入研究候选库；未注册的模型不得进入正式前向验证'}
        results['review']=self._step(run_id,'review',review)
        self.db.execute("UPDATE v10_runs SET status='completed',updated_at=?,last_error='' WHERE run_id=?",(utc(),run_id))
        self.db.commit()
        return {'run_id':run_id,'status':'completed','steps':results,'test_data_claim':False}

    def status(self,run_id=None,limit=20):
        if run_id:
            row=self.db.execute('SELECT * FROM v10_runs WHERE run_id=?',(run_id,)).fetchone()
            if not row:raise KeyError('任务不存在')
            runs=[dict(row)]
        else:
            runs=[dict(x) for x in self.db.execute('SELECT * FROM v10_runs ORDER BY started_at DESC LIMIT ?', (limit,))]
        for r in runs:
            r['config']=json.loads(r.pop('config_json'))
            r['steps']=[dict(x) for x in self.db.execute('''SELECT step,state,attempts,started_at,finished_at,error,result_sha256
                       FROM v10_steps WHERE run_id=? ORDER BY rowid''',(r['run_id'],))]
            r['budget']={x['resource']:x['quantity'] for x in self.db.execute('SELECT resource,quantity FROM v10_budgets WHERE run_id=?',(r['run_id'],))}
        return runs if not run_id else runs[0]
