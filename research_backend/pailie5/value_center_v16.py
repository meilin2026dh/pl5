"""PL5 V1.6 read-only, prequential rule health and research-weight proposals.

No probability advantage is inferred from rare patterns or compression. The
weights are *research annotations*, never automatically used for selections.
"""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from math import log, sqrt
from pathlib import Path
import json
import sqlite3

import numpy as np

from .forward_sculpt_v152 import SculptLedger, canon, digest
from .integration_bridge import decode_mask, N

VERSION = 'pl5-value-center-v16'


def _neutral(state: str, **extra):
    return {'schema': VERSION, 'state': state, 'integrity_verified': None,
            'used_settled_prefix': 0, 'knives': [], 'automatic_activation': False,
            'real_win_probabilities': False, 'research_only': True, **extra}



def propose_research_weight(*, periods: int, observed: int, expected: float,
                            novelty: float, minimum_periods: int,
                            family_size: int, alpha: float) -> dict:
    """Fixed-horizon conservative, non-operational suggestion; NOT a p-value.

    Repeated monitoring and model selection invalidate treating this as a
    one-time confirmatory error guarantee. No direct activation is permitted.
    """
    if periods <= 0 or family_size <= 0 or not 0 <= novelty <= 1:
        raise ValueError('异常规则审计参数')
    margin = sqrt(periods * log(2 * family_size / alpha) / 2)
    delta = expected - observed
    direction = ('fewer_wrong_cuts' if periods >= minimum_periods and delta > margin else
                 'more_wrong_cuts' if periods >= minimum_periods and delta < -margin else
                 'insufficient_evidence')
    weight = 1.0
    if direction == 'fewer_wrong_cuts':
        weight = round(1 + min(.2, (delta-margin)/max(1, expected)) * novelty, 6)
    elif direction == 'more_wrong_cuts':
        weight = round(1 - min(.2, (-delta-margin)/max(1, expected)), 6)
    return {'category':direction,'weight':weight,'margin':round(margin,6)}


