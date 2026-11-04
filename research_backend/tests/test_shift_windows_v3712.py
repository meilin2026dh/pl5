"""V3.7.12: preplanned fixed multiple-look monitoring; no future foresight."""
import pytest
from pailie5.structure_search_v372 import CellDataset
from pailie5.cross_task_v3711 import FrozenBudgetedPrimitive
from pailie5.shift_windows_v3712 import monitor_preplanned_windows


def _frozen():
    # Immutable existing frozen model with known zero prediction. No fitting in monitor.
    return FrozenBudgetedPrimitive('provisional_identified',tuple([0]*100),
        ('id','mul','id'),tuple(), 'a'*64,None,1,1,'test fixture')


def _windows(errors=(0,0,0,0)):
    windows=[]
    for w,n in enumerate(errors):
        rows=tuple((i//10,i%10,1 if i<n else 0) for i in range(w*20,w*20+20))
        # labels' noisy first n within each distinct 20-cell window
        rows=tuple((a,b,1 if j<n else 0) for j,(a,b,_) in enumerate(rows))
        windows.append(CellDataset(rows))
    return tuple(windows)


def test_clean_windows_do_not_trigger_false_shift_alarm():
    result=monitor_preplanned_windows(_frozen(),_windows(),alpha_total=0.01)
    assert result['status']=='no_shift_signal'
    assert result['per_window_alpha']==pytest.approx(0.0025)
    assert result['windows_count']==4
    assert len(result['p_values'])==4
    assert result['fit_was_refreshed'] is False
    assert result['production_enabled'] is False


def test_labeled_shift_after_second_window_is_detected_without_refit():
    out=monitor_preplanned_windows(_frozen(),_windows((0,0,14,14)))
    assert out['status']=='shift_suspected'
    assert out['first_flagged_window']==3
    assert out['window_errors']==[0,0,14,14]
    assert out['multiple_looks_correction']=='Bonferroni'


def test_prespecified_schedule_validation_and_no_look_extension():
    frozen=_frozen()
    with pytest.raises(ValueError,match='exactly four'):
        monitor_preplanned_windows(frozen,_windows()[:3])
    with pytest.raises(ValueError,match='duplicate'):
        monitor_preplanned_windows(frozen,(_windows()[0],)*4)
    with pytest.raises(ValueError,match='alpha_total'):
        monitor_preplanned_windows(frozen,_windows(),alpha_total=0.0)
    with pytest.raises(ValueError,match='noise rate'):
        monitor_preplanned_windows(frozen,_windows(),expected_error_rate=1)
    with pytest.raises(ValueError,match='20'):
        monitor_preplanned_windows(frozen,(CellDataset(_windows()[0].rows[:19]),)+_windows()[1:])


def test_abstaining_fit_cannot_be_monitored():
    from dataclasses import replace
    with pytest.raises(ValueError,match='provisional'):
        monitor_preplanned_windows(replace(_frozen(),status='no_fit',completion=None),_windows())
