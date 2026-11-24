# V3.7.64 — Exact equivalent signed-filter minimization

INTERNAL/AI_AUTHORED. One fixed experiment, no new filter predicates. V3.7.63 showed conditional greedy order nearly attains the modeled optimum when all 12 literals are compulsory. This experiment tests whether *removing redundant constraints* instead of refining order reduces the number of checks while preserving identical candidate membership.

## Hypothesis and exact criterion

For a full truth signature s let A be its nonempty atom. Any conjunction B formed by dropping literals from s contains A. Therefore B=A if and only if |B|=|A|. Using the frozen ternary count vector from V3.7.63, examine every one of 2^12=4096 sub-conjunctions for each of the 893 nonempty complete atoms with 1<=K<=100. No historical inputs are opened. Candidate membership and count are fixed, not optimized across atoms.

Two exact objectives are independently evaluated: minimum number of literals, with minimum modeled cost as tie-break; and minimum weighted short-circuit cost, with minimum literal count as tie-break. Final ties use ascending ternary state ID. The existing exact Bellman ordering is used for each feasible subset, so the second objective is a global optimum in the stated subset-and-order search space. The baseline is a deterministic reverse-index deletion pass followed by the same optimal ordering; compare also the prior full-conjunction optimal order. A deletion rejected at a given step cannot become feasible after dropping further constraints, because the retained set only grows.

Use the two pre-existing cost models (unit and heterogeneous abstract); no fitting, no selection based on historical coverage. Count every subset, including empty and full subsets. Verify independent bitmap membership and cost for all four reported alternatives per atom, and independently enumerate every subset and every permutation on a small synthetic four-rule domain. Report aggregate costs, literal counts, number of improved atoms, and exact ledger hashes. Planning overhead excluded; no wall-clock or historical coverage claim.

## Reproduction and acceptance

`python docs/research/experiments/equivalent_rule_minimization_v3764.py`

Three tests: exhaustive toy oracle, empty atom rejection, full-domain equivalence and objective check. Windows and Ubuntu Python 3.12 targeted CI required. Separate application CI is not waived. V3.7.63 evidence-head CI 45395883982 and 45395883928 passed, but earlier recurrent innovation test timeout remains part of failure lineage. PR #11 has 5 successful and PR #13 has 10 successful returned workflows; Issue #12 remains open. Main SHA c0e38040ec5f389d6444e64b90e7adc42adfca62 at audit start. No main or original data/hash modifications, no merge.

## Decision rule

Report zero benefit if no equivalent reduction exists. If benefit is small or greedy is close, retain exact search as an offline reference rather than adopting it as default. Any real runtime benefit requires a separate workload benchmark including planning overhead. Do not infer historical coverage improvement: all alternatives preserve the same candidate sets.
