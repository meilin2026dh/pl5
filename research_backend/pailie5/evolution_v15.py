"""V1.5 experimental competition and bounded algorithm growth.

Never interprets an exploratory score as a winning probability.  No algorithm
can be approved automatically.  The supplied draw file is NOT authenticated
by this module; provenance must be verified outside the process.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import re
import sqlite3
from typing import Iterable

import numpy as np
from scipy.stats import binomtest

from .algorithm_registry_v14 import Registry
from .integration_bridge import N, encode_mask

VERSION = 'pl5-evolution-v15'


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value) -> str:
    return sha256(canonical(value).encode('utf-8')).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def validate_draws(draws: Iterable[dict]) -> list[dict]:
    """Strict data validation; does not claim that the origin is official."""
    if not isinstance(draws, list) or not 1 <= len(draws) <= 10000:
        raise ValueError('历史记录需要1至10000期')
    clean, issues, dates = [], set(), set()
    for raw in draws:
        if not isinstance(raw, dict):
            raise ValueError('开奖行必须是JSON对象')
        issue, when, number = raw.get('issue'), raw.get('date'), raw.get('number')
        if not isinstance(issue, str) or not re.fullmatch(r'\d{1,20}', issue):
            raise ValueError('无效期号')
        if not isinstance(when, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', when):
            raise ValueError('无效日期')
        date.fromisoformat(when)
        if not isinstance(number, str) or not re.fullmatch(r'[0-9]{5}', number):
            raise ValueError('开奖号码必须是恰好五位的字符串')
        if issue in issues or when in dates:
            raise ValueError('期号或日期重复')
        issues.add(issue); dates.add(when)
        clean.append({'issue':issue, 'date':when, 'number':number})
    return sorted(clean, key=lambda x:(x['date'], int(x['issue'])))


@dataclass(frozen=True)
class Policy:
    min_forward_periods: int = 30
    family_alpha: float = 0.01
    max_competing_rules: int = 60
    max_auto_proposals: int = 5
    max_removed_fraction: float = 0.65

    def __post_init__(self):
        if not 10 <= self.min_forward_periods <= 3000:
            raise ValueError('验证期数门槛范围错误')
        if not 0 < self.family_alpha <= 0.05:
            raise ValueError('显著性上限错误')
        if not 1 <= self.max_competing_rules <= 100:
            raise ValueError('规则数量上限错误')
        if not 1 <= self.max_auto_proposals <= 12:
            raise ValueError('自动提案数量上限错误')
        if not 0 < self.max_removed_fraction <= 0.9:
            raise ValueError('规则剔除比例超限')


class EvolutionLab:
    """Uses V1.4 Registry connection; appends isolated V1.5 tables."""
    def __init__(self, registry: Registry):
        self.registry = registry
        self.db = registry.db
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS v15_scans(
            id TEXT PRIMARY KEY, snapshot_hash TEXT NOT NULL, policy_hash TEXT NOT NULL,
            report_json TEXT NOT NULL, report_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS v15_pauses(
            candidate_id TEXT PRIMARY KEY REFERENCES candidates(id),
            reason TEXT NOT NULL, scan_id TEXT NOT NULL,
            created_at TEXT NOT NULL, cleared_at TEXT);
          CREATE TABLE IF NOT EXISTS v15_proposals(
            algorithm_id TEXT PRIMARY KEY REFERENCES candidates(id),
            formula_json TEXT NOT NULL, source_digest TEXT NOT NULL,
            history_digest TEXT NOT NULL, created_at TEXT NOT NULL);
          ''')
        self.db.commit()

    def paused(self, key: str) -> bool:
        row = self.db.execute('SELECT cleared_at FROM v15_pauses WHERE candidate_id=?', (key,)).fetchone()
        return row is not None and row['cleared_at'] is None

    def pause(self, key: str, *, reason: str, scan_id: str):
        if not self.registry.verify_ledger():
            raise PermissionError('注册事件链异常，拒绝变更状态')
        info = self.registry.get(key)
        if info['state'] != 'approved_experimental':
            raise PermissionError('只允许暂停已批准的实验刀')
        if not isinstance(reason,str) or not 3 <= len(reason) <= 300:
            raise ValueError('暂停原因不合法')
        if self.paused(key):
            return False
        with self.db:
            self.db.execute('''INSERT INTO v15_pauses(candidate_id,reason,scan_id,created_at,cleared_at)
                VALUES(?,?,?,?,NULL) ON CONFLICT(candidate_id) DO UPDATE SET reason=excluded.reason,
                scan_id=excluded.scan_id,created_at=excluded.created_at,cleared_at=NULL''',
                (key, reason, scan_id, _now()))
            self.registry._event(key,'auto_paused_v15',{'scan_id':scan_id,'reason':reason})
        return True

    def resume(self, key: str, *, reviewer: str, explanation: str):
        if not self.registry.verify_ledger():
            raise PermissionError('注册事件链异常，拒绝复审')
        if not isinstance(reviewer,str) or not reviewer.strip() or len(reviewer)>100:
            raise ValueError('必须指定审查人')
        if not isinstance(explanation,str) or len(explanation.strip())<8 or len(explanation)>500:
            raise ValueError('恢复必须提供审查说明')
        if reviewer.strip().casefold()==self.registry.get(key)['creator'].casefold():
            raise PermissionError('研究作者不得自行解除健康暂停')
        if not self.paused(key):
            raise ValueError('该算法未暂停')
        with self.db:
            self.db.execute('UPDATE v15_pauses SET cleared_at=? WHERE candidate_id=?',(_now(),key))
            self.registry._event(key,'human_resumed_v15',{'reviewer':reviewer,'reason':explanation})
        return True

    def scan(self, draws: list[dict], *, source_label: str, reference_issue: str | None = None,
             source_mask: np.ndarray | None = None, policy: Policy = Policy(),
             auto_pause: bool = False) -> dict:
        clean = validate_draws(draws)
        if not isinstance(source_label,str) or not 5 <= len(source_label) <= 200:
            raise ValueError('必须明确填写人工核验的来源标签')
        if reference_issue is not None and (not isinstance(reference_issue,str) or not re.fullmatch(r'\d{1,20}',reference_issue)):
            raise ValueError('参考期号无效')
        base=np.ones(N,dtype=bool) if source_mask is None else np.asarray(source_mask)
        if base.shape != (N,) or base.dtype != np.dtype('bool') or int(base.sum())==0:
            raise ValueError('来源域必须是非空十万位布尔掩码')
        source_hash=encode_mask(base)['sha256']
        # Read by source domain, and fail closed on truncation rather than silently
        # omitting earlier candidate rules from the competition.
        matching=self.db.execute('SELECT id FROM candidates WHERE source_mask_sha256=? ORDER BY rowid LIMIT ?',
                                 (source_hash,policy.max_competing_rules+1)).fetchall()
        if len(matching)>policy.max_competing_rules:
            raise ValueError('参评算法超过本轮预登记上限，必须人工缩小研究范围')
        candidates=[self.registry.get(row['id']) for row in matching]
        keys=[{'id':c['id'],'state':c['state'],'paused':self.paused(c['id'])} for c in candidates]
        policy_signature=digest(vars(policy))
        identifier=digest({'version':VERSION, 'draws':clean, 'source_label':source_label,
                           'reference_issue':reference_issue,'base':source_hash,
                           'policy':policy_signature,'algorithms':keys})
        record=self.db.execute('SELECT report_json,report_sha256 FROM v15_scans WHERE id=?',(identifier,)).fetchone()
        if record:
            if sha256(record['report_json'].encode()).hexdigest()!=record['report_sha256']:
                raise ValueError('已保存的竞争报告被篡改')
            report=json.loads(record['report_json']); report['replayed']=True
            if auto_pause:
                self._apply_pauses(report)
            return report
        masks={c['id']:self.registry.mask(c['id'],require_approval=False) for c in candidates}
        approved=[c for c in candidates if c['state']=='approved_experimental' and not self.paused(c['id'])]
        approved_masks={c['id']:masks[c['id']] for c in approved}
        # Union-bound alpha spending over all registered algorithms and future
        # disjoint blocks; unlike repeated cumulative p-values this does not
        # become liberal with each periodic monitoring run.
        entries=[]
        for c in sorted(candidates,key=lambda x:x['id']):
            key=c['id']; mask=masks[key]
            test=[d for d in clean if d['date']>c['cutoff_date']]
            count=len(test)
            lost=sum(bool(mask[int(r['number'])]) for r in test)
            fair_p=int(mask.sum())/N
            excess_p=float(binomtest(lost,count,fair_p,alternative='greater').pvalue) if count else None
            # marginal effect relative to *other* already-approved masks at the same cutoff and source
            peers=[v for other,v in approved_masks.items() if other!=key and
                   self.registry.get(other)['cutoff_issue']==c['cutoff_issue']]
            other_union=np.logical_or.reduce(peers) if peers else np.zeros(N,dtype=bool)
            marginal=mask & ~other_union
            marginal_hits=sum(bool(marginal[int(r['number'])]) for r in test)
            dupe=int(np.count_nonzero(mask & other_union))
            fresh=int(np.count_nonzero(marginal))
            rowid=self.db.execute('SELECT rowid FROM candidates WHERE id=?',(key,)).fetchone()[0]
            candidate_budget=policy.family_alpha/(rowid*(rowid+1))
            blocks=[]
            for j in range(count//policy.min_forward_periods):
                interval=test[j*policy.min_forward_periods:(j+1)*policy.min_forward_periods]
                hits=sum(bool(mask[int(r['number'])]) for r in interval)
                threshold=candidate_budget/((j+1)*(j+2))
                pv=float(binomtest(hits,len(interval),fair_p,alternative='greater').pvalue)
                blocks.append({'index':j+1,'first_issue':interval[0]['issue'],
                               'last_issue':interval[-1]['issue'],'removed_hits':hits,
                               'p_value':pv,'alpha_budget':threshold,'excess':pv<=threshold})
            risk=(c['state']=='approved_experimental' and not self.paused(key)
                  and any(b['excess'] for b in blocks))
            entries.append({
                'id':key, 'title':c['title'],'state':c['state'],'cutoff_issue':c['cutoff_issue'],
                'cutoff_date':c['cutoff_date'],'expired_for_reference':reference_issue is not None and reference_issue!=c['cutoff_issue'],
                'paused':self.paused(key),'removed_total':int(mask.sum()),'removed_fraction':fair_p,
                'marginal_removed':fresh,'overlap_with_other_approved':dupe,
                'marginal_missed_draws':marginal_hits, 'holdout_periods':count,
                'observed_removed_hits':lost,'fair_expected_removed':count*fair_p,
                'excess_removed_p_one_sided':excess_p,'sequential_alpha_rule_budget':candidate_budget,
                'disjoint_validation_blocks':blocks,
                'multiple_looks_policy':'alpha_i=alpha/[i(i+1)] for registered rowid i; alpha_ij=alpha_i/[j(j+1)] for disjoint full blocks j',
                'eligible_for_risk_decision':c['state']=='approved_experimental' and count>=policy.min_forward_periods,
                'failure_signal':bool(risk),
                'indicative_marginal_ratio':float(fresh/(1+marginal_hits)),
                'warning':'边际比值是启发式压缩/漏删比，不是中奖概率或预测优势。'
            })
        report={'version':VERSION,'id':identifier,'snapshot_hash':digest(clean),
                'data_source_label':source_label,'data_source_independently_verified':False,
                'reference_issue':reference_issue,'latest_issue':clean[-1]['issue'],
                'latest_date':clean[-1]['date'],'base_count':int(base.sum()),
                'policy':vars(policy),'candidate_count':len(entries),
                'approved_active_count':len(approved),'entries':entries,
                'failures':[x['id'] for x in entries if x['failure_signal']],
                'replayed':False,
                'conclusion':'此报告仅审查剔除与冗余，无法证明可预测性。自动暂停门槛使用对算法和离散时间块分配的总alpha预算；输入来源及预先冻结必须外部核验。',
                'no_auto_approval':True,'auto_pause_requested':bool(auto_pause)}
        payload=canonical(report)
        with self.db:
            self.db.execute('INSERT INTO v15_scans VALUES(?,?,?,?,?,?)',
                            (identifier,report['snapshot_hash'],policy_signature,payload,
                             sha256(payload.encode()).hexdigest(),_now()))
        if auto_pause:
            self._apply_pauses(report)
        return report

    def _apply_pauses(self, report):
        # Only a strongly adverse predeclared miss-excess signal can auto-pause.
        # Positive evidence NEVER auto-approves or automatically raises ranking weight.
        for key in report['failures']:
            previous=self.db.execute('SELECT scan_id FROM v15_pauses WHERE candidate_id=?',(key,)).fetchone()
            if previous and previous['scan_id']==report['id']:
                continue  # A human resume cannot be undone by replaying identical evidence.
            if not self.paused(key):
                self.pause(key,reason='预设样本外漏删异常，多重检验校正通过；暂停研究性使用',scan_id=report['id'])

    def propose_from_text(self, *, text: str, source_key: str, history: list[dict],
                          data_sha256: str, creator: str, source_ref: str,
                          source_mask: np.ndarray | None = None, policy: Policy=Policy()) -> dict:
        """Bounded, non-executable formula DSL -> immutable candidate masks.

        The history must contain ONLY records known before the proposed target.
        This route cannot approve, rank as predictive, or execute model code.
        """
        from autoresearch.novelty_v07 import invent_diverse
        from autoresearch.formulas import vector_eval, scalar_eval
        from .pattern_rules import PATTERNS
        clean=validate_draws(history)
        if len(clean)<20:
            raise ValueError('新规则至少需要20期历史')
        if not isinstance(data_sha256,str) or not re.fullmatch(r'[0-9a-f]{64}',data_sha256):
            raise ValueError('历史数据摘要无效')
        if digest(clean) != data_sha256:
            raise ValueError('历史数据摘要与实际输入记录不一致')
        if not isinstance(text,str) or len(text)>30000 or not text.strip():
            raise ValueError('研究文本为空或过长')
        source_mask=np.ones(N,dtype=bool) if source_mask is None else np.asarray(source_mask)
        if source_mask.shape!=(N,) or source_mask.dtype!=np.dtype('bool'):
            raise ValueError('来源域掩码非法')
        algos,novelty=invent_diverse(text,source_key,limit=policy.max_auto_proposals,
                                    search_budget=min(24,max(12,policy.max_auto_proposals*3)))
        generated=[]
        values_indices=[int(d['number']) for d in clean]
        for algo in algos:
            full=vector_eval(algo.formula)
            # Independent implementation checked on deterministic cross-section plus all actual history.
            sampled=set(range(0,N,997))|set(values_indices)
            if any(int(full[n])!=scalar_eval(algo.formula,n) for n in sampled):
                raise ValueError('DSL双实现复核失败')
            observed=full[values_indices]
            context=observed[-algo.window:]
            detector=PATTERNS[algo.pattern]
            if not detector(context):
                generated.append({'fingerprint':algo.fingerprint(),'status':'pattern_not_triggered'})
                continue
            possibilities=np.unique(full)
            continuing=[int(v) for v in possibilities if detector(np.r_[context,v])]
            if not continuing:
                generated.append({'fingerprint':algo.fingerprint(),'status':'no_continuation'})
                continue
            mask=source_mask & np.isin(full,continuing)
            frac=int(mask.sum())/max(1,int(source_mask.sum()))
            if int(mask.sum())==0 or frac>policy.max_removed_fraction:
                generated.append({'fingerprint':algo.fingerprint(),'status':'compression_guard',
                                  'removed_fraction_of_source':frac})
                continue
            r=self.registry.register(title='DSL反延续:'+algo.fingerprint(),family='auto-dsl',
                                     creator=creator,source_ref=source_ref,
                                     cutoff_issue=clean[-1]['issue'],cutoff_date=clean[-1]['date'],
                                     data_sha256=data_sha256,excluded=mask,source_mask=source_mask)
            if r['new']:
                with self.db:
                    self.db.execute('INSERT INTO v15_proposals VALUES (?,?,?,?,?)',
                                    (r['id'],canonical(algo.to_dict()),digest(source_key),digest(clean),_now()))
            generated.append({'fingerprint':algo.fingerprint(),'status':'registered_candidate',
                              'id':r['id'],'new':r['new'],'excluded':int(mask.sum())})
        return {'version':VERSION,'source':source_key,'cutoff_issue':clean[-1]['issue'],
                'novelty':{'evaluated':novelty['evaluated'],'accepted':novelty['accepted']},
                'proposals':generated,'approved':0,'external_code_executed':False,
                'warning':'候选规则未通过独立预测验证；仅注册，不自动批准/启用'}
