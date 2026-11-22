"""PL5 V3.7.28: signed, portable handoff for third-party mathematical tasks.

Signing verifies possession of a private key, *not* that its owner is independent.
No sandbox, third-party identity verification, trusted clock, or external blind
experiment is provided by this module. Keys MUST be created and retained by
separate, independently controlled parties for a future external trial.

Issuer: keygen --private ... --public ...; issue --challenge-public ...
Solver: keygen ..., freeze --challenge-public ... --issuer-attestation ...
Grader: keygen ..., settle --challenge-public ... --challenge-private ...
Audit: verify --challenge-public ... --issuer-attestation ... --solver-dir ...
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research_hard_budget_v3727 import ARMS, _validated_budget, solve as hard_solve, grade as hard_grade
from research_open_grammar_v3725 import _public

PROTOCOL = 'pl5-v3728-signed-blind-handoff-1'
ISSUER = PROTOCOL + ':issuer'
SOLVER = PROTOCOL + ':solver'
GRADER = PROTOCOL + ':grader'
SOURCE_SUBDIRS = ('pailie5', 'autoresearch')
SRC_INCLUDE = ('pyproject.toml', 'research_signed_blind_v3728.py', 'research_hard_budget_v3727.py',
               'research_open_grammar_v3725.py', 'research_external_challenge_v3726.py',
               'benchmark_gate_induction_v3726.py')


def _crypto():
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    except ImportError as exc:
        raise RuntimeError('Install the optional audit dependency: pip install cryptography>=43') from exc
    return InvalidSignature, serialization, Ed25519PrivateKey, Ed25519PublicKey


def _bytes(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _read(path: str | Path) -> dict:
    doc = json.loads(Path(path).read_text('utf-8'))
    if type(doc) is not dict:
        raise ValueError('expected a JSON object')
    return doc


def _restrict_windows_private_acl(path: Path) -> None:
    """Set an explicit, non-inheriting NTFS DACL before any secret bytes exist.

    Only the running account, LOCAL SYSTEM and local Administrators may read the
    key. Fail closed on non-NTFS volumes or when Windows cannot enforce this ACL.
    """
    import csv
    import io
    import re
    import subprocess
    import ctypes
    from ctypes import wintypes

    result = subprocess.run(
        ['whoami.exe', '/user', '/fo', 'csv', '/nh'],
        check=True, capture_output=True, text=True,
    )
    rows = list(csv.reader(io.StringIO(result.stdout.strip())))
    if len(rows) != 1 or len(rows[0]) != 2:
        raise PermissionError('cannot identify Windows account SID')
    sid = rows[0][1].strip()
    if not re.fullmatch(r'S-1-\d+(?:-\d+)+', sid):
        raise PermissionError('invalid Windows account SID')

    # D:P prevents inherited ACEs. No Everyone/Users/Authenticated Users ACE.
    sddl = f'D:P(A;;FA;;;{sid})(A;;FA;;;SY)(A;;FA;;;BA)'
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    convert = advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW
    convert.argtypes = [wintypes.LPCWSTR, wintypes.DWORD,
                        ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]
    convert.restype = wintypes.BOOL
    set_acl = advapi.SetFileSecurityW
    set_acl.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p]
    set_acl.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    descriptor = ctypes.c_void_p()
    if not convert(sddl, 1, ctypes.byref(descriptor), None):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        # DACL_SECURITY_INFORMATION | PROTECTED_DACL_SECURITY_INFORMATION
        if not set_acl(str(path), 0x00000004 | 0x80000000, descriptor):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.LocalFree(descriptor)


def _create(path: str | Path, data: bytes, mode: int = 0o644) -> None:
    path = Path(path)
    if not path.parent.is_dir():
        raise FileNotFoundError(f'output parent directory missing: {path.parent}')
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
    try:
        # On Windows, POSIX mode 0600 is not a security guarantee. Harden the
        # just-created EMPTY file before any private-key material is written.
        if os.name == 'nt' and mode == 0o600:
            _restrict_windows_private_acl(path)
        with os.fdopen(fd, 'wb') as f:
            fd = -1
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        if fd >= 0:
            os.close(fd)
        path.unlink(missing_ok=True)
        raise


def _write_json_new(path: str | Path, data: dict) -> None:
    _create(path, json.dumps(data, indent=2, sort_keys=True,
                             ensure_ascii=False).encode('utf-8') + b'\n')


def keygen(private: str | Path, public: str | Path) -> dict:
    _, serial, EdPriv, _ = _crypto()
    private, public = Path(private), Path(public)
    if private.resolve() == public.resolve():
        raise ValueError('key paths must differ')
    if private.exists() or public.exists():
        raise FileExistsError('refuse overwriting a key')
    secret = EdPriv.generate()
    private_pem = secret.private_bytes(serial.Encoding.PEM, serial.PrivateFormat.PKCS8,
                                       serial.NoEncryption())
    public_pem = secret.public_key().public_bytes(serial.Encoding.PEM,
                                                  serial.PublicFormat.SubjectPublicKeyInfo)
    _create(private, private_pem, 0o600)
    _create(public, public_pem, 0o644)
    return {'fingerprint_sha256': _fingerprint(public),
            'private_key_not_to_distribute': str(private), 'public_key': str(public)}


def _fingerprint(public: str | Path) -> str:
    _, serial, _, EdPub = _crypto()
    key = serial.load_pem_public_key(Path(public).read_bytes())
    if not isinstance(key, EdPub):
        raise ValueError('expected Ed25519 public key')
    return _sha(key.public_bytes(serial.Encoding.Raw, serial.PublicFormat.Raw))


def _sign(body: dict, private: str | Path, schema: str) -> dict:
    _, serial, EdPriv, _ = _crypto()
    secret = serial.load_pem_private_key(Path(private).read_bytes(), password=None)
    if not isinstance(secret, EdPriv):
        raise ValueError('expected Ed25519 private key')
    return {'schema': schema, 'payload': body,
            'signature_alg': 'Ed25519',
            'signature_b64': base64.b64encode(secret.sign(_bytes(body))).decode('ascii')}


def _verify(path: str | Path, public_key: str | Path, schema: str) -> dict:
    InvalidSig, serial, _, EdPub = _crypto()
    envelope = _read(path)
    if set(envelope) != {'schema', 'payload', 'signature_alg', 'signature_b64'} or \
       envelope['schema'] != schema or envelope['signature_alg'] != 'Ed25519':
        raise ValueError('invalid attestation envelope')
    key = serial.load_pem_public_key(Path(public_key).read_bytes())
    if not isinstance(key, EdPub):
        raise ValueError('wrong public key format')
    try:
        signature = base64.b64decode(envelope['signature_b64'], validate=True)
        key.verify(signature, _bytes(envelope['payload']))
    except (InvalidSig, ValueError) as exc:
        raise ValueError('signature does not verify') from exc
    return envelope['payload']


def code_inventory(backend_root: str | Path) -> dict:
    """Pins the available Python research source, not the whole executable environment."""
    root = Path(backend_root).resolve()
    files = {}
    for subdir in SOURCE_SUBDIRS:
        d = root / subdir
        if not d.is_dir():
            raise FileNotFoundError(d)
        for f in d.rglob('*.py'):
            if '__pycache__' not in f.parts:
                files[f.relative_to(root).as_posix()] = _sha(f.read_bytes())
    for rel in SRC_INCLUDE:
        p = root / rel
        if not p.is_file():
            raise FileNotFoundError(p)
        files[rel] = _sha(p.read_bytes())
    return {'sha256': _sha(_bytes(files)), 'count': len(files), 'files': files}


def _ensure_code(backend_root: str | Path, digest: str, count: int) -> dict:
    inventory = code_inventory(backend_root)
    if inventory['sha256'] != digest or inventory['count'] != count:
        raise ValueError('model source-tree hash mismatch')
    return inventory


def _now_untrusted() -> str:
    return datetime.now(timezone.utc).isoformat()


def issue(challenge_public: str | Path, backend_root: str | Path,
          issuer_private: str | Path, issuer_public: str | Path,
          out: str | Path, budget_ms: int) -> dict:
    """Issuer fixes a challenge, code digest and cost rule before solving."""
    _validated_budget(budget_ms)
    pub = _public(challenge_public)
    # Fail closed if issuer tries to use an unrelated signing key.
    _, serial, EdPriv, _ = _crypto()
    secret = serial.load_pem_private_key(Path(issuer_private).read_bytes(), password=None)
    expected_public = secret.public_key().public_bytes(serial.Encoding.Raw, serial.PublicFormat.Raw)
    public_pem = serial.load_pem_public_key(Path(issuer_public).read_bytes())
    actual_public = public_pem.public_bytes(serial.Encoding.Raw, serial.PublicFormat.Raw)
    if actual_public != expected_public:
        raise ValueError('issuer public/private key mismatch')
    code = code_inventory(backend_root)
    body = {
        'protocol': PROTOCOL, 'task_id': pub['task_id'],
        'challenge_public_file_sha256': _sha(Path(challenge_public).read_bytes()),
        'challenge_public_object_sha256': _sha(_bytes(pub)),
        'holdout_commitment': pub['holdout_commitment'],
        'model_source_tree_sha256': code['sha256'],
        'model_source_file_count': code['count'],
        'allowed_budget_ms_per_model': budget_ms,
        'arms': list(ARMS), 'portfolio_max_budget_multiplier': 2,
        'report_all_tasks_denominator': True,
        'score_rule': 'exact holdout cells; failures/timeouts/abstentions retain denominator',
        'issuer_public_key_fingerprint_sha256': _fingerprint(issuer_public),
        'declared_utc_untrusted': _now_untrusted(),
        'claimed_external_independence': False,
        'trusted_timestamp_verified': False,
        'lottery_predictive_advantage': 'NOT_ESTABLISHED',
    }
    _write_json_new(out, _sign(body, issuer_private, ISSUER))
    return {'attestation': str(out), 'issuer_key_fingerprint': _fingerprint(issuer_public),
            'source_files_pinned': code['count'], 'external_independence_verified': False}


def verify_issue(challenge_public: str | Path, backend_root: str | Path,
                 issuer_attestation: str | Path, issuer_public: str | Path) -> dict:
    pub = _public(challenge_public)
    item = _verify(issuer_attestation, issuer_public, ISSUER)
    if (item.get('protocol') != PROTOCOL or item.get('task_id') != pub['task_id'] or
        item.get('issuer_public_key_fingerprint_sha256') != _fingerprint(issuer_public) or
        item.get('challenge_public_file_sha256') != _sha(Path(challenge_public).read_bytes()) or
        item.get('challenge_public_object_sha256') != _sha(_bytes(pub)) or
        item.get('holdout_commitment') != pub['holdout_commitment'] or
        item.get('arms') != list(ARMS) or item.get('portfolio_max_budget_multiplier') != 2 or
        item.get('report_all_tasks_denominator') is not True or
        item.get('claimed_external_independence') is not False):
        raise ValueError('issuer protocol/challenge mismatch')
    budget = item.get('allowed_budget_ms_per_model')
    _validated_budget(budget)
    _ensure_code(backend_root, item['model_source_tree_sha256'], item['model_source_file_count'])
    return item


def _solver_evidence(root: Path) -> dict:
    files = ['protocol.json', 'solver_manifest.json']
    manifest = _read(root / 'solver_manifest.json')
    for arm in ARMS:
        row = manifest['arms'][arm]
        if row['status'] == 'COMPLETED':
            files.extend(f'{arm}/{x}' for x in ('fit.json', 'freeze.json', 'worker_receipt.json'))
        elif row['status'] not in ('TIMED_OUT', 'FAILED'):
            raise ValueError('unknown solver state')
    return {name: _sha((root/name).read_bytes()) for name in files}


def freeze(challenge_public: str | Path, backend_root: str | Path,
           issuer_attestation: str | Path, issuer_public: str | Path,
           solver_private: str | Path, solver_public: str | Path,
           out: str | Path) -> dict:
    item = verify_issue(challenge_public, backend_root, issuer_attestation, issuer_public)
    # Explicitly bind the solving key to a distinct public key.
    _, serial, _, _ = _crypto()
    private_key = serial.load_pem_private_key(Path(solver_private).read_bytes(), password=None)
    if private_key.public_key().public_bytes(serial.Encoding.Raw, serial.PublicFormat.Raw) != \
       serial.load_pem_public_key(Path(solver_public).read_bytes()).public_bytes(serial.Encoding.Raw, serial.PublicFormat.Raw):
        raise ValueError('solver public/private key mismatch')
    output = Path(out)
    hard_solve(challenge_public, output, item['allowed_budget_ms_per_model'])
    evidence = _solver_evidence(output)
    # Never use test labels in the solver. The receipt binds byte-level evidence.
    before = {'protocol': PROTOCOL, 'task_id': item['task_id'],
              'issuer_attestation_sha256': _sha(Path(issuer_attestation).read_bytes()),
              'issuer_public_key_fingerprint_sha256': _fingerprint(issuer_public),
              'solver_public_key_fingerprint_sha256': _fingerprint(solver_public),
              'source_tree_sha256': item['model_source_tree_sha256'],
              'budget_ms_per_model': item['allowed_budget_ms_per_model'],
              'solver_evidence_file_sha256': evidence,
              'declared_utc_untrusted': _now_untrusted(),
              'external_independence_verified': False, 'trusted_timestamp_verified': False}
    # If source code changes during execution reject the whole execution;
    # leaves partial evidence and cannot produce a signed frozen receipt.
    _ensure_code(backend_root, item['model_source_tree_sha256'], item['model_source_file_count'])
    _write_json_new(output/'solver_signed_receipt.json', _sign(before, solver_private, SOLVER))
    return {'out': str(output), 'statuses': {arm:_read(output/'solver_manifest.json')['arms'][arm]['status'] for arm in ARMS},
            'external_independence_verified': False}


def verify_freeze(challenge_public: str | Path, backend_root: str | Path,
                  issuer_attestation: str | Path, issuer_public: str | Path,
                  solver_public: str | Path, out: str | Path) -> dict:
    item = verify_issue(challenge_public, backend_root, issuer_attestation, issuer_public)
    root = Path(out)
    receipt = _verify(root/'solver_signed_receipt.json', solver_public, SOLVER)
    evidence = _solver_evidence(root)
    if (receipt.get('protocol') != PROTOCOL or receipt.get('task_id') != item['task_id'] or
        receipt.get('issuer_attestation_sha256') != _sha(Path(issuer_attestation).read_bytes()) or
        receipt.get('issuer_public_key_fingerprint_sha256') != _fingerprint(issuer_public) or
        receipt.get('solver_public_key_fingerprint_sha256') != _fingerprint(solver_public) or
        receipt.get('source_tree_sha256') != item['model_source_tree_sha256'] or
        receipt.get('budget_ms_per_model') != item['allowed_budget_ms_per_model'] or
        receipt.get('solver_evidence_file_sha256') != evidence or
        receipt.get('external_independence_verified') is not False):
        raise ValueError('solver signed receipt mismatches frozen evidence')
    return receipt


def settle(challenge_public: str | Path, challenge_private: str | Path,
           backend_root: str | Path, issuer_attestation: str | Path,
           issuer_public: str | Path, solver_public: str | Path,
           grader_private: str | Path, grader_public: str | Path,
           out: str | Path) -> dict:
    frozen = verify_freeze(challenge_public, backend_root, issuer_attestation,
                           issuer_public, solver_public, out)
    _, serial, _, _ = _crypto()
    pk = serial.load_pem_private_key(Path(grader_private).read_bytes(), password=None)
    if pk.public_key().public_bytes(serial.Encoding.Raw, serial.PublicFormat.Raw) != \
       serial.load_pem_public_key(Path(grader_public).read_bytes()).public_bytes(serial.Encoding.Raw, serial.PublicFormat.Raw):
        raise ValueError('grader keypair mismatch')
    root = Path(out)
    if (root/'grader_signed_receipt.json').exists() or (root/'score.json').exists():
        raise FileExistsError('study already graded')
    scores = hard_grade(challenge_public, challenge_private, root)
    payload = {'protocol': PROTOCOL, 'task_id': frozen['task_id'],
               'solver_signed_receipt_file_sha256': _sha((root/'solver_signed_receipt.json').read_bytes()),
               'score_file_sha256': _sha((root/'score.json').read_bytes()),
               'grader_public_key_fingerprint_sha256': _fingerprint(grader_public),
               'declared_utc_untrusted': _now_untrusted(),
               'task_scores': scores, 'external_independence_verified': False,
               'trusted_timestamp_verified': False,
               'lottery_predictive_advantage': 'NOT_ESTABLISHED'}
    _write_json_new(root/'grader_signed_receipt.json', _sign(payload, grader_private, GRADER))
    return {'task_id': frozen['task_id'], 'scores': scores,
            'authentic_signatures_verified': True,
            'issuer_independence_verified': False}


def verify_settlement(challenge_public: str | Path, backend_root: str | Path,
                      issuer_attestation: str | Path, issuer_public: str | Path,
                      solver_public: str | Path, grader_public: str | Path,
                      out: str | Path) -> dict:
    freeze_receipt = verify_freeze(challenge_public, backend_root, issuer_attestation,
                                   issuer_public, solver_public, out)
    root = Path(out)
    receipt = _verify(root/'grader_signed_receipt.json', grader_public, GRADER)
    if (receipt.get('protocol') != PROTOCOL or receipt.get('task_id') != freeze_receipt['task_id'] or
        receipt.get('grader_public_key_fingerprint_sha256') != _fingerprint(grader_public) or
        receipt.get('solver_signed_receipt_file_sha256') != _sha((root/'solver_signed_receipt.json').read_bytes()) or
        receipt.get('score_file_sha256') != _sha((root/'score.json').read_bytes()) or
        receipt.get('external_independence_verified') is not False):
        raise ValueError('grader receipt mismatch')
    score = _read(root/'score.json')
    if receipt.get('task_scores') != score.get('arms'):
        # Existing v3727 grade returns *arms* and places the same arms in score.json.
        raise ValueError('grade signed contents differ from score file')
    return {'signed_evidence_verified': True,
            'third_party_identity_verified': False,
            'third_party_clock_verified': False,
            'actual_external_blind_study_verified': False,
            'lottery_predictive_advantage': 'NOT_ESTABLISHED'}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('keygen'); p.add_argument('--private',required=True); p.add_argument('--public',required=True)
    p = sub.add_parser('issue')
    p.add_argument('--challenge-public',required=True);p.add_argument('--backend-root',required=True)
    p.add_argument('--issuer-private',required=True);p.add_argument('--issuer-public',required=True)
    p.add_argument('--out',required=True);p.add_argument('--budget-ms',type=int,required=True)
    p = sub.add_parser('freeze')
    for name in ('challenge-public','backend-root','issuer-attestation','issuer-public','solver-private','solver-public','out'):
        p.add_argument('--'+name,required=True)
    p = sub.add_parser('settle')
    for name in ('challenge-public','challenge-private','backend-root','issuer-attestation','issuer-public','solver-public','grader-private','grader-public','out'):
        p.add_argument('--'+name,required=True)
    p = sub.add_parser('verify')
    for name in ('challenge-public','backend-root','issuer-attestation','issuer-public','solver-public','grader-public','out'):
        p.add_argument('--'+name,required=True)
    a = vars(ap.parse_args()); cmd = a.pop('command'); a = {k.replace('-','_'):v for k,v in a.items()}
    r = {'keygen':keygen,'issue':issue,'freeze':freeze,'settle':settle,'verify':verify_settlement}[cmd](**a)
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
