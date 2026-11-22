# PL5 V3.7.28 cumulative research archive — verified supplementary parts

This directory stores **5,451 files** that were missing from `main/pl5-cumulative/` at the V3.7.28 audit cutoff. They are preserved as **35 ZIP parts** in `parts/`, not as 5,451 separate Git paths. The 910 previously synchronized files remain in `pl5-cumulative/`.

## Contents

- `parts/pl5_v3728_missing_safe_000.zip` … `_034.zip` — 35 actual binary Git blobs, total 5,451 archived files.
- `PL5_V3728_Public_Upload_Selected.csv` — exact paths, byte lengths, and SHA256 for all 5,451 entries.
- `parts_verification.json` — ZIP SHA256, Git Blob SHA1, size, and member count for each of the 35 parts.
- `restore_archives.py` — independently tested verification and extraction tool (Python standard library only).

## Recover on another computer

```bash
git clone https://github.com/meilin2026dh/pl5.git
cd pl5
git fetch origin archive/v3728-research-artifacts-parts
git switch --track origin/archive/v3728-research-artifacts-parts
python archive/v3728/restore_archives.py
python archive/v3728/restore_archives.py --restore
```

The first invocation verifies 35 ZIP files and each of the 5,451 embedded entries against the published manifest. The second expands them into `pl5-cumulative/` after confirming no existing file would be overwritten with different bytes.

## Important boundaries

The original cumulative V3.7.28 archive contains 6,400 paths. Of these, 910 were previously synchronized, 5,451 are in the ZIP parts here, and **39 are not published** because they may contain private challenge answers, SQLite data, or source-rights questions. To have a lossless 6,400-file backup, keep the source `PL5_V3728_Research_Full.zip` and store the 39 held items in an access-controlled **private** archive.

This is a provenance/archive upload, not a claim of successful Windows `D:\\pl5` deployment, independent blind testing, or prediction advantage. Prior versions of the experiment should not be silently reinterpreted.
