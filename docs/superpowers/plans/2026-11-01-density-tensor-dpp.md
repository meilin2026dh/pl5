# Density, tensor and DPP implementation plan

Goal: deliver an integrated experimental workbench with frozen density-ratio/TT scores, ordinary split calibration, time-out evaluation and bounded DPP selection.
Architecture: native TypeScript pure models, isolated cancellable Worker, versioned configuration on FilterInput, orange research card. No new dependency. User requested continuation of the previously presented first-stage scope; native execution follows existing project workflow.

## Design decisions

Train/validation/calibration/test are chronological disjoint segments. Raw digit one-hot 50→8→1 MLP learns real versus pure uniform negatives; negatives may collide, priors balanced. Only validation selects uniform mixing weights; AUC/BCE are diagnostics, not evidence of universal absence. TT is a nonnegative locally normalized five-core latent chain, ranks1/2/4, weighted EM with smoothing. Exhaustive score normalization across100000 yields a proper distribution. Ordinary split calibration only; weighted/ACI remain deferred. Calibration target controls omission, budget subset carries no guarantee. DPP is deterministic greedy logdet approximate MAP on bounded top pool, not sampling or global optimality. Input domain intersection is reported separately. Each historical target evaluated with model frozen before calibration; no refit on held-out answers.

Limits: train80–500, validation20–100, calibration20–200, final test10–100; neural5 epochs, EM8 iterations; shortlist16–256, output1–64 and≤pool, rank1/2/4. Full-universe scoring and saved calibration mask. Domain/history revisions cancel stale work. Report copy includes full input and result; output load/undo preserves previous conditions.

## Tasks

- [x] Domain tests RED: normalized TT and learned dependence, density deterministic/finite, exact tied AUC, DPP unique and monotonic logdet, conformal boundary, time splits/future invariance and caps.
- [x] Implement models in src/domain/advanced/models.ts and config/engine.ts; test GREEN.
- [x] Integrate src/components/AdvancedLab.tsx and worker, FilterInput validation and Workbench; UI tests for cancellation/stale reports/load undo.
- [x] Full tests/types/build, actual browser workflow and independent review; fix findings.
- [x] Detailed Obsidian research receipts, commit and GitHub sync with matching tree.

Review focus: negative collisions allowed; TT zero counts smooth; constant scores preserve ties; empty source gives explicit error; budget subset never inherits calibrated coverage.

实施收据见../../research/discovery-lab.md；取消实际页面证据未确认，交互测试通过。
