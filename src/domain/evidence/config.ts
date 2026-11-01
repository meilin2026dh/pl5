export type EvidenceConfig = {
  window: number;
  monitor: number;
  checks: number;
  resamples: number;
  alpha: number;
  tune: number;
  calibration: number;
  test: number;
  budget: number;
  seed: number;
  referenceIssue?: string;
};
export const defaultEvidence: EvidenceConfig = {
  window: 100,
  monitor: 120,
  checks: 3,
  resamples: 199,
  alpha: 0.05,
  tune: 40,
  calibration: 40,
  test: 60,
  budget: 20,
  seed: 20261101,
};
export function validateEvidence(c: EvidenceConfig) {
  if (!c || typeof c !== "object" || Array.isArray(c))
    throw Error("证据体检配置错误");
  for (const [k, lo, hi] of [
    ["window", 40, 500],
    ["monitor", 40, 500],
    ["checks", 1, 5],
    ["resamples", 99, 999],
    ["tune", 20, 100],
    ["calibration", 20, 100],
    ["test", 30, 200],
    ["budget", 1, 100],
    ["seed", 0, 4294967295],
  ] as const)
    if (!Number.isInteger(c[k]) || c[k] < lo || c[k] > hi)
      throw Error(`证据体检${k}须为${lo}—${hi}整数`);
  if (
    typeof c.alpha !== "number" ||
    !Number.isFinite(c.alpha) ||
    c.alpha < 0.001 ||
    c.alpha > 0.1
  )
    throw Error("证据显著性须为0.001—0.1");
  if (
    c.referenceIssue !== undefined &&
    (typeof c.referenceIssue !== "string" || !c.referenceIssue.trim())
  )
    throw Error("证据参考期错误");
}
