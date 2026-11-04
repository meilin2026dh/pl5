"""Append-only *prospective* top-K pre-registration and verification.

All rules and candidate sets are fixed BEFORE the relevant new draw is in the
provided historical file.  This ledger is for research and does not prove the
source was official or that the operator did not know the future result.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
import sqlite3
from typing import Iterable


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def require_period(value: str) -> str:
    value = str(value).strip()
    if not re.fullmatch(r'[0-9]{4,16}',value):
        raise ValueError('期号必须为4到16位数字字符串')
    return value


def _validate_numbers(numbers: Iterable[str]) -> list[str]:
    out = list(numbers)
    if not 1 <= len(out) <= 100 or len(out) != len(set(out)):
        raise ValueError('预注册必须含1至100注互不重复的号码')
    if any(not isinstance(x,str) or not re.fullmatch(r'[0-9]{5}',x) for x in out):
        raise ValueError('每注必须是5位数字字符串（保留前导零）')
    return out


@dataclass(frozen=True)
class FrozenPrediction:
    target_period: str
    previous_period: str
    created_at: str
    candidates: tuple[str,...]
    history_sha256: str
    algorithm_sha256: str
    source_description: str
    commitment_sha256: str


def initialize(db: sqlite3.Connection):
    db.execute('''CREATE TABLE IF NOT EXISTS predictions (
      target_period TEXT PRIMARY KEY,
      previous_period TEXT NOT NULL,
      created_at TEXT NOT NULL,
      candidates_json TEXT NOT NULL,
      history_sha256 TEXT NOT NULL,
      algorithm_sha256 TEXT NOT NULL,
      source_description TEXT NOT NULL,
      commitment_sha256 TEXT NOT NULL UNIQUE
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS outcomes (
      target_period TEXT PRIMARY KEY REFERENCES predictions(target_period),
      observed_at TEXT NOT NULL,
      result TEXT NOT NULL,
      is_hit INTEGER NOT NULL,
      verified_data_sha256 TEXT NOT NULL,
      observed_source TEXT NOT NULL
    )''')
    # No retroactive editing or replacement of precommitted predictions/outcomes.
    db.executescript('''
      CREATE TRIGGER IF NOT EXISTS predictions_no_update BEFORE UPDATE ON predictions
      BEGIN SELECT RAISE(ABORT, 'immutable_prediction'); END;
      CREATE TRIGGER IF NOT EXISTS predictions_no_delete BEFORE DELETE ON predictions
      BEGIN SELECT RAISE(ABORT, 'immutable_prediction'); END;
      CREATE TRIGGER IF NOT EXISTS outcomes_no_update BEFORE UPDATE ON outcomes
      BEGIN SELECT RAISE(ABORT, 'immutable_outcome'); END;
      CREATE TRIGGER IF NOT EXISTS outcomes_no_delete BEFORE DELETE ON outcomes
      BEGIN SELECT RAISE(ABORT, 'immutable_outcome'); END;
    ''')
    db.commit()


def precommit(db:sqlite3.Connection, *,target_period:str,previous_period:str,
              candidates:list[str],history_sha256:str,algorithm_sha256:str,
              source_description:str)->dict:
    initialize(db)
    target_period=require_period(target_period)
    previous_period=require_period(previous_period)
    if int(target_period)<=int(previous_period):
        raise ValueError('目标期号必须晚于CSV的最后已知期号')
    candidates=_validate_numbers(candidates)
    if not re.fullmatch('[0-9a-f]{64}',history_sha256): raise ValueError('历史指纹错误')
    if not re.fullmatch('[0-9a-f]{64}',algorithm_sha256): raise ValueError('算法指纹错误')
    if not source_description.strip(): raise ValueError('必须提供官方数据核验来源声明')
    created=utc_now()
    canon={'target_period':target_period,'previous_period':previous_period,'created_at':created,
           'candidates':candidates,'history_sha256':history_sha256,
           'algorithm_sha256':algorithm_sha256,'source_description':source_description}
    signature=sha256(json.dumps(canon,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    db.execute('''INSERT INTO predictions(target_period,previous_period,created_at,candidates_json,
       history_sha256,algorithm_sha256,source_description,commitment_sha256)
       VALUES(?,?,?,?,?,?,?,?)''',(target_period,previous_period,created,json.dumps(candidates),
           history_sha256,algorithm_sha256,source_description,signature))
    db.commit()
    return {'target_period':target_period,'count':len(candidates),'committed_at_utc':created,
            'commitment_sha256':signature,'immutable':True,
            'warning':'本地封存可复核，但无法单独证明在开奖前生成，也不能证明CSV真实性'}


def settle_from_history(db:sqlite3.Connection, *,period_to_number:dict[str,str],
                       data_sha256:str,source_description:str) -> dict:
    initialize(db)
    if not source_description.strip():raise ValueError('必须声明核验来源')
    if not re.fullmatch('[0-9a-f]{64}',data_sha256):raise ValueError('历史文件SHA256无效')
    rows=db.execute('''SELECT target_period,candidates_json FROM predictions
       WHERE target_period NOT IN (SELECT target_period FROM outcomes)''').fetchall()
    settled=[]
    for period,candidates_json in rows:
        if period not in period_to_number: continue
        draw=period_to_number[period]
        if not re.fullmatch(r'[0-9]{5}',draw):raise ValueError(f'{period}期开奖号码格式错误')
        hit=int(draw in set(json.loads(candidates_json)))
        db.execute('''INSERT INTO outcomes(target_period,observed_at,result,is_hit,
                   verified_data_sha256,observed_source) VALUES(?,?,?,?,?,?)''',
                   (period,utc_now(),draw,hit,data_sha256,source_description))
        settled.append({'period':period,'number':draw,'hit':bool(hit)})
    db.commit()
    return {'newly_settled':len(settled),'results':settled}


def outcome_report(db:sqlite3.Connection)->dict:
    initialize(db)
    rows=db.execute('''SELECT p.target_period,p.created_at,p.candidates_json,p.commitment_sha256,
         o.result,o.is_hit,o.observed_at FROM predictions p LEFT JOIN outcomes o
         ON p.target_period=o.target_period ORDER BY CAST(p.target_period AS INTEGER)''').fetchall()
    closed=[row for row in rows if row[4] is not None]
    n=len(closed)
    # Diverse K values: exact P(at least one hit) = 1 - product(1-K_t / 100000).
    def coverage(seq):
        miss=1.0
        for item in seq:miss*=1-len(json.loads(item[2]))/100000
        return 1-miss
    rolling=[]
    for i in range(9,len(closed)):
        part=closed[i-9:i+1]
        rolling.append({'start_period':part[0][0],'end_period':part[-1][0],
                        'observed_any_hit':bool(any(x[5] for x in part)),
                        'random_baseline_any_hit':coverage(part)})
    return {'total_predictions':len(rows),'pending':len(rows)-n,'observed_periods':n,
            'observed_hits':sum(int(row[5]) for row in closed),
            'expected_random_hits':sum(len(json.loads(row[2]))/100000 for row in closed),
            'rolling_10_period_windows':rolling,
            'guarantees_win_within_10':False,
            'warning':'仅评价已封存且随后录入的记录；重复滑动窗口不是独立试验，不能仅据此声称预测优势'}
