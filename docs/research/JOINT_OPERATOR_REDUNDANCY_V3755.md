# V3.7.55 — exact joint redundancy of three operator families

## Frozen experiment

One bounded hypothesis: the ten existing additional binary filters are not necessarily all necessary for their joint structural separation contribution. No new filter, threshold or historical data. All structural inputs INTERNAL/AI_AUTHORED. Baseline: 58 V3.7.40 static masks, frozen manifest SHA256 `625ab5ee6e7dd932f3e64b0d0f294763e21aa541ae5bcf69b2c7f987d65f7499`. Parent `39f1e687bc34e34212fd3c7d92028b56cb461c73` (PR #22).

## Exact finite-domain certificate

For each pair of IDs sharing the same 58-bit baseline signature, let D be their XOR difference over the ten new binary predicates. A coalition S distinguishes a pair iff D intersects S. For histogram h of D, define V(S) = sum of h(D) over D intersecting S. Enumerate all 1024 coalitions using subset zeta transform; independently verify the histogram by directly enumerating all old-indistinguishable pairs, and all coalition values by direct sums. Independently regroup original signatures on every family coalition, singleton, leave-one-out and optimal-frontier coalition.

An exact equivalent subset must attain V(full), since the separated-pair set is monotone in S and is contained in the full set. Report every minimum equivalent subset and every cardinality-optimal coalition (ties retained). Each rule's exclusive contribution is h(singleton), independently checked against V(full)-V(full without the rule), with a concrete old-signature witness where positive. Verify that witness using original 58 masks, trial factor division and an independent unordered-digit-pair expansion of the spectral rule.

The exact Shapley contribution is sum over D containing rule i of h(D)/|D|. Rational arithmetic preserves efficiency. Project D onto three disjoint operator families (6 modular predicates, 3 prime-factor predicates, 1 spectral predicate) and repeat the eight-coalition analysis. Family Shapley allocates credit to whole families; it need not equal a sum of rule-level Shapley credits.

## Reproduction and constraints

From root: `python docs/research/experiments/joint_operator_redundancy_v3755.py`. Three unittest cases cover a duplicate rule, family projection and the full domain. Ubuntu and Windows Python 3.12 targeted CI, 15-minute maximum per job. No historical observations or new fitting, no production changes.

Preserve earlier regressions: PR #11/#13 remain drafts, Issue #12 remains open. Previous intermittent application timeout remains a known failure mode. Checked existing targeted/application CI for PR #22 report head, passed; previous PR #11 and #13 head workflows also passed. Main remains `c0e38040ec5f389d6444e64b90e7adc42adfca62`. No independent external acceptance is implied.

Structural pair separation is not candidate compression, historical coverage, historical deletion rate or measured cost. Those require separate evaluations. Do not treat an empty candidate intersection as a successful compression. No main changes, data/hash changes, or automatic merge.
