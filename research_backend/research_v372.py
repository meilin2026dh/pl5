"""PL5 V3.7.2 research CLI; offline by default, never executes supplied code."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np
from pailie5.math_language_v37 import discover
from pailie5.structure_ast_v372 import GRAMMAR
from pailie5.structure_search_v372 import CellDataset, SearchConfig, fit
from pailie5.structure_evidence_v372 import (
    evaluate_frozen, certify_table, save_operator, load_operator,
)

CASES = ('addition', 'bilinear', 'absolute_product', 'squared_sum', 'mixed_minimum', 'iid_random')


def _write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')


def _load_cells(path):
    p = Path(path)
    if p.stat().st_size > 65536: raise ValueError('cell file too large')
    raw = json.loads(p.read_text('utf-8'))
    return CellDataset(raw)


def _prepare_output(path):
    p = Path(path)
    p.mkdir(parents=True, exist_ok=False)
    return p


def _truth(case, seed):
    a, b = np.indices((10, 10))
    if case == 'addition': return (a+b) % 10
    if case == 'bilinear': return (a*b+a) % 10
    if case == 'absolute_product': return np.abs(a*b-3) % 10
    if case == 'squared_sum': return ((a+b)*(a+b)) % 10
    if case == 'mixed_minimum': return np.minimum(a+b, a*b) % 10
    if case == 'iid_random':
        return np.random.default_rng(seed ^ 0x73AA).integers(0, 10, (10, 10))
    raise ValueError('unknown synthetic case')


def _split(truth, seed):
    indices = np.random.default_rng(seed ^ 0x13B7).permutation(100)
    def make(ids):
        return CellDataset(tuple((int(i//10), int(i%10), int(truth.flat[i])) for i in ids))
    mask = np.zeros((10,10), dtype=bool)
    mask.flat[indices[:70]] = True
    return make(indices[:70]), make(indices[70:]), mask


def _trial(case, config, directory, *, baseline=True):
    truth = _truth(case, config.seed)
    train, holdout, mask = _split(truth, config.seed)
    directory.mkdir(parents=True, exist_ok=False)
    _write(directory/'training_cells.json', train.rows)
    # Selection API cannot access truth or holdout; these remain in the caller.
    started = time.perf_counter()
    result = fit(train, config)
    fit_seconds = time.perf_counter()-started
    save_operator(result.operator, directory/'operator.json')
    frozen = load_operator(directory/'operator.json')
    held = evaluate_frozen(frozen, holdout)
    cert = certify_table(frozen, truth)
    altered = CellDataset(tuple((a,b,(y+1)%10) for a,b,y in holdout.rows))
    shifted = evaluate_frozen(frozen, altered)
    report = {
        'case': case, 'seed': config.seed, 'data_type': 'synthetic_operation_table',
        'search': result.to_dict(), 'holdout': held, 'certificate': cert,
        'changed_law_without_refit': shifted,
        'changed_law_meaning': 'same unseen inputs, every true output shifted by +1 mod10; intentionally different operation',
        'fit_seconds': fit_seconds,
        'limitations': ['70/30 input-pair holdout, not future lottery draws',
                        'grammar primitives and bounds are supplied by humans',
                        'no model changes after holdout results'],
    }
    if baseline:
        fixed = discover(truth, mask)
        report['fixed_v37_baseline'] = {
            'expression': fixed['expression'], 'candidates': fixed['candidate_count'],
            'training_errors': fixed['observed_errors'], 'holdout_errors': fixed['unseen_errors'],
            'holdout_count': 30, 'exact_on_all_100_pairs': fixed['exact_certified'],
            'compute_matched': False,
        }
    _write(directory/'holdout_cells.json', holdout.rows)
    _write(directory/'truth_table.json', truth.tolist())
    _write(directory/'report.json', report)
    return report


def _code_fingerprints():
    root = Path(__file__).resolve().parent
    names = ['research_v372.py', 'pailie5/structure_ast_v372.py',
             'pailie5/structure_search_v372.py', 'pailie5/structure_evidence_v372.py',
             'pailie5/symbolic_operators_v30.py', 'pailie5/math_language_v37.py']
    return {name: sha256((root/name).read_bytes()).hexdigest() for name in names}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('fit', 'demo', 'benchmark'):
        p = sub.add_parser(command)
        p.add_argument('--output', required=True, type=Path, help='new output directory; existing paths are never overwritten')
        p.add_argument('--seed', type=int, default=20261102)
        p.add_argument('--max-evaluations', type=int, default=12000)
        p.add_argument('--generations', type=int, default=30)
        if command == 'fit': p.add_argument('--input', type=Path, required=True)
        if command == 'benchmark': p.add_argument('--seeds', nargs='+', type=int, default=[20261102,20261103,20261104])
    p = sub.add_parser('evaluate')
    p.add_argument('--operator', type=Path, required=True)
    p.add_argument('--input', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'evaluate':
            report = evaluate_frozen(load_operator(args.operator), _load_cells(args.input))
            print(json.dumps(report, ensure_ascii=False, allow_nan=False))
            return 0
        config = SearchConfig(seed=args.seed, max_evaluations=args.max_evaluations, generations=args.generations)
        if args.command == 'fit':
            data = _load_cells(args.input)
            result = fit(data, config)
            out = _prepare_output(args.output)
            save_operator(result.operator, out/'operator.json')
            _write(out/'fit_report.json', result.to_dict())
            _write(out/'training_cells.json', data.rows)
            print(json.dumps({'output': str(out), 'expression': result.operator.to_dict()['description'],
                              'training_errors': result.training_errors, 'production_enabled': False}))
        elif args.command == 'demo':
            out = _prepare_output(args.output)
            report = _trial('bilinear', config, out/'trial')
            _write(out/'report.json', report)
            print(json.dumps({'output': str(out), 'holdout': report['holdout'],
                              'description': report['search']['operator']['description']}))
        else:
            if not 1 <= len(args.seeds) <= 10 or len(set(args.seeds)) != len(args.seeds):
                raise ValueError('benchmark needs 1..10 different seeds')
            configs = [SearchConfig(seed=s, max_evaluations=args.max_evaluations,
                                    generations=args.generations) for s in args.seeds]
            out = _prepare_output(args.output)
            protocol = {
                'version': '3.7.2', 'purpose': 'development-stage synthetic structure benchmark',
                'cases': list(CASES), 'configs': [asdict(c) for c in configs],
                'training_pairs': 70, 'heldout_pairs': 30, 'grammar': GRAMMAR,
                'selection': 'train-only; all cases and seeds reported, including failures',
                'baseline': 'V3.7 fixed 1020 expressions; budgets not compute-matched',
                'code_sha256': _code_fingerprints(), 'python': platform.python_version(),
                'numpy': np.__version__, 'recorded_before_trials_utc': datetime.now(timezone.utc).isoformat(),
                'not_external_blind_validation': True,
            }
            _write(out/'protocol.json', protocol)
            protocol_sha = sha256((out/'protocol.json').read_bytes()).hexdigest()
            trials = []
            for case in CASES:
                for cfg in configs:
                    trial = _trial(case, cfg, out/f'{case}_{cfg.seed}')
                    trials.append(trial)
                    print(f'{case} seed={cfg.seed}: train {70-trial["search"]["training_errors"]}/70, '
                          f'holdout {30-trial["holdout"]["errors"]}/30, '
                          f'exact={trial["certificate"]["exact_on_all_100_pairs"]}', flush=True)
            summary = {'protocol_sha256': protocol_sha, 'protocol': protocol, 'trials': trials,
                       'production_enabled': False, 'predictive_advantage': 'NOT_ESTABLISHED'}
            _write(out/'benchmark_results.json', summary)
            print(json.dumps({'output': str(out), 'trials': len(trials), 'protocol_sha256': protocol_sha}))
        return 0
    except (ValueError, OSError, json.JSONDecodeError, RecursionError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
