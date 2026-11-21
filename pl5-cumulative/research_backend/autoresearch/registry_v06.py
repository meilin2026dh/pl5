"""Research provenance and separate admission states. Never automatically activates PL5 ranking."""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
import json
import sqlite3
from .formulas import InventedAlgorithm


def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))


class ResearchRegistry:
    def __init__(self,db:sqlite3.Connection):
        self.db=db
        self.db.row_factory=sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS v06_documents (
            doc_key TEXT PRIMARY KEY, title TEXT NOT NULL,source_url TEXT NOT NULL,
            sha256 TEXT NOT NULL, text_excerpt TEXT NOT NULL, text_length INTEGER NOT NULL,
            kind TEXT NOT NULL, imported_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS v06_algorithms (
            fingerprint TEXT PRIMARY KEY, specification TEXT NOT NULL,
            document_key TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'invented',
            created_at TEXT NOT NULL, FOREIGN KEY(document_key) REFERENCES v06_documents(doc_key));
        CREATE TABLE IF NOT EXISTS v06_audits (
            id INTEGER PRIMARY KEY AUTOINCREMENT, fingerprint TEXT NOT NULL,
            data_sha256 TEXT NOT NULL, created_at TEXT NOT NULL, report_json TEXT NOT NULL,
            report_sha256 TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS v06_approvals (
            fingerprint TEXT PRIMARY KEY, audit_id INTEGER NOT NULL, reviewer TEXT NOT NULL,
            agreed_at TEXT NOT NULL, statement TEXT NOT NULL);
        ''')
        self.db.commit()

    def add_document(self,key,title,text,*,url='',kind='local'):
        if not key or len(key)>200 or not title or len(title)>500:raise ValueError('文献标识或标题不合法')
        if kind not in ('local','arxiv_pdf','abstract'):raise ValueError('来源类型不支持')
        if len(text)<30 or len(text)>70000:raise ValueError('正文长度不合理')
        digest=sha256(text.encode()).hexdigest()
        row=self.db.execute('SELECT sha256 FROM v06_documents WHERE doc_key=?',(key,)).fetchone()
        if row and row['sha256']!=digest:raise ValueError('同一个文献ID与已有文本冲突；禁止无记录替换')
        self.db.execute('INSERT OR IGNORE INTO v06_documents VALUES(?,?,?,?,?,?,?,?)',
                        (key,title,url,digest,text[:70000],len(text),kind,now()))
        self.db.commit();return {'key':key,'sha256':digest,'new':not bool(row)}

    def documents(self,limit=30):
        return [dict(x) for x in self.db.execute(
            'SELECT doc_key,title,source_url,sha256,text_length,kind,imported_at FROM v06_documents ORDER BY imported_at DESC LIMIT ?',
            (max(1,min(int(limit),200)),)).fetchall()]

    def get_document(self,key):
        row=self.db.execute('SELECT * FROM v06_documents WHERE doc_key=?',(key,)).fetchone()
        if not row:raise KeyError('没有找到该文献')
        return dict(row)

    def add_algorithm(self,algo:InventedAlgorithm,key):
        algo.validate();self.get_document(key)
        f=algo.fingerprint()
        existed=self.db.execute('SELECT 1 FROM v06_algorithms WHERE fingerprint=?',(f,)).fetchone()
        self.db.execute('INSERT OR IGNORE INTO v06_algorithms(fingerprint,specification,document_key,created_at) VALUES(?,?,?,?)',
                        (f,canon(algo.to_dict()),key,now()))
        self.db.commit();return {'fingerprint':f,'new':not bool(existed)}

    def algorithms(self,limit=50):
        out=[]
        for row in self.db.execute('SELECT * FROM v06_algorithms ORDER BY created_at DESC LIMIT ?',
                                   (max(1,min(int(limit),300)),)):
            x=dict(row);x['specification']=json.loads(x['specification']);out.append(x)
        return out

    def get_algorithm(self,fingerprint):
        row=self.db.execute('SELECT * FROM v06_algorithms WHERE fingerprint=?',(fingerprint,)).fetchone()
        if not row:raise KeyError('算法不存在')
        return InventedAlgorithm(**json.loads(row['specification'])).validate()

    def add_audit(self,fingerprint,data_sha256,report):
        self.get_algorithm(fingerprint)
        if len(data_sha256)!=64 or not all(c in '0123456789abcdef' for c in data_sha256):
            raise ValueError('历史数据指纹不合法')
        payload=canon(report)
        digest=sha256(payload.encode()).hexdigest()
        self.db.execute('INSERT INTO v06_audits(fingerprint,data_sha256,created_at,report_json,report_sha256) VALUES(?,?,?,?,?)',
                        (fingerprint,data_sha256,now(),payload,digest))
        self.db.commit()
        return {'audit_id':self.db.execute('SELECT last_insert_rowid()').fetchone()[0], 'sha256':digest}

    def audits(self,limit=50):
        res=[]
        for row in self.db.execute('SELECT * FROM v06_audits ORDER BY id DESC LIMIT ?',
                                   (max(1,min(int(limit),100)),)):
            x=dict(row);x['report']=json.loads(x.pop('report_json'));res.append(x)
        return res

    def has_audit(self,fingerprint,data_sha256):
        row=self.db.execute('SELECT id FROM v06_audits WHERE fingerprint=? AND data_sha256=? LIMIT 1',
                            (fingerprint,data_sha256)).fetchone()
        return int(row['id']) if row else None

    def audit_attempts(self):
        # Count attempts globally, including repeated attempts. No evidence-gaming via selective deletion.
        return max(1,self.db.execute('SELECT count(*) FROM v06_audits').fetchone()[0]+1)

    def approve_research_only(self,fingerprint,audit_id,reviewer,consent):
        if consent!='I_APPROVE_RESEARCH_ONLY':raise PermissionError('必须进行明确的人工审批')
        if not reviewer.strip() or len(reviewer)>100:raise ValueError('审批人不能为空')
        algo=self.get_algorithm(fingerprint)
        row=self.db.execute('SELECT * FROM v06_audits WHERE id=? AND fingerprint=?',(audit_id,fingerprint)).fetchone()
        if not row:raise ValueError('算法与审计记录不匹配')
        evidence=json.loads(row['report_json'])
        if not evidence.get('engineering_reproduced'):raise PermissionError('代码未通过独立复现')
        self.db.execute('INSERT INTO v06_approvals VALUES(?,?,?,?,?)',
                        (fingerprint,audit_id,reviewer,now(),'研究库收录；不认可彩票预测优势；不自动激活过滤'))
        self.db.execute('UPDATE v06_algorithms SET state=? WHERE fingerprint=?',('research_approved',fingerprint))
        self.db.commit()
        return {'fingerprint':fingerprint,'state':'research_approved',
                'prediction_validated':False,'ranking_not_changed':True}
