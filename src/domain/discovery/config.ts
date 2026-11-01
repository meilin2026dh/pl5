export type DiscoveryConfig = {
  train: number;
  validation: number;
  calibration: number;
  test: number;
  rank: 1 | 2 | 4;
  model: "ratio" | "tensor";
  coverage: number;
  pool: number;
  budget: number;
  sigma: number;
  seed: number;
  referenceIssue: string;
};
export const defaultDiscovery: DiscoveryConfig = {
  train: 200,
  validation: 50,
  calibration: 100,
  test: 30,
  rank: 2,
  model: "tensor",
  coverage: 0.9,
  pool: 128,
  budget: 20,
  sigma: 1,
  seed: 20261101,
  referenceIssue: "",
};
export function validateDiscovery(c: DiscoveryConfig) {
  for (const [key, lo, hi] of [
    ["train", 80, 500],
    ["validation", 20, 100],
    ["calibration", 20, 200],
    ["test", 10, 100],
    ["pool", 16, 256],
    ["budget", 1, 64],
    ["seed", 0, 4294967295],
  ] as const)
    if (!Number.isInteger(c[key]) || c[key] < lo || c[key] > hi)
      throw Error(`研究参数${key}超限`);
  if (
    ![1, 2, 4].includes(c.rank) ||
    !["ratio", "tensor"].includes(c.model) ||
    !Number.isFinite(c.coverage) ||
    c.coverage <= 0 ||
    c.coverage >= 1 ||
    !Number.isFinite(c.sigma) ||
    c.sigma < 0.2 ||
    c.sigma > 5 ||
    c.budget > c.pool ||
    typeof c.referenceIssue !== "string"
  )
    throw Error("研究模型/覆盖/预算参数错误");
}
