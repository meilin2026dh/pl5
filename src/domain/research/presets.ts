import type { FilterMethod, ResearchConfig } from "./types";
export type FilterSpec = { method: FilterMethod; parameter: number };
const spec = (method: FilterMethod, parameter: number): FilterSpec => ({
  method,
  parameter,
});
export const parameterGrids: Record<FilterMethod, number[]> = {
  hotcold: [4, 5, 6, 7, 8, 9],
  omission: [4, 5, 6, 8, 10, 14, 20, 30],
  bayes: [0.07, 0.08, 0.09, 0.095, 0.1, 0.105, 0.11, 0.12],
  markov: [0.03, 0.05, 0.07, 0.09, 0.11],
  sumSigma: [0.7, 1, 1.3, 1.6, 2, 2.5],
  sumQuantile: [0.5, 0.7, 0.8, 0.9, 0.95, 0.99],
  spanQuantile: [0.5, 0.7, 0.8, 0.9, 0.95, 0.99],
  oddFrequency: [0.01, 0.02, 0.05, 0.08, 0.12],
  bigFrequency: [0.01, 0.02, 0.05, 0.08, 0.12],
  primeFrequency: [0.01, 0.02, 0.05, 0.08, 0.12],
  distinctFrequency: [0.01, 0.02, 0.05, 0.1],
  consecutiveFrequency: [0.01, 0.02, 0.05, 0.1],
  routeFrequency: [0.005, 0.01, 0.02, 0.05],
  tailFrequency: [0.05, 0.08, 0.1, 0.12],
  samePosition: [1, 2, 3, 4],
  positionNeighbor: [1, 2, 3, 4],
  multiset: [1, 2],
};
export const pool: FilterSpec[] = [];
for (const p of [6, 7, 8, 9]) pool.push(spec("hotcold", p));
for (const p of [4, 6, 8, 12, 20]) pool.push(spec("omission", p));
for (const p of [0.085, 0.095, 0.105]) pool.push(spec("bayes", p));
for (const p of [0.04, 0.07, 0.1]) pool.push(spec("markov", p));
for (const p of [0.8, 1.1, 1.4, 1.8, 2.2]) pool.push(spec("sumSigma", p));
for (const p of [0.6, 0.8, 0.9, 0.95])
  pool.push(spec("sumQuantile", p), spec("spanQuantile", p));
for (const p of [0.02, 0.05, 0.1])
  for (const m of [
    "oddFrequency",
    "bigFrequency",
    "primeFrequency",
    "distinctFrequency",
    "consecutiveFrequency",
    "routeFrequency",
    "tailFrequency",
  ] as const)
    pool.push(spec(m, p));
for (const p of [2, 3, 4]) pool.push(spec("samePosition", p));
for (const p of [2, 3, 4]) pool.push(spec("positionNeighbor", p));
pool.push(spec("multiset", 1), spec("multiset", 2));
export const presets: Record<ResearchConfig["preset"], FilterSpec[]> = {
  A: [spec("hotcold", 7), spec("sumSigma", 1.5), spec("oddFrequency", 0.02)],
  B: [
    spec("hotcold", 6),
    spec("spanQuantile", 0.9),
    spec("distinctFrequency", 0.02),
  ],
  C: [
    spec("bayes", 0.09),
    spec("samePosition", 3),
    spec("consecutiveFrequency", 0.02),
  ],
  D: [spec("hotcold", 8), spec("markov", 0.05), spec("primeFrequency", 0.02)],
  E: [
    spec("omission", 8),
    spec("sumQuantile", 0.8),
    spec("bigFrequency", 0.02),
  ],
  F: [
    spec("hotcold", 7),
    spec("sumSigma", 1.5),
    spec("spanQuantile", 0.9),
    spec("oddFrequency", 0.02),
    spec("routeFrequency", 0.01),
  ],
};
