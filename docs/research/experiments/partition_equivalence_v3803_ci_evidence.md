# V3.8.3 partition-equivalence regression evidence (2026-11-26)

Source: INTERNAL/AI_AUTHORED. Scope: synthetic finite-set validation only.

## Verified immutable revision

- Tested revision: `9ad285334328557b2e5b70e7dcc00cd980826a54`
- Test command: `python docs/research/experiments/partition_equivalence_v3803.py`
- [Specialized CI run 45770151158](https://github.com/meilin2026dh/pl5/actions/runs/45770151158): success.
- Windows job 139740574923 and Ubuntu job 139740575165: both successful, including the named test step, four tests each.
- [Application checks 45770151233](https://github.com/meilin2026dh/pl5/actions/runs/45770151233): success.

Read both job logs and compared the complete structured result. The V3803_PARTITION_EQUIVALENCE_JSON payloads agree.

| Domain size | Partitions | Ordered partition pairs | Same class count, inequivalent | Same size histogram, inequivalent | Strict refinement |
|---:|---:|---:|---:|---:|---:|
|1|1|1|0|0|0|
|2|2|4|0|0|2|
|3|5|25|6|6|14|
|4|15|225|72|48|90|
|5|52|2704|900|500|612|
|6|203|41209|13310|6860|4536|

44,168 ordered pairs in total. All witness checks against the independent pair-relation oracle passed; the 100,000-element synthetic relabel and single-point mutation test also passed.

## Interpretation and limitations

The gate checks partition equivalence for a shared nonempty indexed domain with ordinary hashable labels; class counts and histograms alone are insufficient. This closes the pending cross-platform validation of the gate at the tested revision, not at this evidence-only revision. No measured runtime improvement, new filtering rule, candidate compression improvement, or historical coverage improvement is established. Synthetic tests are not independent external validation. Do not treat structural equivalence or rank reduction alone as an engineering performance gain.

PR #11 and #13 remain open drafts; their current heads have respectively 5/5 and 10/10 successful reported workflow runs. Issue #12 remains open. This evidence changes no production code or historical data.
