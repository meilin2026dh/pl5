"""PL5 V1.4 — immutable candidate masks and explicit experimental admission.

This registry NEVER executes algorithm code, asserts predictive advantage, or
allows a client to self-approve. A locally approved mask is applicable only to
its predeclared cutoff: changed data requires a new review/version.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Iterable

import numpy as np

from .integration_bridge import BIT_BYTES, N, decode_mask, encode_mask

STATES = ('candidate', 'experiment_reviewed', 'approved_experimental', 'revoked')


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _text(value: str, label: str, limit: int = 200) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit or '\0' in value:
        raise ValueError(f'{label}无效')
    return value.strip()


def _iso_date(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('日期必须为YYYY-MM-DD')
    date.fromisoformat(value)
    return value


class Registry:
    """Local SQLite ledger; do not create it inside a public HTTP directory."""
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if self.path.exists() and self.path.is_dir():
            raise ValueError('数据库路径不能为目录')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS candidates(
          id TEXT PRIMARY KEY, title TEXT NOT NULL, family TEXT NOT NULL,
          creator TEXT NOT NULL, source_ref TEXT NOT NULL,
          cutoff_issue TEXT NOT NULL, cutoff_date TEXT NOT NULL,
          data_sha256 TEXT NOT NULL, source_mask_sha256 TEXT NOT NULL, mask_sha256 TEXT NOT NULL,
          mask_blob BLOB NOT NULL, excluded_count INTEGER NOT NULL,
          state TEXT NOT NULL CHECK(state IN ('candidate','experiment_reviewed','approved_experimental','revoked')),
          created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS experiments(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          candidate_id TEXT NOT NULL REFERENCES candidates(id),
          snapshot_sha256 TEXT NOT NULL, period_count INTEGER NOT NULL,
          removed_hits INTEGER NOT NULL, fair_expected_removed REAL NOT NULL,
          report_json TEXT NOT NULL, report_sha256 TEXT NOT NULL,
          created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reviews(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          candidate_id TEXT NOT NULL REFERENCES candidates(id),
          experiment_id INTEGER NOT NULL REFERENCES experiments(id),
          reviewer TEXT NOT NULL, statement TEXT NOT NULL,
          created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events(
          seq INTEGER PRIMARY KEY AUTOINCREMENT,
          candidate_id TEXT NOT NULL, event TEXT NOT NULL,
          event_json TEXT NOT NULL, prev_sha256 TEXT NOT NULL,
          event_sha256 TEXT NOT NULL, created_at TEXT NOT NULL);
        ''')
        self.db.commit()

    def close(self):
        self.db.close()

    def _event(self, key, event, body):
        last = self.db.execute('SELECT event_sha256 FROM events ORDER BY seq DESC LIMIT 1').fetchone()
        previous = last['event_sha256'] if last else '0' * 64
        payload = _canonical(dict(candidate_id=key, event=event, data=body))
        digest = _sha((previous + payload).encode())
        self.db.execute('INSERT INTO events(candidate_id,event,event_json,prev_sha256,event_sha256,created_at) VALUES (?,?,?,?,?,?)',
                        (key, event, payload, previous, digest, _now()))

    def verify_ledger(self) -> bool:
        previous = '0'*64
        for row in self.db.execute('SELECT * FROM events ORDER BY seq'):
            if row['prev_sha256'] != previous or _sha((previous + row['event_json']).encode()) != row['event_sha256']:
                return False
            previous = row['event_sha256']
        return True

    def register(self, *, title: str, family: str, creator: str,
                 source_ref: str, cutoff_issue: str, cutoff_date: str,
                 data_sha256: str, excluded: np.ndarray, source_mask: np.ndarray | None = None) -> dict:
        title = _text(title, '算法名称', 160)
        family = _text(family, '算法族', 80)
        creator = _text(creator, '创建者', 100)
        source_ref = _text(source_ref, '来源', 300)
        if not re.fullmatch(r'\d{1,20}', cutoff_issue or ''):
            raise ValueError('截止期号无效')
        cutoff_date = _iso_date(cutoff_date)
        if not isinstance(data_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', data_sha256):
            raise ValueError('数据摘要必须为小写SHA256')
        arr = np.asarray(excluded)
        if arr.dtype != np.dtype('bool') or arr.shape != (N,):
            raise ValueError('规则过滤掩码必须是100000位bool数组')
        count = int(arr.sum())
        if count <= 0 or count >= N:
            raise ValueError('不接受无效的空过滤或全集删除规则')
        domain = np.ones(N,dtype=bool) if source_mask is None else np.asarray(source_mask)
        if domain.dtype != np.dtype('bool') or domain.shape != (N,):
            raise ValueError('来源域掩码必须是100000位布尔数组')
        if np.any(arr & ~domain):
            raise ValueError('过滤掩码超出来源域')
        source_digest = _sha(np.packbits(domain,bitorder='little').tobytes())
        raw = np.packbits(arr, bitorder='little').tobytes()
        digest = _sha(raw)
        signature = dict(title=title, family=family, creator=creator, source_ref=source_ref,
                         cutoff_issue=cutoff_issue, cutoff_date=cutoff_date,
                         data_sha256=data_sha256, source_mask_sha256=source_digest,mask_sha256=digest)
        key = _sha(_canonical(signature).encode())
        if self.db.execute('SELECT 1 FROM candidates WHERE id=?',(key,)).fetchone():
            return {'id':key, 'new':False, 'state':self.get(key)['state']}
        with self.db:
            self.db.execute('INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                            (key,title,family,creator,source_ref,cutoff_issue,cutoff_date,
                             data_sha256,source_digest,digest,raw,count,'candidate',_now()))
            self._event(key,'registered',{'mask_sha256':digest,'excluded_count':count,'cutoff_issue':cutoff_issue})
        return {'id':key,'new':True,'state':'candidate','mask_sha256':digest}

    def get(self, key: str) -> dict:
        row = self.db.execute('SELECT * FROM candidates WHERE id=?',(key,)).fetchone()
        if row is None:
            raise KeyError(f'算法ID不存在: {key}')
        obj=dict(row)
        if len(obj['mask_blob']) != BIT_BYTES or _sha(obj['mask_blob']) != obj['mask_sha256']:
            raise ValueError('算法掩码被损坏或篡改')
        obj.pop('mask_blob')
        return obj

    def list_candidates(self, limit: int = 100) -> list[dict]:
        rows=self.db.execute('SELECT id FROM candidates ORDER BY created_at DESC LIMIT ?',
                             (max(1,min(limit,300)),)).fetchall()
        return [self.get(row['id']) for row in rows]

    def mask(self, key: str, *, require_approval: bool = True, cutoff_issue: str | None = None) -> np.ndarray:
        row = self.db.execute('SELECT * FROM candidates WHERE id=?',(key,)).fetchone()
        if row is None:
            raise KeyError('算法ID不存在')
        if require_approval and row['state'] != 'approved_experimental':
            raise PermissionError('算法未经实验规则审批或已被撤销')
        # V1.5 operational pause is independent of V1.4 approval/revocation.
        if require_approval and self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='v15_pauses'").fetchone():
            paused=self.db.execute('SELECT cleared_at FROM v15_pauses WHERE candidate_id=?',(key,)).fetchone()
            if paused is not None and paused['cleared_at'] is None:
                raise PermissionError('算法已被V1.5健康监测暂停，需人工复审')
        if cutoff_issue is not None and row['cutoff_issue'] != cutoff_issue:
            raise PermissionError('算法基于不同截止期生成，请重新验证并注册新版本')
        if _sha(row['mask_blob']) != row['mask_sha256']:
            raise ValueError('算法掩码摘要不符')
        return np.unpackbits(np.frombuffer(row['mask_blob'],dtype=np.uint8), bitorder='little').astype(bool)

    def evaluate_holdout(self, key: str, draws: Iterable[dict], *, snapshot_sha256: str) -> dict:
        obj=self.get(key)
        if obj['state'] != 'candidate':
            raise PermissionError('仅待研究候选可提交新实验；不可重复利用测试集升级')
        if not re.fullmatch(r'[0-9a-f]{64}', snapshot_sha256):
            raise ValueError('快照摘要不合法')
        rows=list(draws)
        if len(rows)<10 or len(rows)>10000:
            raise ValueError('独立测试至少10期、不超过10000期')
        ids=set(); dates=set()
        for d in rows:
            if not isinstance(d,dict) or not re.fullmatch(r'\d{1,20}',str(d.get('issue',''))):
                raise ValueError('测试期号无效')
            when=_iso_date(d.get('date'))
            n=d.get('number')
            if not isinstance(n,str) or not re.fullmatch(r'\d{5}',n):
                raise ValueError('开奖号码格式无效')
            if when <= obj['cutoff_date']:
                raise ValueError('测试期必须晚于候选规则的训练截止日期')
            if d['issue'] in ids or when in dates:
                raise ValueError('独立测试中存在重复期号或日期')
            ids.add(d['issue']);dates.add(when)
        ban=self.mask(key, require_approval=False)
        removed=sum(bool(ban[int(d['number'])]) for d in rows)
        probability=obj['excluded_count']/N
        report=dict(candidate_id=key, periods=len(rows), removed_hits=removed,
                    retained_hits=len(rows)-removed, excluded_fraction=probability,
                    fair_expected_removed=len(rows)*probability,
                    observed_removed_fraction=removed/len(rows),
                    data_cutoff=obj['cutoff_issue'],
                    test_first=min(dates),test_last=max(dates),
                    proof='mechanical_holdout_check_only',
                    warning='提交者须保证训练未使用此区间。实验通过不代表预测有效；不得据此自动批准或宣称独立前向效果。')
        text=_canonical(report)
        with self.db:
            cur=self.db.execute('INSERT INTO experiments(candidate_id,snapshot_sha256,period_count,removed_hits,fair_expected_removed,report_json,report_sha256,created_at) VALUES(?,?,?,?,?,?,?,?)',
                                (key,snapshot_sha256,len(rows),removed,len(rows)*probability,text,_sha(text.encode()),_now()))
            self.db.execute('UPDATE candidates SET state=? WHERE id=?',('experiment_reviewed',key))
            self._event(key,'holdout_recorded',{'experiment_id':cur.lastrowid,'report_sha256':_sha(text.encode())})
        return {'experiment_id':cur.lastrowid,**report}

    def approve_experimental(self, key: str, *, experiment_id: int, reviewer: str, consent: str) -> dict:
        if consent!='APPROVE_EXPERIMENTAL_NOT_PREDICTIVE':
            raise PermissionError('必须明确确认仅批准实验性规则，而非预测能力')
        reviewer=_text(reviewer,'审批人',100)
        obj=self.get(key)
        if obj['state'] != 'experiment_reviewed':
            raise PermissionError('算法必须先完成独立测试记录，且不得重复审批')
        if reviewer.casefold()==obj['creator'].casefold():
            raise PermissionError('创建者不得自审')
        row=self.db.execute('SELECT * FROM experiments WHERE id=? AND candidate_id=?',
                            (experiment_id,key)).fetchone()
        if not row:
            raise ValueError('审批未引用正确的实验记录')
        if _sha(row['report_json'].encode()) != row['report_sha256']:
            raise ValueError('实验报告完整性校验失败')
        with self.db:
            self.db.execute('UPDATE candidates SET state=? WHERE id=?',('approved_experimental',key))
            self.db.execute('INSERT INTO reviews(candidate_id,experiment_id,reviewer,statement,created_at) VALUES(?,?,?,?,?)',
                            (key,experiment_id,reviewer,'仅批准实验雕刻刀；不证明预测概率提升',_now()))
            self._event(key,'experimental_approved',{'experiment_id':experiment_id,'reviewer':reviewer})
        return {'id':key,'state':'approved_experimental','prediction_validated':False}

    def revoke(self, key: str, *, reviewer: str, reason: str):
        reviewer=_text(reviewer,'审批人',100)
        reason=_text(reason,'撤销原因',500)
        obj=self.get(key)
        if obj['state']=='revoked':
            raise PermissionError('已经撤销')
        with self.db:
            self.db.execute('UPDATE candidates SET state=? WHERE id=?',('revoked',key))
            self._event(key,'revoked',{'reviewer':reviewer,'reason':reason})
        return {'id':key,'state':'revoked'}


def from_github_rule(request: dict, item: dict, *, creator: str, cutoff_date: str,
                     source_ref: str, data_sha256: str, registry: Registry) -> dict:
    """Import an already-computed TypeScript rule mask, never its executable code."""
    base=decode_mask(request['base'])
    keep=decode_mask(item['kept'])
    if np.any(keep & ~base):
        raise ValueError('GitHub规则掩码不是来源域子集')
    cutoff=request.get('meta',{}).get('reference_issue')
    if not cutoff:
        raise ValueError('必须有固定的历史截止期')
    return registry.register(title=item['label'],family=item['group'],creator=creator,
                             source_ref=source_ref,cutoff_issue=cutoff,cutoff_date=cutoff_date,
                             data_sha256=data_sha256,excluded=base & ~keep,source_mask=base)
