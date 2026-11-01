import { numberAt } from "./sets";
import type { HistoryRecord } from "../pick5";
export const kinds = ["U", "I", "J1", "J2"] as const;
export type Kind = (typeof kinds)[number];
export const priors = [0.5, 1 / 6, 1 / 6, 1 / 6];
export const names = {
  U: "独立均匀",
  I: "独立位置",
  J1: "单父位置链",
  J2: "双父位置链",
};
export type JointModel = {
  kind: Kind;
  strength: number;
  counts: number[][];
  totals: number[][];
  n: number;
  logEvidence: number;
};
const depth = (kind: Kind, p: number) =>
  Math.min(p, kind === "J2" ? 2 : kind === "J1" ? 1 : 0);
const context = (d: number[], p: number, k: number) =>
  k === 0 ? 0 : k === 1 ? d[p - 1] : 10 * d[p - 2] + d[p - 1];
export function probability(m: JointModel, number: string) {
  if (m.kind === "U") return 0.00001;
  const d = [...number].map(Number);
  let prob = 1;
  for (let p = 0; p < 5; p++) {
    const q = 10 ** depth(m.kind, p),
      j = context(d, p, depth(m.kind, p)),
      a = m.strength / q;
    prob *= (m.counts[p][j * 10 + d[p]] + a / 10) / (m.totals[p][j] + a);
  }
  return prob;
}
export function updateModel(m: JointModel, number: string) {
  m.logEvidence += Math.log(probability(m, number));
  m.n++;
  if (m.kind === "U") return;
  const d = [...number].map(Number);
  for (let p = 0; p < 5; p++) {
    const j = context(d, p, depth(m.kind, p));
    m.counts[p][j * 10 + d[p]]++;
    m.totals[p][j]++;
  }
}
export function fitModel(
  kind: Kind,
  rows: HistoryRecord[],
  strength: number,
): JointModel {
  const m: JointModel = {
    kind,
    strength,
    n: 0,
    logEvidence: 0,
    counts: [],
    totals: [],
  };
  for (let p = 0; p < 5; p++) {
    const q = 10 ** depth(kind, p);
    m.counts.push(Array(q * 10).fill(0));
    m.totals.push(Array(q).fill(0));
  }
  for (const r of rows) updateModel(m, r.number);
  return m;
}
export function pmf(m: JointModel) {
  return Float64Array.from({ length: 100000 }, (_, i) =>
    probability(m, numberAt(i)),
  );
}
export function softmax(logs: number[]) {
  const a = Math.max(...logs),
    e = logs.map((x) => Math.exp(x - a)),
    s = e.reduce((a, b) => a + b, 0);
  return e.map((x) => x / s);
}
export function evidence(rows: HistoryRecord[], strength: number) {
  const models = kinds.map((k) => fitModel(k, rows, strength)),
    logs = models.map((m, i) => m.logEvidence + Math.log(priors[i])),
    post = softmax(logs);
  return models.map((m, i) => ({
    kind: m.kind,
    name: names[m.kind],
    prior: priors[i],
    posterior: post[i],
    logEvidence: m.logEvidence,
    logBF: m.logEvidence - models[0].logEvidence,
    bits: -logs[i] / Math.LN2,
    savedBits: (logs[i] - logs[0]) / Math.LN2,
    parameters:
      m.kind === "U" ? 0 : m.totals.reduce((a, b) => a + b.length * 9, 0),
    contexts: m.totals.map((x) => x.length),
  }));
}
