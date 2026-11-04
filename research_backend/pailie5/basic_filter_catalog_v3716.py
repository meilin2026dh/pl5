"""V3.7.16: opt-in reusable exact-bitset cache for existing BasicConstraint flows.

Only static BasicConstraint masks are cached, never history-sensitive
patterns. Catalog construction freezes a rule *definition*; the first query
compiles its membership bitset. Mutable externally registered indicators
require explicit refresh on updates. Legacy default paths are unchanged.
"""
from __future__ import annotations

from collections.abc import Sequence

from .basic_filters import BasicConstraint
from .high_throughput_v3714 import ExactFilterEngine


class BasicFilterCatalog:
    """One session for repeated basic rule combinations across PL5 workflows."""

    def __init__(self, rules: Sequence[BasicConstraint]):
        self.rules = tuple(rules)
        if any(not isinstance(rule, BasicConstraint) for rule in self.rules):
            raise ValueError('catalog requires BasicConstraint rules')
        if len(set(self.rules)) != len(self.rules):
            raise ValueError('duplicate rule definitions are not allowed')
        self._names = {rule: f'basic_{i}' for i, rule in enumerate(self.rules)}
        self._engine = ExactFilterEngine()
        for rule, name in self._names.items():
            self._engine.add_basic(name, rule)

    def select(self, constraints: Sequence[BasicConstraint]):
        """Return unchanged sorted integer ticket IDs; reject unregistered rules."""
        names = []
        for rule in constraints:
            try:
                names.append(self._names[rule])
            except (KeyError, TypeError) as e:
                raise ValueError('BasicConstraint not registered in catalog') from e
        return self._engine.evaluate(all_of=names)

    def formatted(self, constraints: Sequence[BasicConstraint]) -> list[str]:
        """Preserve zero-padding of 00000..99999."""
        return [f'{int(n):05d}' for n in self.select(constraints)]

    def refresh(self, dependency: str) -> int:
        """Invalidate masks affected by external indicator mutations."""
        return self._engine.invalidate(dependency)

    def stats(self) -> dict:
        return self._engine.stats()
