import {
  filter,
  defaultPositions,
  ruleLabels,
  type FilterInput,
  type HistoryRecord,
  type Rule,
} from "../pick5";
import { rulesAtCutoff } from "../backtest";
import {
  defaultResearch,
  researchLabels,
  type FilterMethod,
} from "../research/types";
import { researchHistory } from "../research/statistics";
import { validateAudit, type AuditConfig } from "./config";
export function phi(a: Uint8Array, b: Uint8Array): number | null {
  let x = 0,
    y = 0,
    both = 0;
  for (let i = 0; i < a.length; i++) {
    x += a[i];
    y += b[i];
    both += a[i] & b[i];
  }
  const den = Math.sqrt(x * y * (a.length - x) * (a.length - y));
  return den
    ? Math.max(-1, Math.min(1, (both * a.length - x * y) / den))
    : null;
}
const specs: [FilterMethod, number][] = [
  ["sumSigma", 1],
  ["sumSigma", 1.5],
  ["sumSigma", 2],
  ["sumQuantile", 0.7],
  ["sumQuantile", 0.9],
  ["spanQuantile", 0.7],
  ["spanQuantile", 0.9],
  ["hotcold", 6],
  ["hotcold", 8],
  ["omission", 10],
  ["omission", 20],
  ["bayes", 0.08],
  ["bayes", 0.1],
  ["markov", 0.06],
  ["markov", 0.1],
  ["samePosition", 2],
  ["positionNeighbor", 3],
  ["difference", 1],
];
function coverage(numbers: number[]): number {
  const seen = new Uint8Array(50);
  for (let n of numbers)
    for (let p = 4; p >= 0; p--) {
      seen[p * 10 + (n % 10)] = 1;
      n = Math.floor(n / 10);
    }
  return seen.reduce((a, b) => a + b, 0);
}
export type AuditAnalysis = {
  conditions: { id: string; label: string; count: number }[];
  matrix: (number | null)[][];
  redundant: { id: string; against: string; correlation: number | null }[];
  errors: { id: string; reason: string }[];
  steps: {
    id: string;
    label: string;
    before: number;
    after: number;
    removed: number;
    diversityLoss: number;
    ratio: number;
  }[];
  selectedRules: Rule[];
  initial: number;
  remaining: number;
  target: number;
  reached: boolean;
  positionCoverage: number;
  trainingStart: string;
  trainingEnd: string;
};
export type AuditFold = {
  trainingStart: string;
  trainingEnd: string;
  validationStart: string;
  validationEnd: string;
  validationCount: number;
  hits: number;
  outside: number;
  coverage: number;
  compression: number;
  product: number;
  expectedUniformHits: number;
  remaining: number;
  selected: string[];
};
function fit(
  input: FilterInput,
  c: AuditConfig,
  training: HistoryRecord[],
  base: number[],
  progress?: (s: string) => void,
) {
  const referenceIssue = training.at(-1)!.issue;
  const source =
    c.pool === "current"
      ? input.rules.filter((r) => r.enabled)
      : specs.map(([method, parameter], i): Rule => ({
          id: `audit-${i}`,
          kind: "research",
          enabled: true,
          mode: "include",
          values: [],
          research: {
            ...defaultResearch,
            method,
            parameter,
            window: c.training,
          },
        }));
  if (!source.length || source.length > 20)
    throw new Error("条件池须包含1—20个启用条件");
  if (new Set(source.map((r) => r.id)).size !== source.length)
    throw new Error("条件ID重复");
  const historicalKinds = new Set([
    "historyExclude",
    "samePosition",
    "historyOverlap",
    "neighborCounts",
    "historyDelta",
    "omission",
    "frequency",
  ]);
  const rules = rulesAtCutoff(source, referenceIssue).map((r) =>
      historicalKinds.has(r.kind)
        ? { ...r, params: { ...r.params, startIssue: training[0].issue } }
        : r,
    ),
    masks: Uint8Array[] = [],
    valid: Rule[] = [],
    conditions: AuditAnalysis["conditions"] = [],
    errors: AuditAnalysis["errors"] = [];
  for (const r of rules) {
    progress?.(`计算条件 ${conditions.length + 1}/${rules.length}`);
    try {
      const kept = filter({
          positions: defaultPositions(),
          rules: [r],
          history: training,
        }).numbers,
        bits = new Uint8Array(100000);
      for (const n of kept) bits[Number(n)] = 1;
      masks.push(bits);
      valid.push(r);
      conditions.push({
        id: r.id,
        label:
          r.kind === "research"
            ? `${researchLabels[r.research!.method]} · ${r.research!.parameter}`
            : `${ruleLabels[r.kind]} · ${r.values.join(",")}`,
        count: kept.length,
      });
    } catch (e) {
      errors.push({ id: r.id, reason: (e as Error).message });
    }
  }
  if (!valid.length)
    throw new Error("条件池没有可计算的条件，请检查历史窗口与规则参数");
  const matrix = masks.map((a, i) =>
    masks.map((b, j) =>
      i === j
        ? conditions[i].count === 0 || conditions[i].count === 100000
          ? null
          : 1
        : phi(a, b),
    ),
  );
  const eligible: number[] = [],
    redundant: AuditAnalysis["redundant"] = [];
  for (let i = 0; i < valid.length; i++) {
    const against = eligible.find((j) => {
      const p = matrix[i][j];
      return (
        (p !== null && p >= c.correlation) ||
        (conditions[i].count === conditions[j].count &&
          [0, 100000].includes(conditions[i].count))
      );
    });
    if (c.dedupe && against !== undefined)
      redundant.push({
        id: valid[i].id,
        against: valid[against].id,
        correlation: matrix[i][against],
      });
    else eligible.push(i);
  }
  let active = [...base];
  const selected: number[] = [],
    steps: AuditAnalysis["steps"] = [];
  while (active.length > c.target) {
    const beforeCoverage = coverage(active);
    let best: {
      index: number;
      numbers: number[];
      loss: number;
      ratio: number;
    } | null = null;
    for (const i of eligible.filter((i) => !selected.includes(i))) {
      const next = active.filter((n) => masks[i][n] === 1),
        removed = active.length - next.length;
      if (!removed || !next.length) continue;
      const loss = beforeCoverage - coverage(next),
        ratio = removed / (1 + loss);
      if (!best || ratio > best.ratio)
        best = { index: i, numbers: next, loss, ratio };
    }
    if (!best) break;
    const r = conditions[best.index];
    steps.push({
      id: r.id,
      label: r.label,
      before: active.length,
      after: best.numbers.length,
      removed: active.length - best.numbers.length,
      diversityLoss: best.loss,
      ratio: best.ratio,
    });
    selected.push(best.index);
    active = best.numbers;
  }
  const analysis: AuditAnalysis = {
    conditions,
    matrix,
    redundant,
    errors,
    steps,
    selectedRules: selected.map((i) => valid[i]),
    initial: base.length,
    remaining: active.length,
    target: c.target,
    reached: active.length <= c.target,
    positionCoverage: coverage(active),
    trainingStart: training[0].issue,
    trainingEnd: referenceIssue,
  };
  return { analysis, active: new Set(active) };
}
export function analyzeConditions(
  input: FilterInput,
  c: AuditConfig,
  walk: boolean,
  progress?: (s: string) => void,
): { analysis: AuditAnalysis; folds?: AuditFold[] } {
  validateAudit(c);
  const last = researchHistory(
      { ...defaultResearch, window: 1, referenceIssue: c.referenceIssue },
      input.history,
    )[0],
    rows = input
      .history!.filter((r) => r.date <= last.date)
      .sort((a, b) => a.date.localeCompare(b.date));
  if (rows.length < c.training + (walk ? c.folds * c.validation : 0))
    throw new Error("历史不足：体检训练与样本外窗口不够");
  const base = filter({
    ...input,
    rules: [],
    combination: undefined,
    selection: undefined,
    audit: undefined,
  }).numbers.map(Number);
  const latest = fit(input, c, rows.slice(-c.training), base, progress);
  if (!walk) return { analysis: latest.analysis };
  const first = rows.length - c.folds * c.validation,
    folds = Array.from({ length: c.folds }, (_, i): AuditFold => {
      const start = first + i * c.validation,
        training = rows.slice(start - c.training, start),
        validation = rows.slice(start, start + c.validation);
      progress?.(`样本外第${i + 1}/${c.folds}折`);
      const fitted = fit(input, c, training, base, (stage) =>
        progress?.(`第${i + 1}折：${stage}`),
      );
      const baseSet = new Set(base),
        hits = validation.filter((r) =>
          fitted.active.has(Number(r.number)),
        ).length,
        outside = validation.filter(
          (r) => !baseSet.has(Number(r.number)),
        ).length,
        coverage = hits / validation.length,
        compression = 1 - fitted.active.size / base.length;
      return {
        trainingStart: training[0].issue,
        trainingEnd: training.at(-1)!.issue,
        validationStart: validation[0].issue,
        validationEnd: validation.at(-1)!.issue,
        validationCount: validation.length,
        hits,
        outside,
        coverage,
        compression,
        product: coverage * compression,
        expectedUniformHits: (validation.length * fitted.active.size) / 100000,
        remaining: fitted.active.size,
        selected: fitted.analysis.steps.map((s) => s.label),
      };
    });
  return { analysis: latest.analysis, folds };
}
