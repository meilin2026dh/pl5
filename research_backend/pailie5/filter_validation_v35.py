"""V3.5 fixed-budget exclusion evaluation. Research only."""
from dataclasses import dataclass
from .number_validation import is_five_digit_draw

@dataclass(frozen=True)
class FilterEvidence:
    total: int
    removed_count: int
    removed_winners: int
    removal_rate: float
    miss_rate: float
    random_baseline: float

def evaluate_filter(removed_sets, winners, universe_size=100000):
    if not removed_sets or len(removed_sets)!=len(winners) or universe_size<1:
        raise ValueError('invalid experiment')
    if any(not is_five_digit_draw(n) for n in winners):
        raise ValueError('invalid winner')
    if any(len(s)!=len(removed_sets[0]) or len(s)>universe_size or
           any(not is_five_digit_draw(n) for n in s)
           for s in removed_sets):
        raise ValueError('invalid fixed-size exclusion')
    count=sum(w in s for w,s in zip(winners,removed_sets))
    baseline=len(removed_sets[0])/universe_size
    return FilterEvidence(len(winners),len(removed_sets[0]),count,baseline,count/len(winners),baseline)
