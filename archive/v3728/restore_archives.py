#!/usr/bin/env python3
"""Verify and optionally restore the public PL5 V3.7.28 archive ZIP parts.

No private challenge labels, keys, SQLite datasets, or held-back files are in these parts.
Run at the repository root. Requires only Python 3.10+ standard library.
"""
import argparse
import csv
import hashlib
import io
import sys
import zipfile
from pathlib import Path, PurePosixPath


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, default=Path("."), help="Local PL5 git checkout")
    ap.add_argument("--restore", action="store_true", help="Write verified missing files into pl5-cumulative/")
    args = ap.parse_args()
    repo = args.repo.resolve()
    root = repo / "archive" / "v3728"
    manifest = root / "PL5_V3728_Public_Upload_Selected.csv"
    if not manifest.is_file():
        sys.exit(f"Missing verified selection manifest: {manifest}")
    with manifest.open(newline="", encoding="utf-8-sig") as handle:
        expected = {
            row["path"]: (row["sha256"].lower(), int(row["size_bytes"]))
            for row in csv.DictReader(handle)
        }
    if len(expected) != 5451:
        sys.exit(f"Unexpected manifest count: {len(expected)} (expected 5451)")

    parts = sorted((root / "parts").glob("pl5_v3728_missing_safe_*.zip"))
    if len(parts) != 35:
        sys.exit(f"Unexpected ZIP part count: {len(parts)} (expected 35)")
    seen = set()
    pending = []
    dst_root = repo / "pl5-cumulative"
    for part in parts:
        with zipfile.ZipFile(part) as archive:
            if archive.testzip() is not None:
                sys.exit(f"Corrupt ZIP part: {part}")
            for entry in archive.infolist():
                if entry.is_dir():
                    continue
                member = entry.filename
                path = PurePosixPath(member)
                if (
                    member not in expected
                    or member in seen
                    or path.is_absolute()
                    or ".." in path.parts
                    or not path.parts
                ):
                    sys.exit(f"Unexpected, duplicated or unsafe member: {member}")
                data = archive.read(entry)
                sha, size = expected[member]
                if len(data) != size or hashlib.sha256(data).hexdigest() != sha:
                    sys.exit(f"SHA256/size mismatch: {member}")
                target = dst_root.joinpath(*path.parts)
                # Reject symbolic-link traversal, even if the destination is inside the checkout.
                for ancestor in (target, *target.parents):
                    if ancestor == repo.parent:
                        break
                    if ancestor.is_symlink():
                        sys.exit(f"Refusing symlink destination: {target}")
                if target.exists() and target.read_bytes() != data:
                    sys.exit(f"Existing file differs from archive: {target}")
                seen.add(member)
                if args.restore and not target.exists():
                    pending.append((target, data))

    if seen != expected.keys():
        sys.exit(f"Member coverage mismatch: missing={len(expected.keys() - seen)}")
    print(f"Verified {len(seen)} archive entries across {len(parts)} parts; SHA256 matched.")
    if args.restore:
        for target, data in pending:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        print(f"Restored {len(pending)} missing files to {dst_root}.")
    else:
        print("Verification only. Use --restore to extract into pl5-cumulative/.")


if __name__ == "__main__":
    main()