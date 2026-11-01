import type { PosteriorConfig } from "./posterior";
import type { CoverConfig } from "./cover";
export type LabConfig = {
  posterior: PosteriorConfig;
  cover: CoverConfig;
  window: number;
  shortlist: number;
  digits: string;
  candidatesText: string;
  targetsText: string;
  referenceIssue?: string;
};
export const defaultLab: LabConfig = {
  posterior: { mode: "all", window: 100, alpha: 1 },
  cover: {
    mode: "min",
    budget: 10,
    radius: 2,
    nodes: 100000,
    milliseconds: 5000,
  },
  window: 100,
  shortlist: 32,
  digits: "01",
  candidatesText: "",
  targetsText: "",
};
export function validateLab(c: LabConfig) {
  if (
    !c ||
    typeof c !== "object" ||
    !c.posterior ||
    !["all", "window"].includes(c.posterior.mode) ||
    !Number.isInteger(c.posterior.window) ||
    c.posterior.window < 1 ||
    c.posterior.window > 10000 ||
    !Number.isFinite(c.posterior.alpha) ||
    c.posterior.alpha < 0.1 ||
    c.posterior.alpha > 100 ||
    !c.cover ||
    !["min", "max"].includes(c.cover.mode)
  )
    throw Error("研究实验配置错误");
  for (const [n, lo, hi] of [
    [c.window, 40, 500],
    [c.shortlist, 1, 32],
    [c.cover.budget, 0, 32],
    [c.cover.radius, 0, 5],
    [c.cover.nodes, 1, 1000000],
    [c.cover.milliseconds, 1, 5000],
  ])
    if (!Number.isInteger(n) || n < lo || n > hi)
      throw Error("研究窗口/求解规模或预算错误");
  if (
    typeof c.digits !== "string" ||
    !/^\d{1,3}$/.test(c.digits) ||
    new Set(c.digits).size !== c.digits.length ||
    typeof c.candidatesText !== "string" ||
    typeof c.targetsText !== "string" ||
    c.candidatesText.length > 10000 ||
    c.targetsText.length > 10000 ||
    (c.referenceIssue !== undefined &&
      (typeof c.referenceIssue !== "string" || !c.referenceIssue.trim()))
  )
    throw Error("目标数字/显式号码/截止期错误");
}
