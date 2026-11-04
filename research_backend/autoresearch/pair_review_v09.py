"""V0.9 manual paired open-Python review: two different code artifacts in Docker.

Matching Top-K is a necessary consistency check, not faithful paper replication.
Code independence is asserted by a reviewer, not proved by differing SHA256.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
import json
import re
import sqlite3
from .python_lab_v08 import PythonResearchStore,build_walkforward_cases,run_in_docker
from .replication_v09 import hash_obj


def utc():return datetime.now(timezone.utc).isoformat(timespec='seconds')


class PairReview:
    def __init__(self,db:sqlite3.Connection):
        self.db=db
        self.db.row_factory=sqlite3.Row
        self.lab=PythonResearchStore(db)
        db.executescript('''
        CREATE TABLE IF NOT EXISTS v09_code_pairs (
          pair_id TEXT PRIMARY KEY,protocol_id TEXT NOT NULL,
          primary_sha256 TEXT NOT NULL,reference_sha256 TEXT NOT NULL,
          reviewer TEXT NOT NULL,independence_basis TEXT NOT NULL,
          created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS v09_pair_audits(
          id INTEGER PRIMARY KEY AUTOINCREMENT,pair_id TEXT NOT NULL,
          draws_sha256 TEXT NOT NULL,result_json TEXT NOT NULL,created_at TEXT NOT NULL,
          UNIQUE(pair_id,draws_sha256));
        CREATE TRIGGER IF NOT EXISTS v09_pairs_no_update BEFORE UPDATE ON v09_code_pairs
        BEGIN SELECT RAISE(ABORT,'immutable_code_pair');END;
        CREATE TRIGGER IF NOT EXISTS v09_pairs_no_delete BEFORE DELETE ON v09_code_pairs
        BEGIN SELECT RAISE(ABORT,'immutable_code_pair');END;
        CREATE TRIGGER IF NOT EXISTS v09_pair_audits_no_update BEFORE UPDATE ON v09_pair_audits
        BEGIN SELECT RAISE(ABORT,'immutable_pair_audit');END;
        CREATE TRIGGER IF NOT EXISTS v09_pair_audits_no_delete BEFORE DELETE ON v09_pair_audits
        BEGIN SELECT RAISE(ABORT,'immutable_pair_audit');END;
        ''')
        db.commit()

    def register(self,*,protocol_id:str,primary_sha256:str,reference_sha256:str,
                 reviewer:str,independence_basis:str):
        if primary_sha256==reference_sha256:raise ValueError('独立实现必须是不同的代码指纹')
        p=self.db.execute('SELECT code_id FROM v09_protocols WHERE protocol_id=?',(protocol_id,)).fetchone()
        if not p or p['code_id']!=primary_sha256:raise ValueError('协议必须绑定主实现代码')
        self.lab.get(primary_sha256);self.lab.get(reference_sha256)
        if not reviewer or not 20<=len(independence_basis)<=2000:
            raise ValueError('需要审查人和不少于20字的独立实现说明')
        details={'protocol_id':protocol_id,'primary_sha256':primary_sha256,
                 'reference_sha256':reference_sha256,'reviewer':reviewer,
                 'independence_basis':independence_basis}
        pair_id=hash_obj(details)
        self.db.execute('INSERT OR IGNORE INTO v09_code_pairs VALUES(?,?,?,?,?,?,?)',
            (pair_id,protocol_id,primary_sha256,reference_sha256,reviewer,independence_basis,utc()))
        self.db.commit()
        return {'pair_id':pair_id,'code_digests_differ':True,'independence_verified':False,
                'note':'仅登记人工说明，不能自动证明两份代码独立开发'}

    def list(self,limit=30):
        return [dict(row) for row in self.db.execute('SELECT * FROM v09_code_pairs ORDER BY created_at DESC LIMIT ?',
                 (max(1,min(100,limit)),))]

    def audit(self,pair_id:str,draws:list[str],*,k=100,eval_size=8,runner=run_in_docker):
        """4 Docker runs, side-by-side Top-K cross check; no host execution."""
        pair=self.db.execute('SELECT * FROM v09_code_pairs WHERE pair_id=?',(pair_id,)).fetchone()
        if not pair:raise ValueError('代码对不存在')
        data_sha256=hash_obj(draws)
        if self.db.execute('SELECT 1 FROM v09_pair_audits WHERE pair_id=? AND draws_sha256=?',(pair_id,data_sha256)).fetchone():
            raise ValueError('同一个数据范围已经进行过配对实验，禁止自动重复筛选')
        cases=build_walkforward_cases(draws,k=k,eval_size=eval_size)
        first=self.lab.get(pair['primary_sha256'])['source']
        second=self.lab.get(pair['reference_sha256'])['source']
        one=runner(first,cases)['ranked']
        one_again=runner(first,cases)['ranked']
        two=runner(second,cases)['ranked']
        two_again=runner(second,cases)['ranked']
        internally_stable=(one==one_again and two==two_again)
        disagreements=[i for i,(x,y) in enumerate(zip(one,two)) if x!=y]
        reproduced=bool(internally_stable and not disagreements)
        result={'pair_id':pair_id,'evaluated_draws':eval_size,'k':k,
                'same_top_k_all_cases':not disagreements,'different_cases':disagreements,
                'each_implementation_deterministic':internally_stable,
                'ranking_level_cross_reproduction':reproduced,
                'code_independence_verified':False,
                'faithful_paper_reproduction':False,
                'prediction_improvement_proven':False,
                'warning':'两份算法来源独立性需要人工验证；Top-K一致不代表底层分值/数学公式完全一致。'
            }
        self.db.execute('INSERT INTO v09_pair_audits(pair_id,draws_sha256,result_json,created_at) VALUES(?,?,?,?)',
                 (pair_id,data_sha256,json.dumps(result,ensure_ascii=False,sort_keys=True),utc()))
        self.db.commit()
        return result
