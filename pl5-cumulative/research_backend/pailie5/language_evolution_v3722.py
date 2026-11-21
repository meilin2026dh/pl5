"""PL5 V3.7.22: research-only, counterexample-gated *grammar extension*.

Three independent research roles communicate through append-only JSON files:
- setter builds a synthetic task and disjoint train/challenge/validation/holdout;
- inventor sees training cells only and induces restricted unary lookup operators;
- falsifier attacks these hypotheses on challenge cells, without re-training them.

This is finite-domain program synthesis, not invention of a fundamental operation.
All tasks and family code are developer-supplied; the simulation is NOT external
blind validation or evidence of lottery prediction. No unsafe Python execution.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from shutil import copyfile
from typing import Any

import numpy as np

from .meta_operator_v3721 import _features as _existing_features
from .structure_search_v372 import CellDataset
from .symbolic_operators_v30 import eval_expr

VERSION = 'pl5-v3722-grammar-extension-1'
RESEARCH_ONLY = {'production_enabled': False, 'lottery_predictive_advantage': 'NOT_ESTABLISHED',
                 'evidence_grade': 'DEVELOPMENT_SYNTHETIC_NOT_EXTERNAL_BLIND'}
SPLITS = (('training', 55), ('challenge', 15), ('validation', 10), ('holdout', 20))
FEATURE_NAMES = ('a', 'b', 'sum_mod10', 'difference_mod10', 'product_mod10',
                 'xor_mod10', 'absdiff_mod10', 'min', 'max', 'gcd',
                 'sum_raw', 'difference_raw', 'product_raw')
TASK_FAMILIES = ('cubic_sum', 'step_sum', 'square_difference', 'parity_difference',
                 'cubic_product', 'random_null', 'unstructured_interaction')


def _canon(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode('utf-8')).hexdigest()


def _signed(value: dict) -> dict:
    return {**value, 'integrity_sha256': _sha(value)}


def _write_new(path: Path, value: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


def _read_checked(path: Path, schema: str) -> dict:
    if path.stat().st_size > 300_000:
        raise ValueError('evidence exceeds file size cap')
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('evidence must be JSON object')
    signature = value.pop('integrity_sha256', None)
    if value.get('schema') != schema or signature != _sha(value):
        raise ValueError('invalid schema or evidence checksum')
    return value


def _features() -> dict[str, np.ndarray]:
    """Feature grammar is fixed, with a NEW bounded unary map layer on top.

    The learner may select feature semantics but cannot execute arbitrary code.
    """
    base = _existing_features()
    raw = {
        'a': base['a'], 'b': base['b'],
        'sum_mod10': base['sum'],
        'difference_mod10': base['difference'],
        'product_mod10': base['product'],
        'xor_mod10': base['xor'],
        'absdiff_mod10': base['absdiff'],
        'min': base['min'], 'max': base['max'], 'gcd': base['gcd'],
        'sum_raw': base['sum'],
        'difference_raw': base['difference'],
        'product_raw': base['product'],
    }
    result = {}
    for name in FEATURE_NAMES:
        # Vectorised integer evaluation precedes the final mod-10 projection.
        values = eval_expr(raw[name]).reshape((10, 10)).astype(np.int64)
        if not name.endswith('_raw'):
            values = np.mod(values, 10)
        result[name] = values
    return result


def _validate_spec(spec: dict, training_sha256: str) -> tuple[np.ndarray, np.ndarray]:
    if (not isinstance(spec, dict) or spec.get('kind') != 'learned_unary_table_v1'
            or spec.get('feature') not in FEATURE_NAMES
            or spec.get('training_sha256') != training_sha256):
        raise ValueError('unregistered or unbound operator')
    values = _features()[spec['feature']]
    mapping = spec.get('mapping')
    domain = sorted(set(map(int, values.ravel())))
    if (not isinstance(mapping, list) or len(mapping) != len(domain)
            or not isinstance(spec.get('domain'), list) or spec['domain'] != domain):
        raise ValueError('invalid operator domain')
    if any(item is not None and (type(item) is not int or not 0 <= item <= 9) for item in mapping):
        raise ValueError('invalid operator lookup output')
    if not isinstance(spec.get('candidate_id'), str) or len(spec['candidate_id']) != 64:
        raise ValueError('missing candidate identity')
    unsigned = {k: v for k, v in spec.items() if k != 'candidate_id'}
    if spec['candidate_id'] != _sha(unsigned):
        raise ValueError('operator definition changed')
    lookup = dict(zip(domain, mapping))
    output = np.full((10, 10), -1, dtype=np.int64)
    for key, item in lookup.items():
        if item is not None:
            output[values == key] = item
    return values, output


def _evaluate_spec(spec: dict, cells: CellDataset, training_sha256: str) -> dict:
    _, output = _validate_spec(spec, training_sha256)
    wrong, unknown = [], []
    for a, b, expected in cells.rows:
        seen = int(output[a, b])
        if seen < 0:
            unknown.append({'a': a, 'b': b, 'expected': expected, 'reason': 'unobserved_feature_value'})
        elif seen != expected:
            wrong.append({'a': a, 'b': b, 'expected': expected, 'predicted': seen})
    return {'errors': len(wrong), 'unknown': len(unknown), 'witnesses': (wrong + unknown)[:12]}



def finite_domain_certificate(spec: dict, training_sha256: str) -> dict:
    """Independently check all 100 scalar inputs and finite table properties.

    This proves properties ONLY for the digit domain 0..9 under the learned
    mapping, not for all integers or future lottery draws.
    """
    _, predicted = _validate_spec(spec, training_sha256)
    if np.any(predicted < 0):
        raise ValueError('cannot certify incomplete mapping')
    feature = spec['feature']
    domain_lookup = dict(zip(spec['domain'], spec['mapping']))
    def scalar(a: int, b: int) -> int:
        if feature == 'a': v = a
        elif feature == 'b': v = b
        elif feature.startswith('sum_'): v = a + b
        elif feature.startswith('difference_'): v = a - b
        elif feature.startswith('product_'): v = a * b
        elif feature == 'xor_mod10': v = a ^ b
        elif feature == 'absdiff_mod10': v = abs(a-b)
        elif feature == 'min': v = min(a,b)
        elif feature == 'max': v = max(a,b)
        elif feature == 'gcd': v = math.gcd(a,b)
        else: raise ValueError('unknown finite scalar feature')
        if not feature.endswith('_raw'):
            v %= 10
        return int(domain_lookup[v])
    checked = np.array([[scalar(a,b) for b in range(10)] for a in range(10)],dtype=np.int64)
    if not np.array_equal(checked, predicted):
        raise ValueError('vector/scalar discrepancy in certificate')
    return {'domain': 'a,b in {0,...,9}', 'exhaustive_cells': 100,
            'vector_scalar_agreement': True,
            'commutative_on_finite_domain': bool(np.array_equal(checked,checked.T)),
            'idempotent_on_finite_domain': bool(all(checked[x,x]==x for x in range(10))),
            'distinct_outputs': int(len(np.unique(checked))),
            'table_sha256': hashlib.sha256(checked.astype(np.uint8).tobytes()).hexdigest(),
            'not_a_general_math_theorem': True}


def _coordinate_overlap(*groups: list[list[int]]) -> bool:
    seen = set()
    for group in groups:
        keys = {(r[0], r[1]) for r in group}
        if len(keys) != len(group) or keys & seen:
            return True
        seen |= keys
    return False


def create_synthetic_task(destination: str | Path, *, family: str, seed: int):
    """Problem setter writes sealed partitions; no candidate is given the truth grid.

    Family/source are visible in this demonstrator. The evidence grade must
    never be upgraded to an external blind challenge from this API.
    """
    if family not in TASK_FAMILIES or type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError('unknown task family or seed')
    root = Path(destination)
    if root.exists():
        raise FileExistsError('problem-setter dataset already exists')
    root.mkdir(parents=True)
    a, b = np.indices((10, 10), dtype=np.int64)
    if family == 'cubic_sum':
        truth = (np.power(a + b, 3) + 3) % 10
    elif family == 'step_sum':
        truth = np.where((a + b) % 10 >= 5, 7, 2)
    elif family == 'square_difference':
        truth = ((a - b) ** 2 + 2 * (a - b) + 5) % 10
    elif family == 'parity_difference':
        truth = ((a - b) % 2) * 7 + 1
    elif family == 'cubic_product':
        truth = (7 * np.power((a * b) % 10, 3) + 2) % 10
    elif family == 'random_null':
        truth = np.random.default_rng(np.random.SeedSequence([3722, seed, 998])).integers(0, 10, (10, 10))
    else:
        truth = (3*a + b + 7*(a*b % 7)) % 10
    permutation = np.random.default_rng(np.random.SeedSequence([3722, seed, 7])).permutation(100)
    offset, parts = 0, {}
    for stage, count in SPLITS:
        ids = permutation[offset:offset+count]
        records = [[int(i//10), int(i % 10), int(truth.flat[i])] for i in ids]
        _write_new(root/(stage + '.json'), records)
        parts[stage] = {'count': count, 'data_sha256': _sha(sorted(records))}
        offset += count
    protocol = _signed({'schema': VERSION + ':task', 'family': family, 'seed': seed,
                        'partitions': parts, 'table_sha256': hashlib.sha256(
                            truth.astype(np.uint8).tobytes()).hexdigest(),
                        'train_validation_test_disjoint': True,
                        'task_factory_is_developer_authored': True,
                        'external_blind': False, **RESEARCH_ONLY})
    _write_new(root/'protocol.json', protocol)
    return protocol


def invent(training: CellDataset, directory: str | Path, *, max_candidates: int = 24) -> dict:
    """Inventor sees *training only*, not challenge/validation/holdout labels.

    Introduces a data-induced unary lookup class which is not part of the
    older integer-AST grammar. A partial mapping stays UNKNOWN rather than
    silently filling unseen values or memorising coordinate-specific data.
    """
    if not isinstance(training, CellDataset) or type(max_candidates) is not int or not 1 <= max_candidates <= 64:
        raise ValueError('invalid training or resource budget')
    directory = Path(directory)
    if directory.exists():
        raise FileExistsError('study already registered')
    feats = _features()
    rows = training.rows
    proposals, diagnostics = [], []
    for name, values in feats.items():
        domain = sorted(set(map(int, values.ravel())))
        observed: dict[int, set] = {}
        for a, b, y in rows:
            observed.setdefault(int(values[a, b]), set()).add(y)
        conflicts = sum(len(group) > 1 for group in observed.values())
        support = len(observed)
        diagnostics.append({'feature': name, 'domain_size': len(domain),
                            'observed_inputs': support, 'conflicting_inputs': conflicts})
        if conflicts or support < 6 or len(domain) > 24:
            continue
        mapping = [next(iter(observed[v])) if v in observed else None for v in domain]
        definition = {'kind': 'learned_unary_table_v1', 'feature': name, 'domain': domain,
                      'mapping': mapping, 'training_sha256': training.fingerprint}
        spec = {**definition, 'candidate_id': _sha(definition)}
        _, predicted = _validate_spec(spec, training.fingerprint)
        errors = sum(int(predicted[a, b] != y) for a, b, y in rows)
        # 'description_length' is a proxy based on stored lookup entries, not a
        # proof of minimal description length.
        proposals.append((len(domain), -support, name, spec,
                          hashlib.sha256(predicted.astype('<i2').tobytes()).hexdigest(), errors))
    proposals.sort(key=lambda x: (x[0], x[1], x[2]))
    selected, seen_semantics = [], set()
    for domain_size, negative_support, _, spec, semantic_sha, error in proposals:
        if semantic_sha in seen_semantics:
            continue
        seen_semantics.add(semantic_sha)
        selected.append({'spec': spec, 'training_errors': error, 'domain_size': domain_size,
                         'observed_feature_inputs': -negative_support,
                         'coverage_complete': None not in spec['mapping'],
                         'table_sha256': semantic_sha})
        if len(selected) >= max_candidates:
            break
    directory.mkdir(parents=True)
    registry = _signed({'schema': VERSION + ':proposal', 'training_sha256': training.fingerprint,
                        'training_pairs': [list(p) for p in training.pairs],
                        'candidate_limit': max_candidates, 'evaluated_features': len(feats),
                        'diagnostics': diagnostics, 'candidates': selected,
                        'train_labels_only': True, 'test_labels_used': False, **RESEARCH_ONLY})
    _write_new(directory/'proposal.json', registry)
    return registry


def falsify(study: str | Path, challenge: CellDataset) -> dict:
    """Independent falsifier records contrary examples; it cannot fit models.

    Candidate mutations after this stage are prohibited by the evidence chain.
    """
    if not isinstance(challenge, CellDataset):
        raise ValueError('challenge should be CellDataset')
    root = Path(study)
    if (root/'falsification.json').exists():
        raise FileExistsError('challenge already conducted')
    proposal = _read_checked(root/'proposal.json', VERSION+':proposal')
    if _coordinate_overlap(proposal['training_pairs'], [list(r) for r in challenge.pairs]):
        raise ValueError('training/challenge coordinate leak')
    results = []
    for card in proposal['candidates']:
        audit = _evaluate_spec(card['spec'], challenge, proposal['training_sha256'])
        results.append({'candidate_id': card['spec']['candidate_id'],
                        'feature': card['spec']['feature'],
                        'challenge_errors': audit['errors'],
                        'challenge_unknown': audit['unknown'],
                        'counterexamples': audit['witnesses'],
                        'passes': audit['errors'] == 0 and audit['unknown'] == 0})
    evidence = _signed({'schema': VERSION+':challenge', 'proposal_sha256': _sha(proposal),
                        'training_pairs': proposal['training_pairs'],
                        'challenge_sha256': challenge.fingerprint,
                        'challenge_pairs': [list(p) for p in challenge.pairs],
                        'results': results, 'retrain_after_counterexample': False,
                        'test_labels_used': False, **RESEARCH_ONLY})
    _write_new(root/'falsification.json', evidence)
    return evidence


def freeze(study: str | Path, validation: CellDataset) -> dict:
    if not isinstance(validation, CellDataset):
        raise ValueError('expected CellDataset validation')
    root = Path(study)
    if (root/'freeze.json').exists() or (root/'final_operator.json').exists():
        raise FileExistsError('selection already frozen')
    proposal = _read_checked(root/'proposal.json', VERSION+':proposal')
    attack = _read_checked(root/'falsification.json', VERSION+':challenge')
    if attack['proposal_sha256'] != _sha(proposal):
        raise ValueError('proposal was modified after challenge')
    if _coordinate_overlap(proposal['training_pairs'],attack['challenge_pairs'],
                           [list(p) for p in validation.pairs]):
        raise ValueError('validation coordinates not independent')
    cards = {c['spec']['candidate_id']: c for c in proposal['candidates']}
    accepted = []
    for check in attack['results']:
        if not check['passes']:
            continue
        card = cards[check['candidate_id']]
        if not card['coverage_complete']:
            continue
        quality = _evaluate_spec(card['spec'], validation, proposal['training_sha256'])
        if quality['errors'] or quality['unknown']:
            continue
        accepted.append(card)
    accepted.sort(key=lambda c:(c['domain_size'], c['spec']['candidate_id']))
    semantic_tables = {c['table_sha256'] for c in accepted}
    status = 'FROZEN' if len(semantic_tables) == 1 and accepted else 'ABSTAIN'
    if not accepted:
        reason = 'no_candidate_survives_challenge_and_validation'
    elif len(semantic_tables) > 1:
        reason = 'multiple_distinct_behaviours_not_disambiguated'
    else:
        reason = None
    winner = accepted[0] if status == 'FROZEN' else None
    certificate = finite_domain_certificate(winner['spec'], proposal['training_sha256']) if winner else None
    if winner is not None:
        _write_new(root/'final_operator.json', _signed({'schema':VERSION+':operator',
                  'proposal_sha256': _sha(proposal), 'spec': winner['spec'],
                  'selected_on': 'training+challenge+validation_without_test_labels',
                  **RESEARCH_ONLY}))
    payload = _signed({'schema': VERSION+':freeze', 'proposal_sha256': _sha(proposal),
                       'challenge_sha256': _sha(attack),
                       'training_pairs': proposal['training_pairs'],
                       'challenge_pairs': attack['challenge_pairs'],
                       'validation_pairs': [list(p) for p in validation.pairs],
                       'validation_sha256': validation.fingerprint,
                       'status': status, 'reason': reason,
                       'selected_id': winner['spec']['candidate_id'] if winner else None,
                       'selected_feature': winner['spec']['feature'] if winner else None,
                       'passing_candidate_count': len(accepted),
                       'distinct_candidate_behaviours': len(semantic_tables),
                       'finite_domain_certificate': certificate,
                       'test_labels_used': False, **RESEARCH_ONLY})
    _write_new(root/'freeze.json', payload)
    return payload


def evaluate(study: str | Path, holdout: CellDataset) -> dict:
    """One-shot, immutable post-freeze evaluation with no adaptive re-selection."""
    if not isinstance(holdout, CellDataset):
        raise ValueError('expected CellDataset holdout')
    root = Path(study)
    if (root/'evaluation.json').exists():
        raise FileExistsError('holdout evaluated already')
    proposal = _read_checked(root/'proposal.json', VERSION+':proposal')
    attack = _read_checked(root/'falsification.json', VERSION+':challenge')
    selection = _read_checked(root/'freeze.json', VERSION+':freeze')
    if (attack['proposal_sha256'] != _sha(proposal) or
            selection['proposal_sha256'] != _sha(proposal) or
            selection['challenge_sha256'] != _sha(attack)):
        raise ValueError('evidence chain broken')
    if _coordinate_overlap(selection['training_pairs'], selection['challenge_pairs'],
                           selection['validation_pairs'], [list(p) for p in holdout.pairs]):
        raise ValueError('holdout overlaps previous study stage')
    if selection['status'] == 'ABSTAIN':
        if (root/'final_operator.json').exists():
            raise ValueError('abstention has unexpected model')
        result = {'status': 'ABSTAIN', 'holdout_errors': None,
                  'holdout_unknown': None, 'holdout_accuracy': None}
    else:
        final = _read_checked(root/'final_operator.json', VERSION+':operator')
        if final['proposal_sha256'] != _sha(proposal) or final['spec']['candidate_id'] != selection['selected_id']:
            raise ValueError('frozen model not same as selected model')
        expected = next(c for c in proposal['candidates'] if c['spec']['candidate_id'] == selection['selected_id'])
        if final['spec'] != expected['spec']:
            raise ValueError('frozen specification not same as original proposal')
        errors = _evaluate_spec(final['spec'], holdout, proposal['training_sha256'])
        result = {'status': 'EVALUATED', 'holdout_errors': errors['errors'],
                  'holdout_unknown': errors['unknown'],
                  'holdout_accuracy': (len(holdout.rows)-errors['errors']-errors['unknown'])/len(holdout.rows)}
    report = _signed({'schema': VERSION+':evaluation', 'selection_sha256': _sha(selection),
                      'holdout_sha256': holdout.fingerprint,
                      'holdout_count': len(holdout.rows),
                      'no_retraining_or_reselection_after_holdout': True,
                      **result, **RESEARCH_ONLY})
    _write_new(root/'evaluation.json', report)
    return report


def propose_revision(study: str | Path, original_training: CellDataset,
                     original_challenge: CellDataset, new_directory: str | Path) -> dict:
    """Counterexample-guided next iteration, NOT an approved frozen model.

    The old challenge observations are now training facts. Consequently they
    MUST NOT be reused as independent challenge, validation or holdout in the
    new study. A fresh independent gate and an untouched test are mandatory.
    """
    if not isinstance(original_training, CellDataset) or not isinstance(original_challenge, CellDataset):
        raise ValueError('both input partitions must be CellDataset')
    root = Path(study)
    if (root/'freeze.json').exists() or (root/'evaluation.json').exists():
        raise ValueError('revision must precede prior validation freeze and holdout evaluation')
    proposal = _read_checked(root/'proposal.json', VERSION+':proposal')
    attack = _read_checked(root/'falsification.json', VERSION+':challenge')
    if (proposal['training_sha256'] != original_training.fingerprint
            or attack['challenge_sha256'] != original_challenge.fingerprint
            or attack['proposal_sha256'] != _sha(proposal)):
        raise ValueError('revision inputs do not match prior experiment evidence')
    if _coordinate_overlap([list(p) for p in original_training.pairs],
                           [list(p) for p in original_challenge.pairs]):
        raise ValueError('revision source partitions overlap')
    combined = CellDataset(tuple(original_training.rows + original_challenge.rows))
    next_proposal = invent(combined, new_directory)
    provenance = _signed({
        'schema': VERSION+':revision', 'parent_proposal_sha256': _sha(proposal),
        'parent_falsification_sha256': _sha(attack),
        'combined_training_sha256': combined.fingerprint,
        'combined_training_count': len(combined.rows),
        'consumed_challenge_is_now_training': True,
        'require_new_independent_challenge_and_validation': True,
        'holdout_labels_used': False, 'status': 'PROPOSED_NOT_VALIDATED', **RESEARCH_ONLY})
    _write_new(Path(new_directory)/'revision_provenance.json', provenance)
    return {'new_proposal': next_proposal, 'revision_provenance': provenance}
