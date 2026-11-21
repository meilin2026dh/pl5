"""Phase II: locally verifiable PL5 prospective research packets.

A local file and UTC timestamp CANNOT independently prove pre-draw commitment.
Users may publish the SEALED PACKET DIGEST to a third-party service before
publication of the target issue and retain the independently dated receipt.
This module does not authenticate external receipts or lottery source identity.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Callable

import numpy as np

from .research_validation_v3719 import (
    DOMAIN, Draw, Protocol, _frozen_picks, _predict, validate_draws,
)

SCHEMA = 'pl5-v3719-phase2-local-seal-v1'


def digest(value: object) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def checked_document(value: dict) -> dict:
    doc = dict(value)
    doc['document_sha256'] = digest(doc)
    return doc


def verify_document(doc: dict, expected_kind: str) -> None:
    if not isinstance(doc, dict) or doc.get('kind') != expected_kind or doc.get('schema') != SCHEMA:
        raise ValueError('unexpected evidence schema or kind')
    checksum = doc.get('document_sha256')
    if not isinstance(checksum, str) or len(checksum) != 64 or digest({k:v for k,v in doc.items() if k!='document_sha256'}) != checksum:
        raise ValueError('evidence checksum mismatch: altered or corrupted')


def read_evidence(path: Path, kind: str) -> dict:
    doc = json.loads(Path(path).read_text(encoding='utf-8'))
    verify_document(doc, kind)
    return doc


def save_new(path: Path, obj: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # 'x' fails on an existing file. Other-process edits/deletions require an
    # externally audited append-only store; do not claim otherwise.
    with path.open('x', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        f.write('\n')


def read_draw_csv(path: Path) -> tuple[tuple[Draw,...], str]:
    raw = Path(path).read_bytes()
    try:
        stream = io.StringIO(raw.decode('utf-8-sig'), newline='')
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        issue_key = 'issue' if 'issue' in headers else 'period' if 'period' in headers else None
        if issue_key is None or 'number' not in headers or len(set(headers)) != len(headers):
            raise ValueError('CSV must contain unique issue/period and number headers')
        rows = []
        for record in reader:
            if None in record or record.get(issue_key) is None or record.get('number') is None:
                raise ValueError('CSV has malformed cells')
            rows.append(Draw(record[issue_key].strip(), record['number'].strip()))
        validated = validate_draws(rows)
        return validated, sha256(raw).hexdigest()
    except UnicodeError as exc:
        raise ValueError('CSV must be UTF-8') from exc


def reconcile(primary_path: Path, witness_path: Path, *, min_overlap: int = 1) -> dict:
    if Path(primary_path).resolve() == Path(witness_path).resolve():
        raise ValueError('source paths must be distinct')
    primary, primary_sha = read_draw_csv(primary_path)
    witness, witness_sha = read_draw_csv(witness_path)
    if primary_sha == witness_sha:
        raise ValueError('source CSV files must not be byte-identical')
    w = {r.issue:r.number for r in witness}
    matches = [r.issue for r in primary if r.issue in w and w[r.issue] == r.number]
    mismatches = [r.issue for r in primary if r.issue in w and w[r.issue] != r.number]
    if mismatches:
        raise ValueError(f'conflicting publication rows: {mismatches[:5]}')
    if min_overlap < 1 or len(matches) < min_overlap:
        raise ValueError('insufficient cross-source overlap')
    return {
        'primary_raw_sha256':primary_sha, 'witness_raw_sha256':witness_sha,
        'matched_issues':matches,
        'matched_count':len(matches), 'primary_count':len(primary),
        'unchecked_primary_count':len(primary)-len(matches),
        'source_authentication':'NOT_INDEPENDENTLY_AUTHENTICATED',
        'warning':'Both sources may share upstream data; matching rows do not establish independent provenance.',
    }


def _algorithm_fingerprint() -> dict:
    folder = Path(__file__).resolve().parent
    paths = ('research_validation_v3719.py', 'engine.py', 'probability_ranker.py',
             'prospective_validation_v3719.py')
    return {name:sha256((folder/name).read_bytes()).hexdigest() for name in paths}


def register(*, primary: Path, witness: Path, primary_url: str, witness_url: str,
             target_issue: str, protocol: Protocol, study_id: str) -> dict:
    if not study_id or not study_id.isascii() or not all(c.isalnum() or c in '-_' for c in study_id):
        raise ValueError('study id must contain ASCII letters/digits/_/-')
    if not primary_url.startswith('https://') or not witness_url.startswith('https://') or primary_url == witness_url:
        raise ValueError('two distinct HTTPS source descriptions required')
    rows, _ = read_draw_csv(primary)
    rec = reconcile(primary, witness)
    if not target_issue.isascii() or not target_issue.isdigit() or int(target_issue) <= int(rows[-1].issue):
        raise ValueError('target issue must strictly follow available history')
    if len(rows) < protocol.warmup:
        raise ValueError('insufficient history for warmup')
    return checked_document({
        'kind':'registration', 'schema':SCHEMA, 'created_at_utc_local_clock':utc_now(),
        'study_id':study_id, 'target_issue':target_issue,
        'last_known_issue':rows[-1].issue,
        'history_sha256':digest([(r.issue,r.number) for r in rows]),
        'history_count':len(rows), 'protocol': {
            'warmup':protocol.warmup, 'test_size':protocol.test_size,
            'top_k':protocol.top_k, 'seed':protocol.seed,
            'alpha':protocol.alpha, 'methods':list(protocol.methods),
        },
        'source_descriptions':{'primary':primary_url, 'witness':witness_url},
        'crosscheck':rec,
        'algorithm_sha256':_algorithm_fingerprint(),
        'prospective_precommitment_verified':False,
        'production_enabled':False,
    })


def _protocol_from_record(record: dict) -> Protocol:
    p = record['protocol']
    return Protocol(warmup=p['warmup'], test_size=p['test_size'], top_k=p['top_k'],
                    seed=p['seed'], alpha=p['alpha'], methods=tuple(p['methods']))


def seal(registration: dict, primary: Path, witness: Path,
         *, predictor: Callable | None = None) -> dict:
    verify_document(registration, 'registration')
    rows,_ = read_draw_csv(primary)
    current_crosscheck = reconcile(primary, witness)
    if current_crosscheck != registration['crosscheck']:
        raise ValueError('source snapshots changed after preregistration')
    if digest([(r.issue,r.number) for r in rows]) != registration['history_sha256']:
        raise ValueError('training history changed after preregistration')
    if registration['algorithm_sha256'] != _algorithm_fingerprint():
        raise ValueError('algorithm code changed since preregistration')
    if rows[-1].issue != registration['last_known_issue'] or int(registration['target_issue']) <= int(rows[-1].issue):
        raise ValueError('target issue is not after history')
    cfg = _protocol_from_record(registration)
    past = tuple(r.number for r in rows)
    candidates = {}
    for method in cfg.methods:
        raw = (_predict(past, method, cfg, index=len(rows)) if predictor is None
               else predictor(past, method, cfg, len(rows)))
        picks = _frozen_picks(raw, cfg.top_k)
        candidates[method] = {
            'numbers':[f'{int(n):05d}' for n in picks],
            'candidate_sha256':sha256(picks.tobytes()).hexdigest(),
        }
    return checked_document({
        'kind':'seal', 'schema':SCHEMA,
        'sealed_at_utc_local_clock':utc_now(),
        'registration_sha256':registration['document_sha256'],
        'study_id':registration['study_id'],
        'target_issue':registration['target_issue'],
        'last_known_issue':registration['last_known_issue'],
        'history_sha256':registration['history_sha256'],
        'algorithm_sha256':registration['algorithm_sha256'],
        'protocol':registration['protocol'],
        'candidates':candidates,
        'attestation_status':'LOCAL_HASH_ONLY_NO_INDEPENDENT_TIMESTAMP',
        'prospective_precommitment_verified':False,
        'production_enabled':False,
    })


def verify_seal(registration: dict, packet: dict) -> None:
    verify_document(registration, 'registration')
    verify_document(packet, 'seal')
    if (packet['registration_sha256'] != registration['document_sha256']
        or packet['target_issue'] != registration['target_issue']
        or packet['history_sha256'] != registration['history_sha256']
        or packet['algorithm_sha256'] != registration['algorithm_sha256']
        or packet['protocol'] != registration['protocol']):
        raise ValueError('registration/seal binding mismatch')
    cfg = _protocol_from_record(registration)
    if set(packet['candidates']) != set(cfg.methods):
        raise ValueError('candidate method family mismatch')
    for method, value in packet['candidates'].items():
        numbers = value['numbers']
        if (not isinstance(numbers, list) or len(numbers) != cfg.top_k
            or any(not isinstance(x,str) or len(x)!=5 or not x.isascii() or not x.isdigit() for x in numbers)):
            raise ValueError('invalid candidate numbers')
        picks = _frozen_picks(np.array([int(n) for n in numbers], dtype=np.int32), cfg.top_k)
        if numbers != [f'{int(x):05d}' for x in picks]:
            raise ValueError('candidate list not in canonical sorted order')
        if sha256(picks.tobytes()).hexdigest()!=value['candidate_sha256']:
            raise ValueError('candidate bytes digest mismatch')


def settle(registration: dict, packet: dict, primary: Path, witness: Path) -> dict:
    verify_seal(registration, packet)
    # New outcome sources must retain the complete frozen prefix. No data corrections
    # can silently modify the training history after sealing.
    source = reconcile(primary, witness)
    rows,_ = read_draw_csv(primary)
    end = next((i for i,r in enumerate(rows) if r.issue == packet['target_issue']), None)
    if end is None or end != registration['history_count']:
        raise ValueError('target issue absent or history prefix changed')
    if digest([(r.issue,r.number) for r in rows[:end]]) != registration['history_sha256']:
        raise ValueError('historical prefix modified after sealing')
    if packet['target_issue'] not in source['matched_issues']:
        raise ValueError('target outcome must match across both sources')
    outcome = rows[end].number
    results = {m:{'hit':outcome in value['numbers'], 'candidate_sha256':value['candidate_sha256']}
               for m,value in packet['candidates'].items()}
    return checked_document({
        'kind':'settlement', 'schema':SCHEMA,
        'settled_at_utc_local_clock':utc_now(),
        'registration_sha256':registration['document_sha256'],
        'seal_sha256':packet['document_sha256'],
        'target_issue':packet['target_issue'],
        'outcome':outcome, 'source_crosscheck':source, 'results':results,
        'fair_baseline_hit_probability_per_method':registration['protocol']['top_k']/DOMAIN,
        'prospective_precommitment_verified':False,
        'evidence_level':'LOCAL_PROSPECTIVE_WORKFLOW_NOT_EXTERNALLY_TIMESTAMPED',
        'predictive_advantage':'NOT_ESTABLISHED',
        'production_enabled':False,
    })


def verify_settlement(registration: dict, packet: dict, result: dict) -> None:
    verify_seal(registration, packet)
    verify_document(result, 'settlement')
    if (result['registration_sha256'] != registration['document_sha256']
        or result['seal_sha256'] != packet['document_sha256']
        or result['target_issue'] != packet['target_issue']):
        raise ValueError('settlement binding mismatch')
    for name, value in packet['candidates'].items():
        if result['results'][name]['hit'] != (result['outcome'] in value['numbers']):
            raise ValueError('settlement hit inconsistent with sealed candidate list')
        if result['results'][name]['candidate_sha256'] != value['candidate_sha256']:
            raise ValueError('candidate digest inconsistent with settlement')
