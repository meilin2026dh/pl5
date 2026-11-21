# PL5 V3.7.28 supplementary archive upload kit

This kit contains 35 ZIP parts with 5,451 selected files from the cumulative archive, an exact SHA256/size manifest, and a verification/restore program. The other 39 files are in a separate holdback report and are NOT contained in the ZIP parts.

**IMPORTANT**: This is an upload-preparation kit, NOT proof of remote GitHub upload. The destination repository is PUBLIC. It is the owner's responsibility to review proprietary/sensitive contents. The included script aborts on common credential signatures, but no pattern scan can guarantee safety.

Preparation on your own computer with Python 3.12+ and git:

1. Clone or update `https://github.com/meilin2026dh/pl5` and ensure the worktree is clean.
2. Put this kit's `parts` next to the CSV and script.
3. Verify without writing: `python PL5_V3728_upload_safe_archives.py --repo PATH_TO_PL5 --parts parts --selection PL5_V3728_Public_Upload_Selected.csv`
4. After review, rerun with `--apply` to copy files to `pl5-cumulative/`. No Git push is performed by the script.
5. Use a new branch, inspect changes, commit, push and open a PR. Do not commit the 39 excluded files.

The hash list is file-specific; 5,451 paths were confirmed to match 35 ZIP parts. This kit does not change the GitHub repository by itself.