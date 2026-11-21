"""可审计SQLite知识库：多来源导入、冲突阻断、预注册与测试集封存。"""
from __future__ import annotations
import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from .data import Draws, load_csv


def _utc():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def canonical_period(period: str) -> str:
    """统一五位YYNNN与七位YYYYNNN期号；减少跨来源同期开奖被误当成两期。"""
    if re.fullmatch(r'\d{5}', period):
        return '20'+period
    if re.fullmatch(r'20\d{5}', period):
        return period
    raise ValueError(f'无法识别官方体彩期号格式：{period}；需要YYNNN或YYYYNNN')


def fingerprint(draws: Draws) -> str:
    ordered = draws.frame[['period','number']].astype(str).values.tolist()
    return hashlib.sha256(json.dumps(ordered, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def holdout_key(draws: Draws, holdout_size: int) -> str:
    """同一数据集的同一封存窗口只允许分析一次；不随算法/K/seed改变。"""
    if holdout_size < 1 or holdout_size >= len(draws.frame):
        raise ValueError('封存集大小不合法')
    return hashlib.sha256((fingerprint(draws)+'|'+str(holdout_size)).encode()).hexdigest()


@dataclass
class ImportReceipt:
    status: str
    source_id: int
    records: int
    inserted: int
    fingerprint: str
    warnings: tuple[str, ...]


class KnowledgeBase:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys = ON')
        self.conn.executescript('''
        CREATE TABLE IF NOT EXISTS sources (
          id INTEGER PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL,
          sha256 TEXT NOT NULL UNIQUE, dataset_fingerprint TEXT NOT NULL,
          imported_at TEXT NOT NULL, rows INTEGER NOT NULL,
          first_period TEXT NOT NULL, last_period TEXT NOT NULL,
          warning_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS draws (
          period TEXT PRIMARY KEY, number TEXT NOT NULL, first_source_id INTEGER NOT NULL,
          FOREIGN KEY(first_source_id) REFERENCES sources(id));
        CREATE TABLE IF NOT EXISTS source_draws (
          source_id INTEGER NOT NULL, period TEXT NOT NULL, number TEXT NOT NULL,
          PRIMARY KEY(source_id, period), FOREIGN KEY(source_id) REFERENCES sources(id));
        CREATE TABLE IF NOT EXISTS experiments (
          id INTEGER PRIMARY KEY, holdout_key TEXT NOT NULL UNIQUE,
          dataset_fingerprint TEXT NOT NULL, registered_at TEXT NOT NULL,
          preregistration TEXT NOT NULL, dev_result TEXT NOT NULL,
          holdout_result TEXT NOT NULL, status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS hypotheses (
          id INTEGER PRIMARY KEY, experiment_id INTEGER NOT NULL,
          name TEXT NOT NULL, specification TEXT NOT NULL, decision TEXT NOT NULL,
          evidence TEXT NOT NULL,
          FOREIGN KEY(experiment_id) REFERENCES experiments(id));
        ''')
        self.conn.commit()

    def close(self):
        self.conn.close()

    def import_csv(self, content: bytes, source_name: str, *, kind='user_supplied', demo=False) -> ImportReceipt:
        if demo:
            raise ValueError('演示数据禁止导入真实来源知识库。请直接用 --demo-research 运行演示。')
        if not source_name.strip():
            raise ValueError('数据来源名称不能为空')
        draws = load_csv(content, is_demo=False)
        # 拒绝潜在前导零丢失：导入知识库要求来源保留全部5位。
        if any('左补零' in w for w in draws.warnings):
            raise ValueError('存在不足5位的号码。严格入库要求每个开奖号码恰好5位；请向来源核实前导零。')
        digest = hashlib.sha256(content).hexdigest()
        old = self.conn.execute('SELECT * FROM sources WHERE sha256=?', (digest,)).fetchone()
        if old:
            return ImportReceipt('unchanged', int(old['id']), len(draws.frame), 0,
                                 str(old['dataset_fingerprint']), tuple(draws.warnings))
        df = draws.frame
        records = [(canonical_period(str(row.period)), str(row.number)) for row in df.itertuples(index=False)]
        if len({p for p,_ in records})!=len(records):
            raise ValueError('期号格式归一化后出现重复期号，拒绝入库。')
        records.sort(key=lambda item:int(item[0]))
        conflicts = []
        for period, num in records:
            existing = self.conn.execute('SELECT number FROM draws WHERE period=?', (period,)).fetchone()
            if existing and existing['number'] != num:
                conflicts.append((period, existing['number'], num))
        if conflicts:
            head = '; '.join(f'{p}:库内{a} ≠ 新源{b}' for p,a,b in conflicts[:5])
            raise ValueError(f'数据源冲突 {len(conflicts)} 条，拒绝入库、未覆盖旧记录：{head}')
        with self.conn:
            cursor = self.conn.execute('''INSERT INTO sources
                (name,kind,sha256,dataset_fingerprint,imported_at,rows,first_period,last_period,warning_json)
                VALUES (?,?,?,?,?,?,?,?,?)''', (
                source_name,kind,digest,fingerprint(draws),_utc(),len(records),
                records[0][0],records[-1][0],json.dumps(draws.warnings,ensure_ascii=False)))
            sid = int(cursor.lastrowid)
            prev_count = self.conn.total_changes
            self.conn.executemany('INSERT OR IGNORE INTO draws VALUES (?,?,?)',
                                  [(p,n,sid) for p,n in records])
            inserted = self.conn.total_changes - prev_count
            self.conn.executemany('INSERT INTO source_draws VALUES (?,?,?)',
                                  [(sid,p,n) for p,n in records])
        return ImportReceipt('imported',sid,len(records),inserted,fingerprint(draws),tuple(draws.warnings))

    def merged_draws(self) -> Draws:
        rows = self.conn.execute('SELECT period,number FROM draws').fetchall()
        if not rows:
            raise ValueError('知识库暂无真实开奖数据，请先导入CSV。')
        content = 'period,number\n' + ''.join(f"{r['period']},{r['number']}\n" for r in rows)
        # load_csv支持期号数值化排序
        return load_csv(content.encode('utf-8'))

    def sources(self) -> list[dict]:
        return [dict(r) for r in self.conn.execute('SELECT * FROM sources ORDER BY id DESC')]

    def experiments(self) -> list[dict]:
        return [dict(r) for r in self.conn.execute('SELECT * FROM experiments ORDER BY id DESC')]

    def get_experiment(self, key: str) -> dict | None:
        row = self.conn.execute('SELECT * FROM experiments WHERE holdout_key=?', (key,)).fetchone()
        return dict(row) if row else None

    def preregister(self, *, key: str, dataset_sha: str, prereg: dict, dev: dict) -> int:
        """在读取任何封存集开奖结果之前，原子锁定研究设计。"""
        with self.conn:
            cur = self.conn.execute('''INSERT INTO experiments
                (holdout_key,dataset_fingerprint,registered_at,preregistration,dev_result,holdout_result,status)
                VALUES (?,?,?,?,?,?,?)''',
                (key,dataset_sha,_utc(),json.dumps(prereg,ensure_ascii=False),
                 json.dumps(dev,ensure_ascii=False),'{}','sealed_pending'))
        return int(cur.lastrowid)

    def finalize_experiment(self, *, key: str, holdout: dict, hypothesis_rows: list[dict]):
        with self.conn:
            existing = self.get_experiment(key)
            if not existing or existing['status'] != 'sealed_pending':
                raise ValueError('封存实验未注册或已结束，无法再写入测试集。')
            expid = int(existing['id'])
            self.conn.execute('UPDATE experiments SET holdout_result=?, status=? WHERE id=?',
                              (json.dumps(holdout,ensure_ascii=False),holdout['status'],expid))
            self.conn.executemany('''INSERT INTO hypotheses
                (experiment_id,name,specification,decision,evidence)
                VALUES (?,?,?,?,?)''', [(
                expid,h['name'],json.dumps(h,ensure_ascii=False),h.get('decision','rejected'),
                json.dumps(h.get('metrics',{}),ensure_ascii=False)) for h in hypothesis_rows])
            return expid