def analyze(path: str | Path | None, *, minimum_periods: int = 100,
            alpha: float = 0.01, max_periods: int = 3000) -> dict:
    """Evaluate only the contiguous settled prefix from an immutable V1.5.2 ledger.

    Each period's expectation equals the excluded mask count / 100000, even
    when the source domain itself is smaller. Thus a rule's observed exclusion
    is compared with the *same* originally registered domain and knife mask.
    """
    if not isinstance(minimum_periods, int) or not 30 <= minimum_periods <= 3000:
        raise ValueError('minimum_periods必须为30—3000')
    if not 0 < alpha <= .05 or not isinstance(max_periods, int) or max_periods < 30:
        raise ValueError('统计参数超出范围')
    if not path:
        return _neutral('not_configured')
    p = Path(path)
    if not p.exists():
        return _neutral('file_missing')
    try:
        db = sqlite3.connect(p.resolve().as_uri() + '?mode=ro', uri=True, timeout=3)
    except sqlite3.Error:
        return _neutral('read_error')
    db.row_factory = sqlite3.Row
    try:
        ok = SculptLedger.verify(type('ReadOnlyLedger', (), {'db': db})())
        if not ok['ok']:
            return _neutral('ledger_invalid', integrity_verified=False,
                            reasons=ok['errors'][:10])
        rows = db.execute('''SELECT s.target_issue,s.receipt_json,z.result_json
            FROM seals s LEFT JOIN settlements z ON s.target_issue=z.target_issue
            ORDER BY CAST(s.target_issue AS INTEGER)''').fetchall()
        prefix = []
        for row in rows:
            if row['result_json'] is None:
                break
            prefix.append((json.loads(row['receipt_json']), json.loads(row['result_json'])))
        if len(prefix) > max_periods:
            return _neutral('period_limit', integrity_verified=True,
                            used_settled_prefix=0, total_prefix=len(prefix),
                            message='前向记录超过本轮容量限制，拒绝截断后择优评估')
        counters = defaultdict(lambda: {'periods':0, 'observed':0, 'expected':0.0,
                                        'first_cut':0, 'unique_actual':0,
                                        'unique_expected':0.0, 'exclusion_fractions':[],
                                        'last_mask':None, 'last_issue':None})
        for receipt, outcome in prefix:
            if outcome['target_issue'] != receipt['target_issue'] or outcome['receipt_sha256'] != digest(receipt):
                raise ValueError('结算与封存不一致')
            number = outcome.get('number')
            if not isinstance(number,str) or len(number)!=5 or not number.isdigit():
                raise ValueError('结算号码无效')
            target = int(number)
            mask_data = receipt['stage_masks']
            keys = [entry['key'] for entry in mask_data]
            if len(set(keys)) != len(keys) or not keys or keys[0] != '__source__':
                raise ValueError('刀具标识不一致')
            masks = {e['key']:decode_mask(e['excluded_mask']) for e in mask_data}
            for key in keys[1:]:
                if np.any(masks[key] & masks['__source__']):
                    raise ValueError('刀具越过来源域')
            # Unique area is calculated in the same period, with other rules
            # treated symmetrically. It is not an order-dependent first cut.
            all_masks = [masks[key] for key in keys[1:]]
            stack = np.sum(np.stack(all_masks).astype(np.uint8), axis=0,
                           dtype=np.int16) if all_masks else None
            actual_decisions = {d['key']:d for d in outcome['knife_decisions']}
            if set(actual_decisions)!=set(keys):
                raise ValueError('开奖结果规则集合不一致')
            for key in keys[1:]:
                mask = masks[key]
                cut = bool(mask[target])
                if cut != bool(actual_decisions[key]['would_cut']):
                    raise ValueError('开奖后逐刀判断与封存掩码冲突')
                state = counters[key]
                state['periods'] += 1
                state['observed'] += int(cut)
                state['expected'] += int(mask.sum()) / N
                state['first_cut'] += int(actual_decisions[key]['first_cut'])
                unique_mask = mask & (stack == 1)
                state['unique_actual'] += int(unique_mask[target])
                state['unique_expected'] += int(unique_mask.sum())/N
                state['exclusion_fractions'].append(int(mask.sum())/N)
                state['last_mask'] = mask
                state['last_issue'] = receipt['target_issue']
        # A union bound over currently studied knife names is used solely as
        # a fixed-horizon descriptive deviation bound. It cannot be repeatedly
        # inspected and used to claim a sequential alpha guarantee.
        number_of_knives = max(1, len(counters))
        latest_settled = prefix[-1][0]['target_issue'] if prefix else None
        report=[]
        for key in sorted(counters):
            s=counters[key]
            n=s['periods']
            latest=s['last_mask']
            last_count=int(latest.sum())
            others=[v['last_mask'] for other,v in counters.items()
                    if other!=key and v['last_issue']==s['last_issue']]
            union=np.logical_or.reduce(others) if others else np.zeros(N,dtype=bool)
            overlap=int((latest & union).sum())
            novelty=(last_count-overlap)/last_count if last_count else 0.0
            proposal = propose_research_weight(periods=n, observed=s['observed'],
                expected=s['expected'], novelty=novelty,
                minimum_periods=minimum_periods, family_size=number_of_knives, alpha=alpha)
            report.append({
                'id':key,'periods':n,'last_evaluated_issue':s['last_issue'],
                'observed_wrong_cuts':s['observed'],
                'expected_fair_wrong_cuts':round(s['expected'],6),
                'first_cut_actual':s['first_cut'],
                'unique_wrong_cuts':s['unique_actual'],
                'expected_fair_unique_wrong_cuts':round(s['unique_expected'],6),
                'latest_removed':last_count,'latest_overlap':overlap,
                'latest_geometric_novelty':round(novelty,6),
                'average_removed_fraction':round(sum(s['exclusion_fractions'])/n,8),
                'deviation_bound_count':proposal['margin'],
                'evidence_category':proposal['category'],
                'proposed_research_weight':proposal['weight'],
                'ready_for_manual_review':proposal['category']!='insufficient_evidence',
                'approved_for_prediction':False,
                'research_priority':(
                    'review_excess_false_cuts' if proposal['category']=='more_wrong_cuts' else
                    'replicate_on_new_data' if proposal['category']=='fewer_wrong_cuts' else
                    'deduplicate_low_novelty' if novelty<0.2 and n>=minimum_periods else
                    'collect_more_prospective_data'),
            })
        payload={
            'schema':VERSION,'state':'ready','integrity_verified':True,
            'used_settled_prefix':len(prefix),
            'total_sealed':len(rows), 'latest_settled_issue':latest_settled,
            'pending_after_prefix':len(rows)-len(prefix),
            'minimum_periods':minimum_periods, 'alpha_for_diagnostic_bound':alpha,
            'knife_count':len(report), 'knives':report,
            'research_queue':[{
                 'id':x['id'],'priority':x['research_priority'],
                 'current_weight':x['proposed_research_weight']}
                 for x in sorted(report, key=lambda v:(
                     {'review_excess_false_cuts':0,'replicate_on_new_data':1,
                      'deduplicate_low_novelty':2,'collect_more_prospective_data':3}[v['research_priority']],
                     v['id']))[:15]],
            'automatic_activation':False, 'real_win_probabilities':False,
            'research_only':True, 'weights_apply_to_past_records':False,
            'safe_next_steps': '供下一期的人工研究评审，不自动写入雕塑引擎',
            'limitations':'固定截点的Hoeffding并合偏差界仅作诊断；反复查看、选刀、改规则或重复测试不具有相同错误率保证。历史样本小，常见中性权重1.0；公平开奖下保留K注命中概率仍为K/100000。'
        }
        payload['report_sha256']=digest(payload)
        return payload
    except (sqlite3.Error,ValueError,TypeError,KeyError,OverflowError,MemoryError) as exc:
        return _neutral('read_error', integrity_verified=False, message=str(exc)[:200])
    finally:
        db.close()
