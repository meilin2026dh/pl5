"""V3.7.19 Phase III: cautious verification of two manually collected draw ledgers.

Crosschecking two publisher tables does not authenticate their web origin or
prove statistical forecasting ability.  The returned report is retrospective.
"""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse

from .prospective_validation_v3719 import digest, read_draw_csv, reconcile
from .research_validation_v3719 import Protocol, run_walk_forward

VERSION = 'pl5-v3719-phase3-data-quality-1'


def _host(url: str) -> str:
    parsed = urlparse(url)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
            or parsed.password or parsed.port is not None):
        raise ValueError('source URL must be a public HTTPS hostname without credentials')
    return parsed.hostname.lower().removeprefix('www.').removeprefix('api.')


def inspect_sources(primary: Path, witness: Path, *, primary_url: str,
                    witness_url: str, min_overlap: int = 1,
                    require_consecutive: bool = False) -> dict:
    if _host(primary_url) == _host(witness_url):
        raise ValueError('publisher hosts must differ; two pages of one site are not two independent publishers')
    primary_rows, primary_digest = read_draw_csv(primary)
    witness_rows, witness_digest = read_draw_csv(witness)
    match = reconcile(primary, witness, min_overlap=min_overlap)
    verified_issues = frozenset(match['matched_issues'])
    prefix = [r.issue for r in primary_rows if r.issue not in verified_issues]
    if require_consecutive and any(int(b.issue) != int(a.issue) + 1
                                   for a, b in zip(primary_rows, primary_rows[1:])):
        raise ValueError('gaps exist in the selected strict consecutive interval')
    return {
        'schema': VERSION,
        'primary_url': primary_url, 'witness_url': witness_url,
        'primary_sha256': primary_digest, 'witness_sha256': witness_digest,
        'primary_count': len(primary_rows), 'witness_count': len(witness_rows),
        'overlap_verified_count': len(verified_issues),
        'overlap_verified_issues': sorted(verified_issues, key=int),
        'primary_not_crosschecked_issues': prefix,
        'primary_not_crosschecked_count': len(prefix),
        'crosschecked_dataset_sha256': digest([[r.issue,r.number] for r in primary_rows if r.issue in verified_issues]),
        'raw_page_html_preserved': False,
        'source_identity_independently_authenticated': False,
        'evidence_grade': 'CROSSCHECKED_TRANSCRIPT_NOT_ARCHIVED_SOURCE',
        'draw_sequence_consecutive': all(int(b.issue) == int(a.issue)+1 for a,b in zip(primary_rows,primary_rows[1:])),
        'warning': 'Two independently hosted pages agreed, but site authenticity, raw page bytes and historical edit times are not cryptographically proved.',
    }


def audited_walk_forward(primary: Path, witness: Path, *, primary_url: str,
                         witness_url: str, protocol: Protocol,
                         min_overlap: int = 1, strict_test_crosscheck: bool = True,
                         require_consecutive: bool = False) -> dict:
    quality = inspect_sources(primary, witness, primary_url=primary_url,
                              witness_url=witness_url, min_overlap=min_overlap,
                              require_consecutive=require_consecutive)
    rows, _ = read_draw_csv(primary)
    test_start = max(protocol.warmup, len(rows) - protocol.test_size)
    if test_start >= len(rows):
        raise ValueError('no historical test periods after warmup')
    expected_test = [r.issue for r in rows[test_start:]]
    checked = set(quality['overlap_verified_issues'])
    unverified_test = [issue for issue in expected_test if issue not in checked]
    if strict_test_crosscheck and unverified_test:
        raise ValueError('test outcomes not all crosschecked: ' + ','.join(unverified_test[:10]))
    # Existing engine calls each model with the strictly earlier prefix only.
    audit = run_walk_forward(rows, protocol, input_type='unverified_historical_csv')
    if audit['first_test_issue'] != expected_test[0] or audit['last_test_issue'] != expected_test[-1]:
        raise RuntimeError('research engine changed the frozen historical holdout')
    return {
        'schema': 'pl5-v3719-phase3-retrospective-experiment-1',
        'source_quality': quality,
        'experiment': audit,
        'evaluation_issues_all_crosschecked': not unverified_test,
        'evaluation_unverified_issues': unverified_test,
        'evidence_level': 'RETROSPECTIVE_CROSSCHECKED_RESULTS_NOT_BLIND',
        'external_timestamp_verified': False,
        'predictive_advantage': 'NOT_ESTABLISHED',
        'conclusion': 'These are historical post-publication experiments; do not interpret any observed hit as a pre-draw success.',
    }
