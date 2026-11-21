"""V3.7.14 strict functional regressions: failure-first tests."""
import numpy as np
import pytest
from pailie5.basic_filters import BasicConstraint, apply_basic_filters
from pailie5.high_throughput_v3714 import (
    DOMAIN, ExactFilterEngine, bitmap_from_mask, mask_from_bitmap,
)


def test_bit_roundtrip_endpoints_and_leading_zeros():
    flags = np.zeros(DOMAIN, dtype=bool)
    flags[[0, 1, 9, 100, 99999]] = True
    bits = bitmap_from_mask(flags)
    assert mask_from_bitmap(bits).dtype == bool
    assert np.array_equal(mask_from_bitmap(bits), flags)
    assert bitmap_from_mask(np.zeros(DOMAIN,dtype=bool)) == 0
    assert bitmap_from_mask(np.ones(DOMAIN,dtype=bool)).bit_count() == DOMAIN


def test_basic_and_or_not_match_vectorized_oracle():
    engine = ExactFilterEngine()
    rules = {
        'a': BasicConstraint('sum', minimum=15, maximum=30),
        'b': BasicConstraint('span', minimum=3, maximum=7),
        'c': BasicConstraint('odd_count', allowed=(1, 2, 3)),
    }
    for n,r in rules.items(): engine.add_basic(n,r)
    assert np.array_equal(engine.evaluate(all_of=['a','b','c']),apply_basic_filters(list(rules.values())))
    ab = set(map(int,apply_basic_filters([rules['a']]))) | set(map(int,apply_basic_filters([rules['b']])))
    not_c = set(range(DOMAIN)) - set(map(int,apply_basic_filters([rules['c']])))
    assert set(map(int,engine.evaluate(any_of=['a','b'], none_of=['c']))) == ab & not_c
    assert len(engine.evaluate(any_of=[])) == 0
    assert len(engine.evaluate()) == DOMAIN
    assert engine.formatted(all_of=['a'])[:1] == [f'{int(engine.evaluate(all_of=["a"])[0]):05d}']


def test_mutating_input_mask_does_not_corrupt_cached_rule():
    mask = np.zeros(DOMAIN,dtype=bool)
    mask[0]=True
    engine=ExactFilterEngine()
    engine.add_mask('only0',mask)
    mask[0]=False
    mask[1]=True
    assert engine.evaluate(all_of=['only0']).tolist() == [0]


def test_replacement_and_dependency_invalidation():
    engine = ExactFilterEngine()
    first = np.zeros(DOMAIN,dtype=bool);first[0]=True
    second = np.zeros(DOMAIN,dtype=bool);second[42]=True
    state = [first]
    engine.add_vector('historical',lambda:state[0],dependencies=('latest-draw',))
    assert engine.evaluate(all_of=['historical']).tolist()==[0]
    state[0]=second
    assert engine.evaluate(all_of=['historical']).tolist()==[0] # immutable until explicit invalidate
    assert engine.invalidate('latest-draw')==1
    assert engine.evaluate(all_of=['historical']).tolist()==[42]
    engine.add_mask('historical',first,replace=True)
    assert engine.evaluate(all_of=['historical']).tolist()==[0]
    engine.remove('historical')
    with pytest.raises(KeyError):engine.evaluate(all_of=['historical'])


def test_deferred_rules_run_only_on_static_survivors():
    engine=ExactFilterEngine()
    mask=np.zeros(DOMAIN,dtype=bool);mask[0:20]=True
    engine.add_mask('pre',mask)
    seen=[]
    engine.add_deferred('expensive',lambda n: seen.append(n) or n%2==0,cost_hint=10)
    assert engine.evaluate(all_of=['pre','expensive']).tolist()==list(range(0,20,2))
    assert seen==list(range(20))
    with pytest.raises(ValueError):engine.evaluate(any_of=['expensive'])
    with pytest.raises(ValueError):engine.evaluate(none_of=['expensive'])


def test_invalid_inputs_and_rule_collisions():
    engine=ExactFilterEngine()
    with pytest.raises(ValueError):bitmap_from_mask(np.zeros(100,dtype=bool))
    with pytest.raises(ValueError):mask_from_bitmap(-1)
    with pytest.raises(ValueError):mask_from_bitmap(1<<DOMAIN)
    with pytest.raises(ValueError):engine.add_basic('invalid',BasicConstraint('no_such_indicator'))
    engine.add_basic('one',BasicConstraint('digit_1',minimum=1))
    with pytest.raises(ValueError):engine.add_basic('one',BasicConstraint('digit_1',minimum=2))
    with pytest.raises(KeyError):engine.evaluate(all_of=['missing'])


def test_cache_statistics_and_intersection_short_circuit():
    engine=ExactFilterEngine()
    engine.add_mask('empty',np.zeros(DOMAIN,dtype=bool))
    engine.add_deferred('expensive',lambda _: (_ for _ in ()).throw(AssertionError('should not run')))
    assert engine.evaluate(all_of=['empty','expensive']).size==0
    stats=engine.stats()
    assert stats['cached_rules']==1
    assert stats['cached_bytes']>=12500
    assert stats['deferred_evaluations']==0
