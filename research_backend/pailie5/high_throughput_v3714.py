"""PL5 V3.7.14: exact, reusable bitmap executor for the 100,000-ticket domain.

A Bloom filter is not used: a dense exact bitmap costs just 12,500 bytes per
full-domain rule, offers no false positives, and permits efficient AND/OR/NOT.

Only context-stable, explicitly invalidated rules may be cached. Deferred
predicates run over survivors only. This is a performance layer, never a
statement about predictive advantage or lottery coverage.
"""
from __future__ import annotations

from dataclasses import dataclass
import sys
from typing import Callable, Iterable

import numpy as np

from .basic_filters import BasicConstraint
from .pattern_rules import EXTRA_INDICATORS, indicator_table, indicator_values

DOMAIN = 100_000
BYTES_PER_MASK = (DOMAIN + 7) // 8
_ALL = (1 << DOMAIN) - 1


def bitmap_from_mask(mask: np.ndarray) -> int:
    """Pack 100,000 booleans in increasing ticket-index bit order."""
    arr = np.asarray(mask)
    if arr.shape != (DOMAIN,) or arr.dtype != np.bool_:
        raise ValueError('bitmap mask requires 100000 boolean values')
    return int.from_bytes(np.packbits(arr, bitorder='little').tobytes(), 'little')


def mask_from_bitmap(bits: int) -> np.ndarray:
    """Unpack an exact 100,000-ticket bitmap, preserving 00000 as index 0."""
    if type(bits) is not int or bits < 0 or bits > _ALL:
        raise ValueError('bitmap must be a nonnegative integer within the PL5 domain')
    data = bits.to_bytes(BYTES_PER_MASK, 'little')
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8), bitorder='little')[:DOMAIN].astype(bool)


@dataclass
class _Rule:
    vector_factory: Callable[[], np.ndarray] | None = None
    deferred: Callable[[int], bool] | None = None
    bits: int | None = None
    dependencies: tuple[str, ...] = ()
    cost_hint: float = 1.0


