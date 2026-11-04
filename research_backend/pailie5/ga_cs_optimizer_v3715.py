"""V3.7.15 GA/CS constrained search on exact PL5 rule bitmaps.

A cost-matched *engineering* optimizer, not a lottery prediction model.
The only input used by fitness is the frozen candidate mask inventory,
not any future draw labels. There is no lookahead, retrospective tuning,
or guaranteed predictive advantage.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

import numpy as np


@dataclass(frozen=True)
class SearchProblem:
    """Exact static condition masks; immutable snapshot for a single trial.

    For the PL5 universe use universe_size=100000, with each bit denoting
    the corresponding five-digit ticket index. `hard_mask` applies to EVERY
    genome; it must never be treated as an optional optimization decision.
    """
    masks: tuple[int, ...]
    rule_names: tuple[str, ...]
    universe_size: int
    target: int
    min_survivors: int
    max_survivors: int
    min_active: int = 0
    hard_mask: int | None = None
    complexity_weight: float = 0.014

    def __post_init__(self) -> None:
        masks = tuple(self.masks)
        names = tuple(self.rule_names)
        object.__setattr__(self, 'masks', masks)
        object.__setattr__(self, 'rule_names', names)
        if not isinstance(self.universe_size, int) or not 1 <= self.universe_size <= 1_000_000:
            raise ValueError('universe_size must be in 1..1000000')
        if not (0 < len(masks) <= 60 and len(masks) == len(names)):
            raise ValueError('masks must correspond to 1..60 named rules')
        if not all(isinstance(n, str) and n and names.count(n) == 1 for n in names):
            raise ValueError('rule_names must be unique, nonempty strings')
        full = (1 << self.universe_size) - 1
        if any(type(b) is not int or b < 0 or b > full for b in masks):
            raise ValueError('rule masks must fit in the declared universe')
        if not (isinstance(self.min_survivors, int) and isinstance(self.max_survivors, int)
                and isinstance(self.target, int) and 1 <= self.min_survivors <= self.target
                <= self.max_survivors <= self.universe_size):
            raise ValueError('require 1 <= min_survivors <= target <= max_survivors <= universe_size')
        if not isinstance(self.min_active, int) or not 0 <= self.min_active <= len(masks):
            raise ValueError('min_active must be a feasible rule count')
        if self.hard_mask is not None and (type(self.hard_mask) is not int
                                           or self.hard_mask < 0 or self.hard_mask > full):
            raise ValueError('hard_mask must be a valid nonnegative mask')
        if not math.isfinite(self.complexity_weight) or self.complexity_weight < 0:
            raise ValueError('complexity_weight must be nonnegative and finite')


@dataclass(frozen=True)
class Candidate:
    genome: int
    survivors: int
    rule_count: int
    feasible: bool
    fitness: float


@dataclass(frozen=True)
class SearchResult:
    method: str
    seed: int
    evaluations: int
    best: Candidate
    best_trace: tuple[float, ...]
    stage_evaluations: dict[str, int]
    selected_rules: tuple[str, ...]


def evaluate_genome(problem: SearchProblem, genome: int) -> Candidate:
    """Exact conjunction and fitness, no external or future outcome data."""
    if type(genome) is not int or genome < 0 or genome >= (1 << len(problem.masks)):
        raise ValueError('genome must encode only known optional rule positions')
    bits = (1 << problem.universe_size) - 1 if problem.hard_mask is None else problem.hard_mask
    active = genome.bit_count()
    for i, rule in enumerate(problem.masks):
        if genome & (1 << i):
            bits &= rule
            if bits == 0:
                break
    n = bits.bit_count()
    feasible = (problem.min_active <= active and
                problem.min_survivors <= n <= problem.max_survivors)
    deviation = abs(math.log((n + 1) / (problem.target + 1)))
    regularizer = problem.complexity_weight * active
    if feasible:
        fit = -deviation - regularizer
    else:
        boundary = (problem.min_survivors if n < problem.min_survivors
                    else problem.max_survivors if n > problem.max_survivors else problem.target)
        distance = abs(math.log((n + 1) / (boundary + 1)))
        fit = -10.0 - distance - regularizer - max(0, problem.min_active - active)
    return Candidate(genome, n, active, feasible, round(fit, 12))


def _best_key(c: Candidate) -> tuple[float, int, int]:
    # Feasibility dominates every infeasible candidate. Deterministic ties.
    return (float(c.feasible), c.fitness, -c.genome)


def _repair(genome: int, k: int, minimum: int, rng: np.random.Generator) -> int:
    if genome.bit_count() < minimum:
        spare = [i for i in range(k) if not genome & (1 << i)]
        for i in rng.choice(spare, size=minimum - genome.bit_count(), replace=False):
            genome |= 1 << int(i)
    return genome


def _random(k: int, minimum: int, rng: np.random.Generator) -> int:
    return _repair(int(rng.integers(0, 1 << k)), k, minimum, rng)


def _levy_flight_steps(k: int, rng: np.random.Generator) -> int:
    """Mantegna symmetric Levy-flight step, beta=1.5, clipped to k bits."""
    beta = 1.5
    sigma = (math.gamma(1 + beta) * math.sin(math.pi * beta / 2)
             / (math.gamma((1 + beta) / 2) * beta * 2 ** ((beta - 1) / 2))) ** (1 / beta)
    numerator = float(rng.normal(0, sigma))
    denominator = max(abs(float(rng.normal())), 1e-12) ** (1 / beta)
    return min(k, 1 + int(abs(numerator / denominator)))


def _mutate(parent: int, k: int, flips: int, minimum: int,
            rng: np.random.Generator) -> int:
    gene = parent
    indices = rng.choice(k, size=min(k, flips), replace=False)
    for i in indices:
        gene ^= 1 << int(i)
    return _repair(gene, k, minimum, rng)


def optimize(problem: SearchProblem, *, method: Literal['random','ga','cs','ga_cs','anneal','greedy'],
             evaluations: int = 240, seed: int = 3715, switch_ratio: float = 0.3,
             population_size: int = 12) -> SearchResult:
    """Evaluate *exactly* the same number of candidate genomes per method.

    Calls to the objective, including repeats and initial nests, ALL count
    against the shared limit. No post-search refitting on held-out labels.
    """
    allowed = ('random','ga','cs','ga_cs','anneal','greedy')
    if method not in allowed:
        raise ValueError('unknown search method')
    if type(evaluations) is not int or evaluations < 1:
        raise ValueError('evaluations must be a positive integer')
    if not 0 < switch_ratio < 1 or not math.isfinite(switch_ratio):
        raise ValueError('switch_ratio must be strictly between 0 and 1')
    if type(population_size) is not int or population_size < 2:
        raise ValueError('population_size must be >=2')
    if type(seed) is not int or seed < 0:
        raise ValueError('seed must be a nonnegative integer')
    k = len(problem.masks)
    rng = np.random.default_rng(seed)
    pool: list[Candidate] = []
    best: Candidate | None = None
    trace: list[float] = []
    stages: dict[str, int] = {}
    current: Candidate | None = None

    def score(genome: int, stage: str) -> Candidate:
        nonlocal best
        candidate = evaluate_genome(problem, genome)
        stages[stage] = stages.get(stage, 0) + 1
        if best is None or _best_key(candidate) > _best_key(best):
            best = candidate
        # Trace records the lexicographic objective including feasibility.
        trace.append((10.0 if best.feasible else 0.0) + best.fitness)
        return candidate

    def add_pool(c: Candidate) -> None:
        # Elite retention and best-of-family replacement, bounded population.
        pool.append(c)
        pool.sort(key=_best_key, reverse=True)
        del pool[population_size:]

    def tournament() -> Candidate:
        choices = rng.choice(len(pool), size=min(3,len(pool)), replace=False)
        return max((pool[int(i)] for i in choices), key=_best_key)

    if method == 'ga_cs':
        ga_budget = min(evaluations, max(1, int(evaluations * switch_ratio)))
    else:
        ga_budget = evaluations if method == 'ga' else 0

    for idx in range(evaluations):
        if method == 'ga_cs':
            stage = 'ga' if idx < ga_budget else 'cs'
        elif method == 'ga':
            stage = 'ga'
        elif method == 'cs':
            stage = 'cs'
        else:
            stage = method

        if stage == 'random':
            gene = _random(k,problem.min_active,rng)
        elif stage == 'ga':
            if len(pool) < min(population_size, max(2, ga_budget)):
                gene = _random(k,problem.min_active,rng)
            else:
                p1,p2=tournament(),tournament()
                mask=int(rng.integers(0,1<<k))
                gene=(p1.genome & mask)|(p2.genome & ((1<<k)-1 ^ mask))
                if float(rng.random()) < .80:
                    gene=_mutate(gene,k,1+int(rng.random()<.22),problem.min_active,rng)
                gene=_repair(gene,k,problem.min_active,rng)
        elif stage == 'cs':
            if not pool:
                gene = _random(k,problem.min_active,rng)
            elif float(rng.random()) < .12:
                gene = _random(k,problem.min_active,rng)  # nest abandonment
            else:
                source = pool[int(rng.integers(0,len(pool)))]
                gene = _mutate(source.genome,k,_levy_flight_steps(k,rng),problem.min_active,rng)
        elif stage == 'anneal':
            if current is None:
                gene = _random(k,problem.min_active,rng)
            else:
                gene = _mutate(current.genome,k,1+int(rng.random()<.18),problem.min_active,rng)
        elif stage == 'greedy':
            if current is None:
                gene = _random(k,problem.min_active,rng)
            else:
                # Deterministic bitwise neighborhood, with periodic restarts.
                if idx % (2*k + 1) == 0:
                    gene = _random(k,problem.min_active,rng)
                else:
                    gene = _mutate(current.genome,k,1,problem.min_active,rng)
        else:
            raise AssertionError(stage)
        candidate=score(gene,stage)
        if stage in ('ga','cs'):
            add_pool(candidate)
        elif stage == 'anneal':
            if current is None or _best_key(candidate) > _best_key(current):
                current=candidate
            else:
                temperature=max(0.02,1.0-idx/evaluations)
                if float(rng.random()) < math.exp(min(0,(candidate.fitness-current.fitness)/temperature)):
                    current=candidate
        elif stage == 'greedy':
            if current is None or _best_key(candidate)>_best_key(current) or idx % (2*k+1)==0:
                current=candidate
    assert best is not None
    return SearchResult(method=method,seed=seed,evaluations=evaluations,best=best,
                        best_trace=tuple(trace),stage_evaluations=stages,
                        selected_rules=tuple(problem.rule_names[i] for i in range(k)
                                             if best.genome & (1<<i)))
