"""V3.7.21: counterexample-guided, finite-domain *derived* operator research.

The only discovery input is a CellDataset of training cells. A new unary map
q(x)=u*x*x+v*x+w (mod 10) can be promoted to a bounded legacy AST, but no
new mathematical law or lottery predictive advantage is claimed. The grammar,
coefficient domain, and admission rules are human designed. Artifacts are
append-only and locally hash checked, not authenticated third-party timestamps.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from shutil import copyfile
from itertools import product

import numpy as np

from .math_discovery_v3720 import _basis, invent_compositions
from .structure_ast_v372 import normalize, table, validate_ast
from .structure_search_v372 import CellDataset, FrozenOperator
from .structure_evidence_v372 import save_operator, load_operator, evaluate_frozen
from .symbolic_operators_v30 import CONST

VERSION = 'pl5-v3721-counterexample-meta-1'
RESEARCH_ONLY = {'production_enabled': False, 'predictive_advantage': 'NOT_ESTABLISHED',
                 'lottery_prediction_test': False}


def _canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _digest(obj):
    return hashlib.sha256(_canon(obj).encode('utf-8')).hexdigest()


def _sign(obj):
    return {**obj, 'integrity_sha256': _digest(obj)}


def _new(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        f.write('\n')


def _checked(path: Path, schema: str):
    if path.stat().st_size > 200_000:
        raise ValueError('research evidence size exceeded')
    obj = json.loads(path.read_text('utf-8'))
    signature = obj.pop('integrity_sha256', None)
    if obj.get('schema') != schema or signature != _digest(obj):
        raise ValueError('research evidence integrity/schema mismatch')
    return obj


def _bin(op, left, right):
    return ('binary', op, left, right)


def _quadratic_ast(feature, u: int, v: int, w: int):
    """Horner form: ((u*x+v)*x+w), to satisfy 15-node AST restriction."""
    scaled = feature if u == 1 else _bin('mul', ('const', u), feature)
    linear = scaled if v == 0 else _bin('add', scaled, ('const', v))
    squared = _bin('mul', linear, feature)
    expr = squared if w == 0 else _bin('add', squared, ('const', w))
    return normalize(expr)


def _features():
    return {**_basis(), 'difference': _bin('sub', ('a',), ('b',))}


def fibre_diagnostics(training: CellDataset) -> list[dict]:
    """A consistent feature fibre x=>y is required before hypothesizing q(x).

    Zero conflict is a necessary, not sufficient, condition for a unary law.
    These diagnostics see *only* observed training coordinates and values.
    """
    if not isinstance(training, CellDataset):
        raise ValueError('training must be CellDataset')
    output = []
    for name, expr in _features().items():
        vals = table(expr)
        groups = {}
        for a, b, y in training.rows:
            groups.setdefault(int(vals[a, b]), set()).add(y)
        conflicts = sum(len(v) > 1 for v in groups.values())
        output.append({'feature': name, 'distinct_input_values': len(groups),
                       'conflicting_input_values': conflicts,
                       'eligible': len(groups) >= 6 and conflicts == 0})
    return output


def invent_meta_operators(training: CellDataset, *, top_n: int = 12) -> dict:
    """Fit new derived unary polynomial forms without reading unseen labels.

    Search u>0 to represent a genuinely nonlinear *family relative to the
    earlier two-feature affine family*. Representations that exceed bounded
    existing AST grammar are discarded, never executed with eval/exec.
    """
    if (not isinstance(training, CellDataset) or type(top_n) is not int
            or not 1 <= top_n <= 32):
        raise ValueError('invalid training or candidate budget')
    diagnostics = fibre_diagnostics(training)
    allowed = {r['feature'] for r in diagnostics if r['eligible']}
    basis = _features()
    ids = np.array([10*a + b for a, b, _ in training.rows], dtype=np.int64)
    targets = np.array([y for _, _, y in training.rows], dtype=np.int64)
    candidates = {}
    attempted = 0
    for name in sorted(allowed):
        term = basis[name]
        vals = table(term).astype(np.int64).reshape(-1)
        for u, v, w in product(CONST, CONST, CONST):
            if u == 0:
                continue
            attempted += 1
            prediction = ((u * vals * vals + v * vals + w) % 10).astype(np.uint8)
            errors = int(np.count_nonzero(prediction[ids] != targets))
            expr = _quadratic_ast(term, u, v, w)
            try:
                nodes, depth = validate_ast(expr)
            except ValueError:
                continue
            # Semantic deduplication uses input predictions, not unseen labels.
            key = prediction.tobytes()
            record = {'feature': name, 'coefficients': [u, v, w],
                      'training_errors': errors, 'nodes': nodes, 'depth': depth,
                      'unary_lookup_mod10': [int((u*x*x+v*x+w)%10) for x in range(10)],
                      'second_difference_mod10': (2*u) % 10}
            rank = (errors, nodes, repr(expr))
            if key not in candidates or rank < candidates[key][0]:
                candidates[key] = (rank, expr, record)
    top = sorted(candidates.values(), key=lambda v: v[0])[:top_n]
    return {'expressions': tuple(item[1] for item in top),
            'records': [item[2] for item in top], 'fibre_diagnostics': diagnostics,
            'evaluated_parameters': attempted, 'distinct_behaviours': len(candidates),
            'source': 'training_only', **RESEARCH_ONLY}


def propose(training: CellDataset, destination: str | Path, *, top_n: int = 12) -> dict:
    """Stage 1: training-only proposal. No validation or test argument exists."""
    if not isinstance(training, CellDataset):
        raise ValueError('expected CellDataset')
    dest = Path(destination)
    if dest.exists():
        raise FileExistsError('study directory already exists')
    # Parent composition baseline is a comparator, not the whole V3.7.20 search.
    legacy = invent_compositions(training, top_n=1)
    proposals = invent_meta_operators(training, top_n=top_n)
    origin = [('legacy_composition', legacy['expressions'][0], None)]
    origin.extend((f'meta_{i:02d}', expr, proposals['records'][i])
                  for i, expr in enumerate(proposals['expressions']))
    dest.mkdir(parents=True)
    previous_table = table(origin[0][1])
    cards = []
    for name, expression, meta in origin:
        op = FrozenOperator(expression, training.fingerprint, training.pairs)
        if op.identity in {c['operator_id'] for c in cards}:
            continue
        path = f'operators/{name}.json'
        save_operator(op, dest/path)
        values = table(expression)
        errors = [{'a':a, 'b':b, 'expected':y, 'got':int(values[a,b])}
                  for a,b,y in training.rows if int(values[a,b]) != y]
        repaired = [{'a':a, 'b':b, 'expected':y} for a,b,y in training.rows
                    if int(previous_table[a,b]) != y and int(values[a,b]) == y]
        cards.append({'name':name, 'operator_id':op.identity, 'path':path,
                      'training_errors':len(errors), 'training_counterexamples':errors[:12],
                      'legacy_error_repairs':len(repaired),
                      'legacy_repair_witnesses':repaired[:8],
                      'origin': 'meta-polynomial' if meta else 'legacy-composition',
                      'learned_meta':meta})
    report = _sign({'schema':VERSION+':proposal', 'training_sha256':training.fingerprint,
                    'training_pairs':[list(x) for x in training.pairs],
                    'baseline_training_errors':legacy['records'][0]['training_errors'],
                    'hypothesis_count':proposals['evaluated_parameters'],
                    'distinct_meta_behaviours':proposals['distinct_behaviours'],
                    'fibre_diagnostics':proposals['fibre_diagnostics'],
                    'candidates':cards, 'training_only':True,
                    'holdout_read':False, **RESEARCH_ONLY})
    _new(dest/'proposal.json', report)
    return report


def freeze(study: str | Path, validation: CellDataset, *, max_error_rate: float = 0.0) -> dict:
    """Stage 2: validation-only selection or abstention, no holdout input.

    Abstain on high validation error OR multiple distinct table behaviours tied
    for winning validation score. This is a conservative research gate.
    """
    if not isinstance(validation, CellDataset) or type(max_error_rate) not in (float, int) \
            or not 0 <= max_error_rate <= 0.5:
        raise ValueError('invalid validation or abstention threshold')
    study = Path(study)
    if (study/'freeze.json').exists() or (study/'final_operator.json').exists():
        raise FileExistsError('frozen study is append-only')
    proposal = _checked(study/'proposal.json', VERSION+':proposal')
    seen = {tuple(p) for p in proposal['training_pairs']}
    if seen & set(validation.pairs):
        raise ValueError('training/validation coordinate leakage')
    ranked = []
    for card in proposal['candidates']:
        # Explicit whitelist avoids arbitrary relative/absolute path traversal.
        if card['path'] != f"operators/{card['name']}.json":
            raise ValueError('unexpected operator path')
        operator = load_operator(study/card['path'])
        if (operator.identity != card['operator_id']
                or operator.source_data_sha256 != proposal['training_sha256']
                or set(operator.source_pairs) != seen):
            raise ValueError('candidate fingerprint mismatch')
        result = evaluate_frozen(operator, validation)
        ranked.append({'name':card['name'], 'operator_id':operator.identity,
                       'validation_errors':result['errors'], 'nodes':validate_ast(operator.expression)[0],
                       'path':card['path'], 'table_sha256':hashlib.sha256(table(operator.expression).tobytes()).hexdigest()})
    ranked.sort(key=lambda c:(c['validation_errors'], c['nodes'], c['operator_id']))
    leader = ranked[0]
    tied_tables = {r['table_sha256'] for r in ranked if r['validation_errors'] == leader['validation_errors']}
    too_many_errors = leader['validation_errors']/len(validation.rows) > max_error_rate
    ambiguous = len(tied_tables) > 1
    status = 'ABSTAIN' if too_many_errors or ambiguous else 'FROZEN'
    reason = ('validation_error_exceeds_threshold' if too_many_errors else
              'distinct_models_tied_on_validation' if ambiguous else 'validation_gate_passed')
    if status == 'FROZEN':
        # Freeze candidate before exposing the stage-3 interface.
        copyfile(study/leader['path'], study/'final_operator.json')
    payload = _sign({'schema':VERSION+':freeze', 'proposal_sha256':_digest(proposal),
                     'training_sha256':proposal['training_sha256'],
                     'training_pairs':proposal['training_pairs'],
                     'validation_sha256':validation.fingerprint,
                     'validation_pairs':[list(x) for x in validation.pairs],
                     'status':status, 'abstention_reason':reason if status=='ABSTAIN' else None,
                     'selected':leader if status=='FROZEN' else None,
                     'best_candidate':leader, 'validation_results':ranked,
                     'test_labels_used':False, **RESEARCH_ONLY})
    _new(study/'freeze.json', payload)
    return payload


def evaluate(study: str | Path, holdout: CellDataset) -> dict:
    """Stage 3: immutable one-shot test, never adapt on holdout outcomes."""
    if not isinstance(holdout, CellDataset):
        raise ValueError('expected CellDataset')
    study = Path(study)
    if (study/'evaluation.json').exists():
        raise FileExistsError('holdout already evaluated')
    prop = _checked(study/'proposal.json', VERSION+':proposal')
    frozen = _checked(study/'freeze.json', VERSION+':freeze')
    if frozen['proposal_sha256'] != _digest(prop):
        raise ValueError('proposal changed after freezing')
    if set(holdout.pairs) & ({tuple(p) for p in frozen['training_pairs']} |
                             {tuple(p) for p in frozen['validation_pairs']}):
        raise ValueError('holdout coordinate overlap')
    if frozen['status']=='ABSTAIN':
        if (study/'final_operator.json').exists():
            raise ValueError('abstained study has unexpected frozen operator')
        data = {'status':'ABSTAIN', 'holdout_errors':None, 'holdout_accuracy':None,
                'operator_id':None, 'no_holdout_scoring':True}
    else:
        operator = load_operator(study/'final_operator.json')
        if (operator.identity != frozen['selected']['operator_id'] or
                operator.source_data_sha256 != frozen['training_sha256']):
            raise ValueError('frozen operator modified')
        result = evaluate_frozen(operator, holdout)
        data = {'status':'EVALUATED','holdout_errors':result['errors'],
                'holdout_accuracy':result['accuracy'],'operator_id':operator.identity,
                'no_holdout_scoring':False}
    report = _sign({'schema':VERSION+':evaluation',
                    'freeze_sha256':_digest(frozen), 'holdout_sha256':holdout.fingerprint,
                    'holdout_count':len(holdout.rows), **data,
                    'evidence_grade':'DEVELOPMENT_SYNTHETIC_ONLY',
                    'selection_changed_after_holdout':False, **RESEARCH_ONLY})
    _new(study/'evaluation.json', report)
    return report


def make_synthetic(destination: str | Path, *, case: str, seed: int) -> dict:
    """Developer-provided synthetic demonstration; not a genuinely blind task."""
    if case not in ('square_sum', 'quadratic_difference', 'linear_sum', 'cubic_sum', 'iid_null'):
        raise ValueError('unknown synthetic case')
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError('invalid seed')
    dest = Path(destination)
    if dest.exists():
        raise FileExistsError('synthetic case path already exists')
    dest.mkdir(parents=True)
    a,b = np.indices((10,10), dtype=np.int64)
    if case=='square_sum':
        truth = ((a+b)**2+3)%10
    elif case=='quadratic_difference':
        truth = ((a-b)**2+2*(a-b)+5)%10
    elif case=='linear_sum':
        truth = (2*a+3*b+5)%10
    elif case=='cubic_sum':
        truth = ((a+b)**3+3)%10
    else:
        truth = np.random.default_rng(np.random.SeedSequence([seed, 3721, 999])).integers(0,10,(10,10))
    order = np.random.default_rng(np.random.SeedSequence([seed, 3721])).permutation(100)
    for name, ids in [('training',order[:60]),('validation',order[60:80]),('holdout',order[80:])]:
        rows = [[int(i//10),int(i%10),int(truth.flat[i])] for i in ids]
        _new(dest/(name+'.json'),rows)
    meta = _sign({'schema':VERSION+':synthetic', 'case':case, 'seed':seed,
                  'truth_sha256':hashlib.sha256(np.asarray(truth,dtype=np.uint8).tobytes()).hexdigest(),
                  'partition':'60/20/20, coordinate-disjoint',
                  'source':'synthetic, constructed in same codebase as the learner',
                  'external_blind':False, **RESEARCH_ONLY})
    _new(dest/'protocol.json',meta)
    return meta