class ExactFilterEngine:
    """Boolean rule executor with explicit cache lifecycle and no false drops.

    All input predicates are trusted Python code from this application, not
    untrusted user strings. External changes to registered vector functions
    must be announced via :meth:`invalidate` with a matching dependency name.
    """

    def __init__(self) -> None:
        self._rules: dict[str, _Rule] = {}
        self._compilations = 0
        self._deferred_evaluations = 0

    def _install(self, name: str, rule: _Rule, *, replace: bool) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError('rule name must be a nonempty string')
        if name in self._rules and not replace:
            raise ValueError('rule already registered: ' + name)
        self._rules[name] = rule

    def add_mask(self, name: str, mask: np.ndarray, *, replace: bool = False) -> None:
        """Freeze an external boolean mask immediately; caller mutations are safe."""
        self._install(name, _Rule(bits=bitmap_from_mask(mask)), replace=replace)

    def add_vector(self, name: str, factory: Callable[[], np.ndarray], *,
                   dependencies: Iterable[str] = (), replace: bool = False) -> None:
        """Lazy cache of a deterministic full-universe mask; invalidate on input change."""
        if not callable(factory):
            raise ValueError('vector rule requires a callable')
        deps = tuple(dependencies)
        if any(not isinstance(d, str) or not d for d in deps):
            raise ValueError('dependency keys must be nonempty strings')
        self._install(name, _Rule(vector_factory=factory, dependencies=deps), replace=replace)

    def add_basic(self, name: str, rule: BasicConstraint, *, replace: bool = False) -> None:
        """Index an existing PL5 BasicConstraint without changing its semantics."""
        if not isinstance(rule, BasicConstraint):
            raise ValueError('requires BasicConstraint')
        if rule.indicator not in indicator_table() and rule.indicator not in EXTRA_INDICATORS:
            raise ValueError('unknown indicator: ' + str(rule.indicator))

        def calculate() -> np.ndarray:
            values = indicator_values(rule.indicator, 'raw')
            result = np.ones(DOMAIN, dtype=bool)
            if rule.minimum is not None:
                result &= values >= rule.minimum
            if rule.maximum is not None:
                result &= values <= rule.maximum
            if rule.allowed is not None:
                result &= np.isin(values, rule.allowed)
            if rule.denied is not None:
                result &= ~np.isin(values, rule.denied)
            return result

        # Legacy indicator registrations can be mutable, so callers must
        # invalidate 'indicator:<name>' after updating an external array.
        self.add_vector(name, calculate,
                        dependencies=(f'indicator:{rule.indicator}',), replace=replace)

    def add_deferred(self, name: str, predicate: Callable[[int], bool], *,
                     cost_hint: float = 1.0, replace: bool = False) -> None:
        """Register a context-sensitive predicate, evaluated exactly after bitmaps."""
        if not callable(predicate) or not (0 < cost_hint < float('inf')):
            raise ValueError('deferred predicate must be callable with positive finite cost')
        self._install(name, _Rule(deferred=predicate, cost_hint=float(cost_hint)),replace=replace)

    def remove(self, name: str) -> None:
        del self._rules[name]

    def invalidate(self, dependency: str) -> int:
        """Drop cached masks that depend on the changed external data source."""
        if not isinstance(dependency, str) or not dependency:
            raise ValueError('dependency key must be a nonempty string')
        count = 0
        for rule in self._rules.values():
            if rule.bits is not None and rule.vector_factory is not None and dependency in rule.dependencies:
                rule.bits = None
                count += 1
        return count

    def _compile(self, name: str) -> int:
        r = self._rules[name]
        if r.deferred is not None:
            raise ValueError('deferred rules cannot be compiled as membership bitmaps: ' + name)
        if r.bits is None:
            if r.vector_factory is None:
                raise AssertionError('missing rule compiler')
            r.bits = bitmap_from_mask(r.vector_factory())
            self._compilations += 1
        return r.bits

    def evaluate(self, *, all_of: Iterable[str] = (),
                 any_of: Iterable[str] | None = None,
                 none_of: Iterable[str] = ()) -> np.ndarray:
        """Return sorted integer tickets meeting (AND all) AND (OR any) AND NOT any.

        `any_of=None` applies no OR restriction. `any_of=[]` requests the
        empty union. Deferred predicates are permitted ONLY in `all_of`.
        """
        required = tuple(dict.fromkeys(all_of))
        optional = None if any_of is None else tuple(dict.fromkeys(any_of))
        forbidden = tuple(dict.fromkeys(none_of))
        for n in required + (optional or ()) + forbidden:
            if n not in self._rules:
                raise KeyError(n)
        for n in (optional or ()) + forbidden:
            if self._rules[n].deferred is not None:
                raise ValueError('deferred rule only supported in all_of: ' + n)

        masks = [self._compile(n) for n in required if self._rules[n].deferred is None]
        masks.sort(key=int.bit_count)  # early-empty short circuit
        selected = _ALL
        for bits in masks:
            selected &= bits
            if selected == 0:
                break
        if selected and optional is not None:
            allowed = 0
            for n in optional:
                allowed |= self._compile(n)
            selected &= allowed
        if selected and forbidden:
            denied = 0
            for n in forbidden:
                denied |= self._compile(n)
            selected &= ~denied
        if selected == 0:
            return np.empty(0, dtype=np.int32)
        numbers = np.flatnonzero(mask_from_bitmap(selected)).astype(np.int32)
        late = [self._rules[n] for n in required if self._rules[n].deferred is not None]
        late.sort(key=lambda r:r.cost_hint)
        for r in late:
            before = len(numbers)
            numbers = np.fromiter((int(n) for n in numbers if r.deferred(int(n))), dtype=np.int32)
            self._deferred_evaluations += before
            if numbers.size == 0:
                break
        return numbers

    def formatted(self, **kwargs) -> list[str]:
        """Format selected integer tickets as five characters (00000 etc)."""
        return [f'{int(n):05d}' for n in self.evaluate(**kwargs)]

    def stats(self) -> dict:
        stored = [r.bits for r in self._rules.values() if r.bits is not None]
        return {'registered_rules':len(self._rules),
                'cached_rules':len(stored),
                'cached_bytes':len(stored)*BYTES_PER_MASK,
                'cached_python_bytes':sum(sys.getsizeof(bits) for bits in stored),
                'compilations':self._compilations,
                'deferred_evaluations':self._deferred_evaluations}
