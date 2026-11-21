# V3.7.11 research specification

- Build a provenance-preserving candidate grammar bank only from other tasks that have passed source holdout validation; never use target holdout labels for target fitting.
- Compare transfer ordering to uninformed grammar ordering at **identical full-table feature candidate counts** (not identical runtime or full compute complexity). Freeze the specification bank before any target fits.
- A budget-limited recovered model is called *provisional*, only identified relative to the searched sublanguage, and explicitly not usable in production.
- Detect a possibly corrupted training label by one-cell deletion and insist on a unique corrected location and consistent generated full-table completion; diagnosis is not authorization to output a production model.
- Drift monitoring receives observed post-fit labels, requires a fixed prespecified evaluation window and binomial tail under an explicit hypothetical iid error rate, and never purports to anticipate unseen regime changes.
- Predeclare cases and seeds; record independent source/target task truth fingerprints, training/holdout fingerprints, source bank evidence, candidate budget, abstentions, and outcome criteria. Include IID and corruption controls.
- Limit scope to 10x10 synthetic digit operation tables. No lottery advantage claim.
