import { validatePotential } from "./potential";
import { filterMethods, scoreMethods, type ResearchConfig } from "./types";
const finite = (v: unknown, lo: number, hi: number) =>
  typeof v === "number" && Number.isFinite(v) && v >= lo && v <= hi;
const integer = (v: unknown, lo: number, hi: number) =>
  finite(v, lo, hi) && Number.isInteger(v);
export function validateResearchConfig(
  value: unknown,
): asserts value is ResearchConfig {
  if (!value || typeof value !== "object" || Array.isArray(value))
    throw new Error("实验参数格式错误");
  const c = value as ResearchConfig;
  if (
    ![...filterMethods, ...scoreMethods, "auto", "greedy", "preset"].includes(
      c.method,
    ) ||
    !filterMethods.includes(c.family)
  )
    throw new Error("实验方法不合法");
  if (
    !integer(c.window, 1, 100000) ||
    !integer(c.seed, 0, 4294967295) ||
    !integer(c.windows, 2, 20) ||
    !integer(c.folds, 1, 5) ||
    !integer(c.validationSize, 1, 200) ||
    !integer(c.maxSteps, 1, 8)
  )
    throw new Error("实验窗口、种子或验证设置超出范围");
  if (
    !finite(c.parameter, 0, 100000) ||
    !finite(c.retain, 0.00001, 1) ||
    !finite(c.targetCoverage, 0, 1) ||
    !["inclusive", "seeded"].includes(c.ties) ||
    !["lift60", "cov90", "strict"].includes(c.selection) ||
    !["A", "B", "C", "D", "E", "F"].includes(c.preset)
  )
    throw new Error("实验参数或选择策略不合法");
  if (
    c.referenceIssue !== undefined &&
    (typeof c.referenceIssue !== "string" || !c.referenceIssue.trim())
  )
    throw new Error("实验参考期格式错误");
  if (c.method === "auto" || c.method === "greedy")
    if (c.window - c.folds * c.validationSize < 10)
      throw new Error("历史不足：滚动验证后至少需要10期训练记录");
  if (c.method === "potential") validatePotential(c.potential, c.window);
  const method = c.method === "auto" ? c.family : c.method;
  if (method === "hotcold" && !integer(c.parameter, 1, 10))
    throw new Error("Top K须为1至10整数");
  if (
    ["omission", "multiset", "samePosition", "positionNeighbor"].includes(
      method,
    ) &&
    !integer(
      c.parameter,
      method === "multiset" ? 1 : 0,
      method === "samePosition" || method === "positionNeighbor" ? 5 : 100000,
    )
  )
    throw new Error("实验计数阈值超出范围");
  if (
    [
      "bayes",
      "markov",
      "sumQuantile",
      "spanQuantile",
      ...filterMethods.filter((m) => m.endsWith("Frequency")),
    ].includes(method) &&
    !finite(c.parameter, 0, 1)
  )
    throw new Error("概率、频率或分位比例须在0至1之间");
  if (method === "sumSigma" && !finite(c.parameter, 0, 10))
    throw new Error("标准差倍数须在0至10之间");
}
