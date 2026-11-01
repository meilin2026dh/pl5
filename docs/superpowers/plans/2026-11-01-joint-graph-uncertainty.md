# Joint sequence, graph and uncertainty implementation

User explicitly requested implementation of all four researched directions. Native TypeScript/Worker execution; prior Obsidian topic15 is the research brief. No additional dependencies or automatic betting.

- [x] TDD domain models: trainable joint autoregressive attention, trained graph-level classifier with training-only position-digit cooccurrence, contrastive masked-view encoder with explicit artificial task; verify gradients/causality/determinism.
- [x] Bayesian three-state uncertainty: simultaneous conservative marginal credible intervals, practical delta and abstention; never kill from low information. Report posterior not frequentist FDR.
- [x] Integrate four scorer options in existing discovery config/Worker/UI, saved parameters and folded replay. Plain split calibration and DPP subset remain distinct.
- [x] Full verification, independent implementation review, actual browser scenarios, detailed Obsidian notes and matching GitHub source tree.

Constraints: joint autoregression length5 with BOS and strict prefix; no actual future-period features. Graph edges trained only on training segment, candidate graph preserves position identity. Contrastive positives are same sample and masked view; other historical samples are representation negatives, not alleged abnormal draws. Continuous scores normalized over100000 for research probability, not predictive evidence. Uncertainty uses train segment only and independent decision softness. New neural modes cap training200, train3 epochs joint/graph and contrastive3; inference bounded by100000, prefix memoization. Exact parameter/version reports.

实施、实际结果和限制见../../research/joint-graph-uncertainty.md。
