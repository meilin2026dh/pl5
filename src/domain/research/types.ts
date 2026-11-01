import { defaultPotential, type PotentialConfig } from "./potential";
import type { HistoryRecord } from "../pick5";
export const filterMethods = [
  "difference",
  "hotcold",
  "omission",
  "bayes",
  "markov",
  "sumSigma",
  "sumQuantile",
  "spanQuantile",
  "oddFrequency",
  "bigFrequency",
  "primeFrequency",
  "distinctFrequency",
  "consecutiveFrequency",
  "routeFrequency",
  "tailFrequency",
  "samePosition",
  "positionNeighbor",
  "multiset",
] as const;
export type FilterMethod = (typeof filterMethods)[number];
export const scoreMethods = [
  "markovScore",
  "potential",
  "heatScore",
  "bma",
  "dsPlausibility",
  "dsBelief",
  "dsDempster",
  "sparseBest",
] as const;
export type ScoreMethod = (typeof scoreMethods)[number];
export type ResearchMethod =
  FilterMethod | ScoreMethod | "auto" | "greedy" | "preset";
export type ResearchConfig = {
  method: ResearchMethod;
  potential?: PotentialConfig;
  window: number;
  referenceIssue?: string;
  parameter: number;
  family: FilterMethod;
  selection: "lift60" | "cov90" | "strict";
  retain: number;
  ties: "inclusive" | "seeded";
  seed: number;
  windows: number;
  folds: number;
  validationSize: number;
  targetCoverage: number;
  maxSteps: number;
  preset: "A" | "B" | "C" | "D" | "E" | "F";
};
export const defaultResearch: ResearchConfig = {
  method: "hotcold",
  potential: { ...defaultPotential },
  window: 100,
  parameter: 7,
  family: "hotcold",
  selection: "cov90",
  retain: 0.25,
  ties: "inclusive",
  seed: 20261029,
  windows: 5,
  folds: 3,
  validationSize: 10,
  targetCoverage: 0.9,
  maxSteps: 8,
  preset: "A",
};
export const researchLabels: Record<ResearchMethod, string> = {
  difference: "有符号差分形态白名单",
  markovScore: "马尔可夫路径似然评分",
  hotcold: "逐位冷热Top K",
  omission: "逐位遗漏上限",
  bayes: "贝叶斯平滑阈值",
  markov: "马尔可夫转移阈值",
  sumSigma: "和值标准差带",
  sumQuantile: "和值中心分位",
  spanQuantile: "跨度中心分位",
  oddFrequency: "奇偶个数频率",
  bigFrequency: "大小个数频率",
  primeFrequency: "质合个数频率",
  distinctFrequency: "不同数字数频率",
  consecutiveFrequency: "连号对数频率",
  routeFrequency: "012路个数频率",
  tailFrequency: "和尾频率",
  samePosition: "同位重号上限",
  positionNeighbor: "同位重邻上限",
  multiset: "数字多重集历史次数",
  potential: "冷热势能动态评分",
  heatScore: "平滑热度评分",
  bma: "BMA七模型平均",
  dsPlausibility: "D-S IDM似然度",
  dsBelief: "D-S IDM信念度",
  dsDempster: "D-S分窗融合",
  sparseBest: "单位置最佳模型",
  auto: "滚动自动选参",
  greedy: "贪心组合",
  preset: "固定组合包",
};
export type ResearchDiagnostics = Record<string, unknown>;
export type PreparedResearch = {
  test: (number: string) => boolean;
  diagnostics: ResearchDiagnostics;
};
export type ResearchStats = {
  rows: HistoryRecord[];
  digits: number[][];
  n: number;
  counts: number[][];
  omissions: number[][];
  transitions: number[][][];
  last: number[];
  sums: number[];
  spans: number[];
  mean: number;
  sd: number;
  frequencies: Record<string, Map<string, number>>;
  multisets: Map<string, number>;
};
export type ScoreModel = {
  score: (number: string) => number;
  details: ResearchDiagnostics;
};
