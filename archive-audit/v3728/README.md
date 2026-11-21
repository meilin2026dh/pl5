# PL5 V3.7.28 archive synchronization status

This branch records a *partial* audit-only submission. It is NOT a full backup of the historical archive.

- Files in V3.7.28 cumulative archive: **6,400**.
- Existing source files inside `pl5-cumulative/` on `main`: **910**.
- Archive entries not present at the corresponding `pl5-cumulative/` paths: **5,490**.
- Entries in an initial upload-candidate selection: **5,451**.
- Entries intentionally excluded pending separate privacy/provenance review: **39**.
- This branch currently adds ONLY the audit documents and selection/verification instructions; it does NOT contain the 5,451 missing file payloads.

The 39 held files include private challenge answer JSON, SQLite data, unverified draw transcriptions, and registry records. The 5,451 candidates have not passed a comprehensive secret/data rights review and should not be pushed wholesale to a public repository without checking.

Prioritize reproducible manifests, then public research evidence, while keeping private challenge keys and labels outside public Git history. GitHub Actions success and a successful audit do not establish lottery predictive advantage.

Do not merge this branch as a substitute for uploading the archive files.
