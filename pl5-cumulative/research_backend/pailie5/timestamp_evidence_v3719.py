"""Offline RFC3161 timestamp request/verification for an unchanged seal packet.

The TSA must be a trusted third party supplied by the operator.  Creating a
request is NOT receiving a timestamp.  Successful signature verification does
not by itself establish a pre-draw prediction: authoritative draw publication
cutoff evidence is needed separately.
"""
from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from .prospective_validation_v3719 import read_evidence


def make_request(packet_path: Path, query_path: Path) -> dict:
    read_evidence(packet_path, 'seal')
    target = Path(query_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError('timestamp request output exists; will not overwrite')
    # The query must be DER, not a copied JSON record.
    try:
        completed = subprocess.run(['openssl', 'ts', '-query', '-data', str(packet_path),
                                    '-sha256', '-cert', '-out', str(target)],
                                   text=True, capture_output=True, check=False, timeout=30)
        if completed.returncode != 0:
            raise ValueError('openssl ts -query failed: ' + completed.stderr[-400:])
        return {'timestamp_request': str(target), 'seal_file_sha256':sha256(Path(packet_path).read_bytes()).hexdigest(),
                'tsa_response_received':False,'independent_timestamp_verified':False,
                'instruction':'Send the .tsq binary to a trusted RFC3161 TSA, retain its .tsr reply and trusted CA certificate chain.'}
    except Exception:
        target.unlink(missing_ok=True)
        raise


def verify_response(packet_path: Path, response_path: Path, trusted_ca: Path) -> dict:
    read_evidence(packet_path, 'seal')
    for name, path in [('TSA reply', response_path),('trusted CA chain',trusted_ca)]:
        if not Path(path).is_file():
            raise ValueError(f'{name} file not found')
    args = ['openssl','ts','-verify','-data',str(packet_path),'-in',str(response_path),
            '-CAfile',str(trusted_ca)]
    verified = subprocess.run(args, text=True, capture_output=True, timeout=30, check=False)
    if verified.returncode != 0:
        raise ValueError('RFC3161 signature or message imprint verification FAILED: ' + verified.stderr[-400:])
    result = subprocess.run(['openssl','ts','-reply','-in',str(response_path),'-text'],
                            text=True, capture_output=True, timeout=30, check=False)
    if result.returncode != 0:
        raise ValueError('RFC3161 reply could not be parsed: ' + result.stderr[-400:])
    matches = re.findall(r'^Time stamp:\s*(.+?)\s*$',result.stdout,flags=re.MULTILINE|re.IGNORECASE)
    if len(matches) != 1:
        raise ValueError('cannot uniquely determine signed timestamp time')
    ts = matches[0]
    # OpenSSL prints a human-readable GMT time in the reply.
    try:
        issued = datetime.strptime(ts,'%b %d %H:%M:%S %Y GMT').replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError('unrecognized signed RFC3161 time: '+ts) from exc
    return {'signature_and_message_imprint_valid':True,
            'signed_timestamp_utc':issued.isoformat(),
            'seal_file_sha256':sha256(Path(packet_path).read_bytes()).hexdigest(),
            'evidence_level':'RFC3161_TIMESTAMP_VALIDATED_NO_DRAW_CUTOFF_VERIFICATION',
            'predraw_status':'NOT_ESTABLISHED_WITHOUT_INDEPENDENT_DRAW_PUBLICATION_EVIDENCE',
            'trusted_ca_supplied_by_operator':True}
