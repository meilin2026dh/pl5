"""V3.7.12: fixed four-window family-wise controlled *post-label* shift monitor.

Caller remains responsible for chronological provenance and model assumptions.
No sequential optional peeking, no self-refit, no future-drift prediction.
"""
from __future__ import annotations

from .cross_task_v3711 import FrozenBudgetedPrimitive, detect_labeled_shift
from .structure_search_v372 import CellDataset


def monitor_preplanned_windows(frozen:FrozenBudgetedPrimitive,
                               windows:tuple[CellDataset,...],*,
                               expected_error_rate:float=0.02,
                               alpha_total:float=0.01)->dict:
    if not isinstance(frozen,FrozenBudgetedPrimitive) or frozen.status!='provisional_identified':
        raise ValueError('requires a provisional identified frozen fit')
    if not isinstance(windows,tuple) or len(windows)!=4:
        raise ValueError('exactly four preplanned windows required')
    if any(not isinstance(w,CellDataset) or len(w.rows)!=20 for w in windows):
        raise ValueError('every window requires exactly 20 labeled observations')
    if len({w.fingerprint for w in windows})!=4:
        raise ValueError('duplicate windows are not independent validation')
    if type(expected_error_rate) not in (float,int) or not 0<expected_error_rate<1:
        raise ValueError('noise rate must lie strictly between 0 and 1')
    if type(alpha_total) not in (float,int) or not 0<alpha_total<1:
        raise ValueError('alpha_total must lie strictly between 0 and 1')
    local_alpha=float(alpha_total)/4.0
    reports=[detect_labeled_shift(frozen,w,expected_error_rate=expected_error_rate,
                                  alpha=local_alpha) for w in windows]
    flagged=[i+1 for i,r in enumerate(reports) if r['status']=='shift_suspected']
    return {'schema':'pl5-v3712-four-fixed-window-1',
            'status':'shift_suspected' if flagged else 'no_shift_signal',
            'windows_count':4,'window_errors':[r['observed_errors'] for r in reports],
            'p_values':[r['p_value'] for r in reports],
            'per_window_alpha':local_alpha,'family_alpha_total':float(alpha_total),
            'first_flagged_window':flagged[0] if flagged else None,
            'multiple_looks_correction':'Bonferroni',
            'observation_fingerprints':[w.fingerprint for w in windows],
            'frozen_operator_id':frozen.identity,
            'fit_was_refreshed':False,'production_enabled':False,
            'predictive_advantage':'NOT_ESTABLISHED',
            'assumptions':'four a-priori nonadaptively scheduled windows; iid error model; caller attests chronology'}
