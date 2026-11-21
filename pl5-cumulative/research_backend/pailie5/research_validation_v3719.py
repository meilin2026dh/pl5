"""V3.7.19: reproducible, strictly past-only *retrospective* PL5 research audit.

This module provides evidence for algorithms, not evidence of forecast advantage.
A CSV backtest cannot verify that the candidate set existed before publication;
prospective prediction must be independently timestamped and sealed.

Prediction tracks share a comparable 100,000-number hit-rate baseline. NCA,
finite-algebra discovery and GA-CS are evaluated on separate engineering tasks:
their metrics must NEVER be combined with observed lottery hit rates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import re
from typing import Callable, Sequence

import numpy as np
from scipy.stats import binomtest

from .engine import score_candidates
from .probability_ranker import rank_target_snapshot_v3717

DOMAIN = 100_000
VERSION = 'pl5-v3719-research-validation-1'
METHODS = ('random', 'positional', 'pairwise', 'ensemble', 'heuristic_rank')


def _digest(value: object) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':')).encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class Draw:
    issue: str
    number: str


@dataclass(frozen=True)
class Protocol:
    warmup: int = 40
    test_size: int = 10
    top_k: int = 100
    seed: int = 3719
    alpha: float = 0.01
    methods: tuple[str, ...] = METHODS

    def __post_init__(self) -> None:
        if type(self.warmup) is not int or self.warmup < 30:
            raise ValueError('warmup must be at least 30 for the historical ranker')
        if type(self.test_size) is not int or self.test_size < 1:
            raise ValueError('test_size must be positive')
        if type(self.top_k) is not int or not 1 <= self.top_k <= DOMAIN:
            raise ValueError('top_k must be between 1 and 100000')
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError('seed must be a nonnegative int')
        if type(self.alpha) not in (float, int) or not 0 < self.alpha < 1:
            raise ValueError('alpha must lie strictly in (0,1)')
        if not isinstance(self.methods, (tuple, list)) or not self.methods:
            raise ValueError('methods must be a nonempty list')
        if len(set(self.methods)) != len(self.methods) or any(m not in METHODS for m in self.methods):
            raise ValueError('unsupported or duplicate methods')
        if 'random' not in self.methods:
            raise ValueError('the random control is mandatory')


def validate_draws(rows: Sequence[Draw]) -> tuple[Draw, ...]:
    records = tuple(rows)
    if not records:
        raise ValueError('empty history')
    prior = -1
    for row in records:
        if (not isinstance(row, Draw) or not isinstance(row.issue, str)
                or re.fullmatch(r'[0-9]+', row.issue) is None
                or not isinstance(row.number, str)
                or re.fullmatch(r'[0-9]{5}', row.number) is None):
            raise ValueError('draws require exact five ASCII digits and numeric issue IDs')
        issue = int(row.issue)
        if issue <= prior:
            raise ValueError('issues must be unique and chronologically increasing')
        prior = issue
    return records


def _predict(history: tuple[str, ...], method: str, protocol: Protocol,
             *, index: int) -> np.ndarray:
    """Only prior draws enter this callable; actual result is deliberately absent."""
    if method == 'random':
        return np.sort(np.random.default_rng(protocol.seed + index).choice(
            DOMAIN, size=protocol.top_k, replace=False).astype(np.int32))
    if method == 'heuristic_rank':
        return np.sort(rank_target_snapshot_v3717(list(history)).order[:protocol.top_k])
    scores = score_candidates(list(history), method)
    # Tie-breaking is seed-controlled. No labels or rank of test draw involved.
    rng = np.random.default_rng(protocol.seed + index)
    scores = scores + rng.uniform(-1e-12, 1e-12, size=DOMAIN)
    return np.sort(np.lexsort((np.arange(DOMAIN, dtype=np.int32), -scores))[:protocol.top_k])


def _frozen_picks(picks: np.ndarray, expected_size: int) -> np.ndarray:
    p = np.asarray(picks)
    if p.ndim != 1 or len(p) != expected_size or p.dtype.kind not in ('i', 'u'):
        raise ValueError('candidate set must have the frozen integer budget')
    if (np.any(p < 0) or np.any(p >= DOMAIN) or len(np.unique(p)) != expected_size):
        raise ValueError('candidate set must contain valid unique ticket IDs')
    frozen = np.sort(p.astype('<i4', copy=True))
    frozen.flags.writeable = False
    return frozen


def _wilson(hits: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    phat = hits / n
    denom = 1 + z*z/n
    center = (phat + z*z/(2*n))/denom
    radius = z*math.sqrt(phat*(1-phat)/n + z*z/(4*n*n))/denom
    return round(max(0.0, center-radius), 10), round(min(1.0, center+radius), 10)


def run_walk_forward(rows: Sequence[Draw], protocol: Protocol,
                     *, input_type: str = 'unverified_historical_csv',
                     predictor: Callable[[tuple[str, ...], str, Protocol, int], np.ndarray] | None = None) -> dict:
    """Retrospective walk-forward. The predictor *never* receives the target.

    ``predictor`` is for isolated adapter tests/research. The caller owns its
    pre-registration; this function cannot prove external precommitment.
    """
    records = validate_draws(rows)
    if input_type not in ('unverified_historical_csv', 'synthetic_fair_iid'):
        raise ValueError('source provenance must be declared and supported')
    if len(records) <= protocol.warmup:
        raise ValueError('not enough history for the warmup and one test')
    begin = max(protocol.warmup, len(records)-protocol.test_size)
    selected = records[begin:]
    if not selected:
        raise ValueError('empty held-out evaluation')
    predictions = []
    for idx in range(begin, len(records)):
        # No target or suffix is read until every candidate set is frozen.
        prior = tuple(r.number for r in records[:idx])
        history_digest = _digest([(r.issue, r.number) for r in records[:idx]])
        period_sets = []
        for method in protocol.methods:
            raw = (_predict(prior, method, protocol, index=idx) if predictor is None
                   else predictor(prior, method, protocol, idx))
            picks = _frozen_picks(raw, protocol.top_k)
            candidate_digest = sha256(picks.tobytes()).hexdigest()
            period_sets.append((method, picks, candidate_digest))
        # Reveal outcome only AFTER all models for the period have made picks.
        actual = records[idx]
        winning_id = int(actual.number)
        for method, picks, candidate_digest in period_sets:
            hit = bool(np.searchsorted(picks, winning_id) < len(picks)
                       and picks[np.searchsorted(picks, winning_id)] == winning_id)
            predictions.append({
                'issue':actual.issue, 'method':method, 'history_count':len(prior),
                'history_sha256':history_digest, 'candidate_sha256':candidate_digest,
                'candidate_count':protocol.top_k, 'actual':actual.number, 'hit':hit,
            })
    n = len(selected)
    p0 = protocol.top_k/DOMAIN
    family = max(1, sum(m!='random' for m in protocol.methods))
    models = []
    for method in protocol.methods:
        hits = sum(int(r['hit']) for r in predictions if r['method'] == method)
        single = float(binomtest(hits, n, p=p0, alternative='greater').pvalue)
        models.append({
            'method':method, 'test_periods':n, 'top_k':protocol.top_k,
            'hits':hits, 'hit_rate':hits/n, 'fair_expected_hits':n*p0,
            'fair_hit_probability':p0, 'wilson_95_interval':_wilson(hits, n),
            'one_sided_binomial_p':single,
            'bonferroni_family_p':min(1.0, family*single) if method != 'random' else None,
            'passes_predeclared_alpha':(min(1.0, family*single) < protocol.alpha)
                if method != 'random' else False,
            'predictive_advantage':'NOT_ESTABLISHED',
        })
    return {
        'schema':VERSION, 'protocol':asdict(protocol), 'input_type':input_type,
        'dataset_sha256':_digest([(r.issue, r.number) for r in records]),
        'protocol_sha256':_digest(asdict(protocol)), 'dataset_rows':len(records),
        'first_test_issue':selected[0].issue, 'last_test_issue':selected[-1].issue,
        'test_count':n, 'baseline_per_draw':p0, 'models':models,
        'predictions':predictions,
        'evidence_level':'RETROSPECTIVE_WALK_FORWARD_ONLY',
        'prospective_precommitment_verified':False,
        'production_enabled':False,
        'predictive_advantage':'NOT_ESTABLISHED',
        'warnings':[
            'This is a retrospective simulation, not externally sealed prospective forecasting.',
            'The input CSV and issue chronology were not independently authenticated.',
            'P-values assume independent fair draws; repeated holdout selection or parameter tuning invalidates nominal significance.',
            'Bonferroni adjusts the within-run model family only, not repeated experiments across versions.',
            'Engineering benchmarks, finite algebra and NCA tasks cannot be pooled with lottery hit rates.',
        ],
    }


def synthetic_fair_draws(*, n: int, seed: int) -> tuple[Draw, ...]:
    if type(n) is not int or n < 31 or type(seed) is not int or seed < 0:
        raise ValueError('n >= 31 and a nonnegative seed are required')
    rng = np.random.default_rng(seed)
    return tuple(Draw(str(i + 1), f'{int(num):05d}')
                 for i, num in enumerate(rng.integers(0, DOMAIN, size=n)))


def auxiliary_track_checks(*, seed: int = 3719) -> dict:
    """Separate frozen toy/synthetic *engineering* checks for other tracks.

    Not a claim that NCA, algebraic operators or GA-CS predict future draws.
    """
    from . import nca_v36, math_language_v37, ga_cs_optimizer_v3715
    if type(seed) is not int or seed < 0:
        raise ValueError('seed must be nonnegative')
    rng = np.random.default_rng(seed)
    # NCA has its own chronological input contract and a disjoint holdout.
    ext = rng.integers(0, 10, size=80)
    values = rng.integers(0, DOMAIN, size=80)
    observations = [nca_v36.Observation(str(i+1), f'{int(v):05d}', int(e))
                    for i, (e, v) in enumerate(zip(ext, values))]
    nca = nca_v36.fit_and_test(observations[:50], observations[50:])
    # Finite-algebra model: holdout cells are evaluated after masked fit.
    a, b = np.indices((10, 10))
    table = ((a+b) % 10).astype(np.uint8)
    mask = rng.random((10, 10)) < 0.7
    mask[0, 0] = True
    algebra = math_language_v37.discover(table, mask)
    # GA-CS optimizes frozen rule masks, no prize labels enter fitness.
    masks = tuple(sum(1 << j for j in range(128) if (j+i) % (i+3) != 0)
                  for i in range(4))
    problem = ga_cs_optimizer_v3715.SearchProblem(
        masks=masks, rule_names=tuple(f'r{i}' for i in range(4)),
        universe_size=128, target=45, min_survivors=20, max_survivors=80,
        min_active=1)
    ga = ga_cs_optimizer_v3715.optimize(problem, method='ga_cs', evaluations=48, seed=seed)
    random = ga_cs_optimizer_v3715.optimize(problem, method='random', evaluations=48, seed=seed)
    return {
        'schema':'pl5-v3719-auxiliary-tracks-1', 'input':'frozen_synthetic_only',
        'nca': {'train':50, 'holdout':30, 'operator':nca['operator'],
                'test_miss_rate':nca['test_miss_rate'], 'baseline':nca['baseline'],
                'external_publication_independently_verified':False},
        'math_language': {'observed_cells':int(mask.sum()), 'holdout_cells':int((~mask).sum()),
                          'observed_errors':algebra['observed_errors'],
                          'holdout_errors':algebra['unseen_errors'],
                          'expression':algebra['expression'],
                          'heldout_cells_were_used_for_operator_fit':False,
                          'protocol_not_blinded_at_module_output':True},
        'ga_cs': {'evaluation_budget_each':48, 'ga_cs_fitness':ga.best.fitness,
                  'random_fitness':random.best.fitness,
                  'ga_cs_feasible':ga.best.feasible, 'random_feasible':random.best.feasible,
                  'lottery_draw_labels_used':False},
        'production_enabled':False, 'predictive_advantage':'NOT_ESTABLISHED',
    }
