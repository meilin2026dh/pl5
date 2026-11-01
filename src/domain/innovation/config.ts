export type InnovationConfig = {
  solver: "rank" | "sample" | "cover" | "entropy";
  rules: "hard" | "soft";
  budget: number;
  shortlist: number;
  digits: string;
  matches: number;
  weights: number[];
  tune: boolean;
  rescue: boolean;
  simulations: number;
  seed: number;
  window: number;
  referenceIssue?: string;
};
export const defaultInnovation: InnovationConfig = {
  solver: "cover",
  rules: "hard",
  budget: 20,
  shortlist: 128,
  digits: "012",
  matches: 3,
  weights: [1, 1, 1, 1],
  tune: false,
  rescue: true,
  simulations: 10000,
  seed: 20261101,
  window: 100,
};
export function validateInnovation(c: InnovationConfig) {
  if (
    !c ||
    typeof c !== "object" ||
    !["rank", "sample", "cover", "entropy"].includes(c.solver) ||
    !["hard", "soft"].includes(c.rules) ||
    typeof c.digits !== "string" ||
    !/^\d{1,8}$/.test(c.digits) ||
    new Set(c.digits).size !== c.digits.length ||
    typeof c.tune !== "boolean" ||
    typeof c.rescue !== "boolean"
  )
    throw Error("覆盖实验配置错误；目标数字池须为1—8个不同数字");
  for (const [k, lo, hi] of [
    ["budget", 1, 100],
    ["shortlist", 16, 256],
    ["matches", 3, 5],
    ["simulations", 100, 100000],
    ["seed", 0, 4294967295],
    ["window", 40, 500],
  ] as const)
    if (!Number.isInteger(c[k]) || c[k] < lo || c[k] > hi)
      throw Error(`覆盖实验${k}须为${lo}—${hi}整数`);
  if (c.tune && c.digits.length < 2)
    throw Error("权重实验至少需要两个目标数字以分离训练和验证结构场景");
  if (c.budget > c.shortlist) throw Error("注数预算不能超过候选短名单");
  if (
    !Array.isArray(c.weights) ||
    c.weights.length !== 4 ||
    c.weights.some(
      (w) => typeof w !== "number" || !Number.isFinite(w) || w < 0 || w > 10,
    ) ||
    !c.weights.some((w) => w > 0)
  )
    throw Error("四项软权重须为0—10，且至少一项大于0");
  if (
    c.referenceIssue !== undefined &&
    (typeof c.referenceIssue !== "string" || !c.referenceIssue.trim())
  )
    throw Error("覆盖实验参考期错误");
}
