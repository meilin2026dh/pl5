"""PL5 V1.5.2: local append-only prospective audit of ESSE sculpting.

This ledger is a *research notebook*. It does not prove pre-draw publication time,
origin authenticity, fair-draw violations, or predictive advantage.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import re
import sqlite3

from .evolution_v15 import validate_draws
from .integration_bridge import run_bridge, decode_mask, encode_mask
import numpy as np

VERSION = 'pl5-sculpt-forward-v152'
ZERO = '0' * 64


def canon(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(x):
    return sha256(canon(x).encode('utf-8')).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def issue(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4,20}', value):
        raise ValueError('期号必须为4—20位数字字符串')
    return value


def clean_snapshot(rows):
    return validate_draws(rows)


class SculptLedger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA busy_timeout=4000')
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS seals (
            target_issue TEXT PRIMARY KEY, previous_issue TEXT NOT NULL,
            created_at TEXT NOT NULL, receipt_json TEXT NOT NULL,
            receipt_sha256 TEXT NOT NULL UNIQUE,
            history_sha256 TEXT NOT NULL,
            candidate_sha256 TEXT NOT NULL,
            source_label TEXT NOT NULL
          );
          CREATE TABLE IF NOT EXISTS settlements (
            target_issue TEXT PRIMARY KEY REFERENCES seals(target_issue),
            observed_at TEXT NOT NULL, draw_number TEXT NOT NULL,
            official_snapshot_sha256 TEXT NOT NULL,
            result_json TEXT NOT NULL, result_sha256 TEXT NOT NULL
          );
          CREATE TABLE IF NOT EXISTS evidence_events (
            seq INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL,
            target_issue TEXT NOT NULL, payload_json TEXT NOT NULL,
            prev_sha256 TEXT NOT NULL, event_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL
          );
          CREATE TRIGGER IF NOT EXISTS seals_no_update BEFORE UPDATE ON seals
            BEGIN SELECT RAISE(ABORT,'immutable_seal'); END;
          CREATE TRIGGER IF NOT EXISTS seals_no_delete BEFORE DELETE ON seals
            BEGIN SELECT RAISE(ABORT,'immutable_seal'); END;
          CREATE TRIGGER IF NOT EXISTS settlements_no_update BEFORE UPDATE ON settlements
            BEGIN SELECT RAISE(ABORT,'immutable_settlement'); END;
          CREATE TRIGGER IF NOT EXISTS settlements_no_delete BEFORE DELETE ON settlements
            BEGIN SELECT RAISE(ABORT,'immutable_settlement'); END;
          CREATE TRIGGER IF NOT EXISTS evidence_events_no_update BEFORE UPDATE ON evidence_events
            BEGIN SELECT RAISE(ABORT,'immutable_event'); END;
          CREATE TRIGGER IF NOT EXISTS evidence_events_no_delete BEFORE DELETE ON evidence_events
            BEGIN SELECT RAISE(ABORT,'immutable_event'); END;
        ''')
        self.db.commit()

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _append(self, kind, target, payload):
        latest = self.db.execute('SELECT event_sha256 FROM evidence_events ORDER BY seq DESC LIMIT 1').fetchone()
        prev = latest['event_sha256'] if latest else ZERO
        text = canon({'kind':kind,'target_issue':target,'payload':payload})
        stamp = now()
        head = sha256((prev + text).encode('utf8')).hexdigest()
        self.db.execute('INSERT INTO evidence_events(kind,target_issue,payload_json,prev_sha256,event_sha256,created_at) VALUES(?,?,?,?,?,?)',
                        (kind,target,text,prev,head,stamp))

    def verify(self):
        prev = ZERO
        errors = []
        for row in self.db.execute('SELECT * FROM evidence_events ORDER BY seq'):
            expected = sha256((prev+row['payload_json']).encode('utf8')).hexdigest()
            if row['prev_sha256'] != prev or expected != row['event_sha256']:
                errors.append('event:'+str(row['seq']))
            try:
                payload = json.loads(row['payload_json'])
                if payload['kind']!=row['kind'] or payload['target_issue']!=row['target_issue'] or canon(payload)!=row['payload_json']:
                    errors.append('event_payload:'+str(row['seq']))
            except (ValueError, KeyError, TypeError):
                errors.append('event_parse:'+str(row['seq']))
            prev=row['event_sha256']
        events = set()
        for x in self.db.execute('SELECT kind,target_issue,payload_json FROM evidence_events'):
            try:
                events.add((x['kind'], x['target_issue'], json.loads(x['payload_json'])['payload']['sha256']))
            except (ValueError, KeyError, TypeError):
                errors.append('event_index:'+x['target_issue'])
        for row in self.db.execute('SELECT * FROM seals'):
            try:
                receipt=json.loads(row['receipt_json'])
                h=digest(receipt)
                if (h!=row['receipt_sha256'] or canon(receipt)!=row['receipt_json'] or
                    receipt['target_issue']!=row['target_issue'] or receipt['previous_issue']!=row['previous_issue'] or
                    receipt['history_sha256']!=row['history_sha256'] or
                    receipt['candidate_sha256']!=row['candidate_sha256'] or
                    receipt['source_label']!=row['source_label'] or
                    ('seal',row['target_issue'],h) not in events):
                    errors.append('seal:'+row['target_issue'])
            except (ValueError,TypeError,KeyError):
                errors.append('seal_parse:'+row['target_issue'])
        for row in self.db.execute('SELECT * FROM settlements'):
            try:
                data=json.loads(row['result_json']);h=digest(data)
                if (h!=row['result_sha256'] or canon(data)!=row['result_json'] or
                    row['target_issue']!=data['target_issue'] or row['draw_number']!=data['number'] or
                    row['official_snapshot_sha256']!=data['official_snapshot_sha256'] or
                    ('settle',row['target_issue'],h) not in events):
                    errors.append('settlement:'+row['target_issue'])
            except (ValueError,TypeError,KeyError):
                errors.append('settlement_parse:'+row['target_issue'])
        seals = {r[0] for r in self.db.execute('SELECT target_issue FROM seals')}
        settled = {r[0] for r in self.db.execute('SELECT target_issue FROM settlements')}
        if not settled.issubset(seals):errors.append('orphan_settlement')
        if self.db.execute('SELECT COUNT(*) FROM evidence_events').fetchone()[0]!=len(seals)+len(settled):
            errors.append('event_count_mismatch')
        return {'ok':not errors,'errors':errors[:30]}

    def seal(self, *, target_issue, official_draws, source_label, bridge_request, registry=None, code_revision='uncommitted'):
        if not self.verify()['ok']:
            raise PermissionError('证据链异常，禁止登记新期号')
        target=issue(target_issue)
        rows=clean_snapshot(official_draws)
        last=rows[-1]
        if target in {r['issue'] for r in rows}:
            raise ValueError('目标期已出现在官方数据快照，拒绝事后封存')
        if int(target)<=int(last['issue']):
            raise ValueError('目标期号必须严格晚于最新历史期号')
        old=self.db.execute('SELECT target_issue FROM seals ORDER BY CAST(target_issue AS INTEGER) DESC LIMIT 1').fetchone()
        if old and int(target)<=int(old['target_issue']):
            raise ValueError('期号必须递增，禁止回填以前漏封存的期号')
        if not isinstance(source_label,str) or not 5<=len(source_label)<=200:
            raise ValueError('来源说明不合法')
        if not isinstance(bridge_request,dict) or bridge_request.get('meta',{}).get('reference_issue')!=last['issue']:
            raise ValueError('过滤所使用的历史截止期与最新官方快照不一致')
        if not isinstance(code_revision,str) or len(code_revision)>120:
            raise ValueError('代码版本标记无效')
        result=run_bridge(bridge_request,registry=registry)
        if result['selected_count']>100 or not result['source_guard']:
            raise ValueError('候选号码预算或来源检查未通过')
        numbers=result['top_numbers']
        if len(numbers)!=len(set(numbers)) or not numbers:
            raise ValueError('候选集为空或存在重复')
        stages=result['steps']
        for stage in stages:
            if stage['before']-stage['after']!=stage['newly_removed'] or stage['after']>stage['before']:
                raise ValueError('逐刀过滤轨迹不一致')
        base=decode_mask(bridge_request['base'])
        mask_entries=[('__source__', ~base)]
        for item in bridge_request['rules']:
            mask_entries.append((item['id'], base & ~decode_mask(item['kept'])))
        for meta in result['registered_experimental_rules']:
            if registry is None:
                raise PermissionError('注册算法必须从已审核本地注册库读取')
            mask_entries.append(('registry:'+meta['id'], base & registry.mask(meta['id'], cutoff_issue=last['issue'])))
        if [k for k,_ in mask_entries] != [x['key'] for x in stages]:
            raise ValueError('逐刀顺序与计算来源不一致')
        stage_masks = [{'key': k, 'excluded_mask': encode_mask(m)} for k,m in mask_entries]
        receipt={'version':VERSION,'target_issue':target,'previous_issue':last['issue'],
                 'cutoff_date':last['date'],'created_at':now(),
                 'history_sha256':digest(rows),'source_label':source_label,
                 'request_sha256':result['request_sha256'],
                 'code_revision':code_revision,
                 'engine':result['engine'],'registered_rules':result['registered_experimental_rules'],
                 'unverified_rule_types':result['unverified_rule_types'],
                 'full_mask_parity_verified':result['full_mask_parity_verified'],
                 'independent_rule_ids':result['independent_rule_ids'],
                 'source_guard':result['source_guard'],'initial':result['base_count'],
                 'strict_kept':result['strict_keep_count'],'restored':result['restored_for_quota'],
                 'stages':stages,'stage_masks':stage_masks,'marginals':result['marginals'],
                 'candidates':numbers,'candidate_sha256':digest(numbers),
                 'fair_probability':len(numbers)/100000,
                 'status':'exploratory_non_predictive'}
        raw=canon(receipt);hashcode=digest(receipt)
        with self.db:
            self.db.execute('INSERT INTO seals(target_issue,previous_issue,created_at,receipt_json,receipt_sha256,history_sha256,candidate_sha256,source_label) VALUES (?,?,?,?,?,?,?,?)',
                            (target,last['issue'],receipt['created_at'],raw,hashcode,receipt['history_sha256'],receipt['candidate_sha256'],source_label))
            self._append('seal',target,{'sha256':hashcode})
        return {'target_issue':target,'count':len(numbers),'receipt_sha256':hashcode,
                'history_sha256':receipt['history_sha256'],'stages':len(stages),
                'restored_for_quota':receipt['restored'],
                'note':'本地封存不能独立证明早于开奖；不证明中奖概率增益'}

    def settle(self, *, official_draws, source_label):
        if not self.verify()['ok']:raise PermissionError('证据链异常，拒绝开奖核验')
        rows=clean_snapshot(official_draws)
        by_issue={r['issue']:r for r in rows}
        if not isinstance(source_label,str) or not 5<=len(source_label)<=200:
            raise ValueError('核验来源说明无效')
        completed=[];history_digest=digest(rows)
        for old in self.db.execute('SELECT target_issue,draw_number FROM settlements'):
            previous=by_issue.get(old['target_issue'])
            if previous and previous['number']!=old['draw_number']:
                raise ValueError('已结算期号的官方号码发生修改，拒绝静默覆盖')
        pending=self.db.execute('SELECT * FROM seals WHERE target_issue NOT IN (SELECT target_issue FROM settlements) ORDER BY CAST(target_issue AS INTEGER)').fetchall()
        # Fail the entire batch first if the prior latest history was revised.
        for seal in pending:
            if seal['target_issue'] not in by_issue:continue
            receipt=json.loads(seal['receipt_json'])
            prefix=[r for r in rows if int(r['issue'])<=int(receipt['previous_issue'])]
            if not prefix or prefix[-1]['issue']!=receipt['previous_issue'] or digest(prefix)!=receipt['history_sha256']:
                raise ValueError('官方历史快照的既往记录发生变化，请人工核对后再结算')
            if by_issue[seal['target_issue']]['date']<=receipt['cutoff_date']:
                raise ValueError('开奖号码日期不晚于封存截止日期')
        with self.db:
            for seal in pending:
                target=seal['target_issue']
                if target not in by_issue:continue
                receipt=json.loads(seal['receipt_json'])
                draw=by_issue[target]
                hit=draw['number'] in receipt['candidates']
                n=int(draw['number']); first_cut=False; decisions=[]
                for i, mask in enumerate(receipt['stage_masks']):
                    cuts=bool(decode_mask(mask['excluded_mask'])[n])
                    is_first=cuts and not first_cut
                    decisions.append({'key':mask['key'], 'would_cut':cuts, 'first_cut':is_first})
                    first_cut=first_cut or cuts
                data={'version':VERSION,'knife_decisions':decisions,'target_issue':target,'number':draw['number'],
                      'draw_date':draw['date'],'is_hit':bool(hit),
                      'candidate_count':len(receipt['candidates']),
                      'receipt_sha256':seal['receipt_sha256'],
                      'official_snapshot_sha256':history_digest,
                      'source_label':source_label,'observed_at':now()}
                raw=canon(data);sha=digest(data)
                self.db.execute('INSERT INTO settlements(target_issue,observed_at,draw_number,official_snapshot_sha256,result_json,result_sha256) VALUES(?,?,?,?,?,?)',
                                (target,data['observed_at'],draw['number'],history_digest,raw,sha))
                self._append('settle',target,{'sha256':sha})
                completed.append({'issue':target,'number':draw['number'],'hit':hit})
        return {'newly_settled':len(completed),'results':completed,'snapshot_sha256':history_digest}

    def report(self):
        check=self.verify()
        rows=self.db.execute('''SELECT s.target_issue,s.receipt_json,z.result_json FROM seals s
                LEFT JOIN settlements z ON s.target_issue=z.target_issue ORDER BY CAST(s.target_issue AS INTEGER)''').fetchall()
        entries=[]
        for row in rows:
            r=json.loads(row['receipt_json']);v=json.loads(row['result_json']) if row['result_json'] else None
            entries.append({'issue':r['target_issue'],'candidate_count':len(r['candidates']),
                            'hit':None if v is None else v['is_hit'],
                            'fair_probability':r['fair_probability'],
                            'receipt_sha256':digest(r),'stages':r['stages'],
                            'restored':r['restored'],'number':v['number'] if v else None,
                            'knife_decisions':v['knife_decisions'] if v else None})
        # Only the uninterrupted prefix of registered predictions is valid for running stats.
        prefix=[]
        for row in entries:
            if row['hit'] is None:break
            prefix.append(row)
        per_knife={}
        for e in prefix:
            for decision in e['knife_decisions']:
                key=decision['key']
                stat=per_knife.setdefault(key,{'would_cut_actual':0,'first_cut_actual':0,'audited_periods':0})
                stat['audited_periods']+=1
                stat['would_cut_actual']+=int(decision['would_cut'])
                stat['first_cut_actual']+=int(decision['first_cut'])
        groups=[]
        for i in range(0,max(0,len(prefix)-9)):
            block=prefix[i:i+10]
            groups.append({'first':block[0]['issue'],'last':block[-1]['issue'],
                           'hit':any(x['hit'] for x in block),
                           'fair_random_at_least_once':1.0-__import__('math').prod(1-x['fair_probability'] for x in block),
                           'registered_10_only':True})
        return {'version':VERSION,'integrity':check,'seals':len(entries),
                'settled':sum(x['hit'] is not None for x in entries),
                'pending':sum(x['hit'] is None for x in entries),
                'first_pending_blocks_headline':bool(entries and len(prefix)<len(entries)),
                'auditable_settled_prefix':len(prefix),
                'hits_in_prefix':sum(bool(x['hit']) for x in prefix),
                'expected_fair_hits_in_prefix':sum(x['fair_probability'] for x in prefix),
                'rolling_10_registered':groups[-15:],
                'knife_actuals_in_prefix':per_knife,
                'latest':entries[-1] if entries else None,
                'predictive_advantage_proven':False,
                'warning':'记录仅为本地证据，未独立证明开奖前提交或覆盖所有实际期次。每期100注公平基线0.1%。'}
