export type ProbabilityConfig = {
  train: number;
  calibration: number;
  test: number;
  target: number;
  budget: number;
  strength: number;
  radius: number;
  seed: number;
  referenceIssue?: string;
  uniformOnly?: boolean;
};
export const defaultProbability: ProbabilityConfig = {
  train: 500,
  calibration: 100,
  test: 100,
  target: 0.9,
  budget: 1000,
  strength: 10,
  radius: 0.01,
  seed: 20261101,
};
export function validateProbability(c: ProbabilityConfig) {
  if (!c || typeof c !== "object" || Array.isArray(c))
    throw Error("概率实验配置错误");
  for (const [k, lo, hi] of [
    ["train", 100, 1000],
    ["calibration", 20, 500],
    ["test", 30, 500],
    ["budget", 1, 100000],
    ["seed", 0, 4294967295],
  ] as const)
    if (!Number.isInteger(c[k]) || c[k] < lo || c[k] > hi)
      throw Error(`概率实验${k}须为${lo}—${hi}整数`);
  for (const [k, lo, hi] of [
    ["target", 0.5, 0.99],
    ["strength", 0.1, 100],
    ["radius", 0, 5],
  ] as const)
    if (!Number.isFinite(c[k]) || c[k] < lo || c[k] > hi)
      throw Error(`概率实验${k}须为${lo}—${hi}`);
  if (c.uniformOnly !== undefined && typeof c.uniformOnly !== "boolean")
    throw Error("均匀对照开关错误");
  if (
    c.referenceIssue !== undefined &&
    (typeof c.referenceIssue !== "string" || !c.referenceIssue.trim())
  )
    throw Error("概率历史截止期错误");
}
