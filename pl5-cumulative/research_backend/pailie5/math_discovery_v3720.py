"""V3.7.20 bounded, auditable mathematical-expression discovery (research only).

This module reuses the existing safe integer AST and frozen-operator evaluator.
One stage receives *only* training rows, a second receives validation rows,
and a final stage receives never-used test rows. No user Python is executed.
Generated compositions are novel *relative to this fixed search catalogue*;
there is no claim of invention of fundamental mathematics or of predictive skill.
"""
from __future__ import annotations

import hashlib
import json
from itertools import combinations
from pathlib import Path
from shutil import copyfile

import numpy as np

from .structure_ast_v372 import normalize, validate_ast, table
from .structure_search_v372 import CellDataset, SearchConfig, FrozenOperator, fit
from .structure_evidence_v372 import save_operator, load_operator, evaluate_frozen

VERSION = 'pl5-v3720-three-gate-math-research-1'
A, B = ('a',), ('b',)
COEFFICIENTS = (0, 1, 2, 3, 5, 9)
SHIFTS = (0, 1, 2, 3, 5, 9)


def _binary(op, l, r):
    return ('binary', op, l, r)


def _canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _digest(obj):
    return hashlib.sha256(_canonical(obj).encode('utf-8')).hexdigest()


def _write_new(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as h:
        json.dump(obj, h, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        h.write('\n')


def _read_checked(path: Path, schema: str):
    obj = json.loads(path.read_text('utf-8'))
    sig = obj.pop('integrity_sha256', None)
    if obj.get('schema') != schema or not isinstance(sig, str) or sig != _digest(obj):
        raise ValueError(f'corrupted or unsupported research evidence: {path.name}')
    return obj


def _signed(obj):
    return {**obj, 'integrity_sha256': _digest(obj)}


def read_cells(path: str | Path) -> CellDataset:
    """Strict digit-operation observations; no time-series/lottery targets."""
    path = Path(path)
    if path.stat().st_size > 16384:
        raise ValueError('cell data size limit exceeded')
    raw = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(raw, list):
        raise ValueError('expected a list of 10x10 grid observations')
    return CellDataset(tuple(tuple(row) if isinstance(row, list) else row for row in raw))


def _basis():
    return {
        'a': A,
        'b': B,
        'sum': _binary('add', A, B),
        'product': _binary('mul', A, B),
        'absdiff': _binary('absdiff', A, B),
        'xor': _binary('xor', A, B),
        'min': _binary('min', A, B),
        'max': _binary('max', A, B),
        'gcd': _binary('gcd', A, B),
        'a_squared': _binary('mul', A, A),
        'b_squared': _binary('mul', B, B),
    }


def _scaled(coefficient: int, term):
    if coefficient == 0:
        return ('const', 0)
    if coefficient == 1:
        return term
    return _binary('mul', ('const', coefficient), term)


def _expression(t1, t2, u, v, shift):
    output = _binary('add', _scaled(u, t1), _scaled(v, t2))
    if shift:
        output = _binary('add', output, ('const', shift))
    return normalize(output)


def invent_compositions(training: CellDataset, *, top_n: int = 16) -> dict:
    """Fit coefficient parameters on training labels only; return bounded ASTs.

    Feature-pair families are synthesized from all distinct safe feature pairs;
    unlike arbitrary Python generation, the grammar and coefficients are fixed.
    Behaviour deduplication uses *input predictions*, not any unseen labels.
    """
    if not isinstance(training, CellDataset) or type(top_n) is not int or not 1 <= top_n <= 32:
        raise ValueError('invalid training observations or top_n')
    basis = _basis()
    feature_values = {name: table(expr).astype(np.int64).reshape(-1) for name, expr in basis.items()}
    ids = np.array([10 * a + b for a, b, _ in training.rows], dtype=np.int64)
    target = np.array([v for _, _, v in training.rows], dtype=np.int64)
    selected = {}
    count = 0
    valid = 0
    for name1, name2 in combinations(basis, 2):
        t1, t2 = basis[name1], basis[name2]
        f1, f2 = feature_values[name1], feature_values[name2]
        for u in COEFFICIENTS:
            for v in COEFFICIENTS:
                if u == v == 0:
                    continue
                for shift in SHIFTS:
                    count += 1
                    expr = _expression(t1, t2, u, v, shift)
                    try:
                        nodes, _ = validate_ast(expr, max_nodes=15, max_depth=8)
                    except ValueError:
                        continue
                    valid += 1
                    # Keep integer intermediary semantics to agree with the old AST.
                    prediction = ((u * f1 + v * f2 + shift) % 10).astype(np.uint8)
                    errors = int(np.count_nonzero(prediction[ids] != target))
                    key = prediction.tobytes()
                    score = (errors, nodes, repr(expr))
                    prior = selected.get(key)
                    if prior is None or score < prior[0]:
                        selected[key] = (score, expr, (name1, name2, u, v, shift))
    ranked = sorted(selected.values(), key=lambda item: item[0])[:top_n]
    return {
        'expressions': tuple(x[1] for x in ranked),
        'records': [{'source_features': [x[2][0], x[2][1]],
                     'learned_coefficients': [x[2][2], x[2][3], x[2][4]],
                     'training_errors': x[0][0], 'nodes': x[0][1]}
                    for x in ranked],
        'proposal_count': count,
        'valid_ast_count': valid,
        'distinct_behaviours': len(selected),
        'labels_used': 'training_only',
    }


def _check_disjoint(*datasets):
    seen = set()
    for data in datasets:
        pairs = set(data.pairs)
        if seen & pairs:
            raise ValueError('training/validation/holdout coordinate leakage')
        seen |= pairs


def propose(training: CellDataset, destination: str | Path, *, seed: int = 3720,
            eval_budget: int = 1200, top_n: int = 16) -> dict:
    """First gate: NO validation or test dataset accepted by this function."""
    if (not isinstance(training, CellDataset) or type(seed) is not int or not 0 <= seed < 2**32
            or type(eval_budget) is not int or not 100 <= eval_budget <= 10000):
        raise ValueError('invalid bounded research configuration')
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError('append-only study directory already exists')
    destination.mkdir(parents=True)
    cfg = SearchConfig(seed=seed, max_evaluations=eval_budget,
                       generations=8, population=32, beam_width=16, max_nodes=15, max_depth=8)
    baseline = fit(training, cfg)
    generated = invent_compositions(training, top_n=top_n)
    # Repair search is conditioned on training-only failed examples.
    repair = fit(training, cfg, warm_starts=generated['expressions'])
    source = {'baseline': baseline.operator, 'repaired': repair.operator}
    for i, expr in enumerate(generated['expressions']):
        source[f'invention_{i:02d}'] = FrozenOperator(expr, training.fingerprint, training.pairs)
    cards = []
    seen_ids = set()
    for label, operator in source.items():
        if operator.identity in seen_ids:
            continue
        seen_ids.add(operator.identity)
        filename = f'operators/{label}.json'
        save_operator(operator, destination / filename)
        pred = table(operator.expression)
        failed = [{'a': a, 'b': b, 'expected': y, 'predicted': int(pred[a, b])}
                  for a, b, y in training.rows if int(pred[a, b]) != y]
        nodes, depth = validate_ast(operator.expression)
        cards.append({'name': label, 'path': filename, 'operator_id': operator.identity,
                      'training_errors': len(failed), 'training_counterexamples': failed[:12],
                      'nodes': nodes, 'depth': depth, 'source': 'training_only',
                      'research_only': True})
    report = _signed({
        'schema': VERSION + ':proposal', 'training_sha256': training.fingerprint,
        'training_pairs': [list(p) for p in training.pairs],
        'seed': seed, 'budget_per_search': eval_budget, 'generated': {
            k: v for k, v in generated.items() if k != 'expressions'},
        'baseline': {'training_errors': baseline.training_errors,
                     'evaluations': baseline.evaluated_expressions},
        'repair': {'training_errors': repair.training_errors,
                   'evaluations': repair.evaluated_expressions},
        'candidates': cards,
        'selection_used': 'training_only',
        'holdout_read': False,
        'production_enabled': False,
        'predictive_advantage': 'NOT_ESTABLISHED',
    })
    _write_new(destination/'proposal.json', report)
    return report


def freeze(study: str | Path, validation: CellDataset) -> dict:
    """Second gate: choose one expression using validation cells, never test cells."""
    study = Path(study)
    card = _read_checked(study/'proposal.json', VERSION + ':proposal')
    if not isinstance(validation, CellDataset):
        raise ValueError('validation must be CellDataset')
    train_pairs = {tuple(p) for p in card['training_pairs']}
    if train_pairs & set(validation.pairs):
        raise ValueError('training/validation coordinate leakage')
    if (study/'freeze.json').exists() or (study/'final_operator.json').exists():
        raise FileExistsError('frozen research evidence cannot be replaced')
    measured = []
    for candidate in card['candidates']:
        operator = load_operator(study/candidate['path'])
        if (operator.identity != candidate['operator_id'] or
                operator.source_data_sha256 != card['training_sha256'] or
                set(operator.source_pairs) != train_pairs):
            raise ValueError('candidate identity or source provenance mismatch')
        result = evaluate_frozen(operator, validation)
        measured.append({'name': candidate['name'], 'operator_id': operator.identity,
                         'validation_errors': result['errors'], 'nodes': candidate['nodes'],
                         'source_path': candidate['path']})
    measured.sort(key=lambda x: (x['validation_errors'], x['nodes'], x['operator_id']))
    winner = measured[0]
    copyfile(study/winner['source_path'], study/'final_operator.json')
    frozen = _signed({
        'schema': VERSION + ':freeze',
        'proposal_integrity_sha256': _digest(card),
        'training_sha256': card['training_sha256'],
        'train_pairs': card['training_pairs'],
        'validation_sha256': validation.fingerprint,
        'validation_pairs': [list(p) for p in validation.pairs],
        'selected': winner, 'validation_results': measured,
        'selection_used': 'validation_only_after_training_frozen',
        'test_labels_used': False, 'production_enabled': False,
        'predictive_advantage': 'NOT_ESTABLISHED',
    })
    _write_new(study/'freeze.json', frozen)
    return frozen


def evaluate(study: str | Path, holdout: CellDataset) -> dict:
    """Third gate: no re-fitting. The final heldout labels must be truly untouched."""
    study = Path(study)
    prop = _read_checked(study/'proposal.json', VERSION + ':proposal')
    frozen = _read_checked(study/'freeze.json', VERSION + ':freeze')
    if frozen['proposal_integrity_sha256'] != _digest(prop):
        raise ValueError('proposal altered after freeze')
    if not isinstance(holdout, CellDataset):
        raise ValueError('holdout must be CellDataset')
    unseen = set(holdout.pairs)
    if unseen & ({tuple(p) for p in frozen['train_pairs']} | {tuple(p) for p in frozen['validation_pairs']}):
        raise ValueError('holdout coordinate overlaps training or validation')
    if (study/'evaluation.json').exists():
        raise FileExistsError('test evidence is append-only; one evaluation per freeze')
    operator = load_operator(study/'final_operator.json')
    if (operator.identity != frozen['selected']['operator_id'] or
            operator.source_data_sha256 != frozen['training_sha256']):
        raise ValueError('frozen winner has been modified')
    result = evaluate_frozen(operator, holdout)
    predicted = table(operator.expression)
    errors = [{'a': a, 'b': b, 'predicted': int(predicted[a, b]), 'observed': y}
              for a, b, y in holdout.rows if int(predicted[a, b]) != y]
    report = _signed({
        'schema': VERSION + ':evaluation',
        'freeze_integrity_sha256': _digest(frozen),
        'operator_id': operator.identity,
        'holdout_sha256': holdout.fingerprint,
        'holdout_count': result['count'], 'holdout_errors': result['errors'],
        'holdout_accuracy': result['accuracy'],
        'holdout_counterexamples': errors,
        'selection_changed_after_holdout': False,
        'evidence_grade': 'EXPLORATORY_SYNTHETIC_ONLY',
        'production_enabled': False,
        'predictive_advantage': 'NOT_ESTABLISHED',
        'lottery_prediction_test': False,
    })
    _write_new(study/'evaluation.json', report)
    return report


def split_synthetic(destination: str | Path, *, case: str = 'composite_absproduct',
                    seed: int = 3720) -> dict:
    """Demo only: fixed structured tasks and null control, *not* independent data."""
    if case not in ('composite_absproduct', 'shifted_square', 'iid_null'):
        raise ValueError('unsupported synthetic study')
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError('invalid seed')
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError('demo directory must be new')
    destination.mkdir(parents=True)
    a, b = np.indices((10, 10), dtype=np.int64)
    if case == 'composite_absproduct':
        truth = ((a*b + np.abs(a-b)) % 10).astype(np.uint8)
    elif case == 'shifted_square':
        truth = (((a+b)**2+3) % 10).astype(np.uint8)
    else:
        truth = np.random.default_rng(np.random.SeedSequence([seed, 884])).integers(0, 10, (10, 10), dtype=np.uint8)
    order = np.random.default_rng(np.random.SeedSequence([seed, 3720])).permutation(100)
    train_ids, validation_ids, test_ids = order[:60], order[60:80], order[80:]
    for label, ids in (('training', train_ids), ('validation', validation_ids), ('holdout', test_ids)):
        rows = [(int(i//10), int(i%10), int(truth.flat[i])) for i in ids]
        _write_new(destination/(label+'.json'), rows)
    meta = _signed({'schema': VERSION+':demo', 'case': case, 'seed': seed,
                    'grid_sha256': hashlib.sha256(truth.tobytes()).hexdigest(),
                    'protocol': 'locally generated synthetic split; not external blind trial',
                    'train_n': 60, 'validation_n': 20, 'holdout_n': 20,
                    'predictive_advantage': 'NOT_ESTABLISHED'})
    _write_new(destination/'protocol.json', meta)
    return meta
