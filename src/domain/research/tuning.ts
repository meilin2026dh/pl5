import type { HistoryRecord } from "../pick5";
import { buildStats } from "./statistics";
import { fitFilter } from "./filters";
import { parameterGrids, pool, type FilterSpec } from "./presets";
import type { ResearchConfig, ResearchDiagnostics } from "./types";
export type ValidationFold = {
  training: HistoryRecord[];
  validation: HistoryRecord[];
};
export function validationFolds(
  config: ResearchConfig,
  rows: HistoryRecord[],
): ValidationFold[] {
  const first = rows.length - config.folds * config.validationSize;
  if (first < 10) throw new Error("历史不足：滚动验证后至少需要10期训练记录");
  return Array.from({ length: config.folds }, (_, i) => {
    const cut = first + i * config.validationSize;
    return {
      training: rows.slice(0, cut),
      validation: rows.slice(cut, cut + config.validationSize),
    };
  });
}
type Evaluation = {
  parameter: number;
  coverage: number;
  averageCount: number;
  allHit: boolean;
};
export function chooseParameter(
  entries: Evaluation[],
  strategy: ResearchConfig["selection"],
): { entry: Evaluation; fallback: boolean } {
  if (!entries.length) throw new Error("自动选择候选为空");
  const eligible = entries.filter((e) =>
    strategy === "strict"
      ? e.allHit
      : e.coverage >= (strategy === "cov90" ? 0.9 : 0.6),
  );
  const fallback = !eligible.length;
  const sorted = [...(fallback ? entries : eligible)].sort((a, b) =>
    fallback
      ? b.coverage - a.coverage || a.averageCount - b.averageCount
      : strategy === "lift60"
        ? (b.averageCount ? b.coverage / b.averageCount : 0) -
            (a.averageCount ? a.coverage / a.averageCount : 0) ||
          a.averageCount - b.averageCount
        : a.averageCount - b.averageCount,
  );
  return { entry: sorted[0], fallback };
}
let universe: number[][] | undefined;
const digits = () =>
  (universe ??= Array.from({ length: 100000 }, (_, i) => [
    Math.floor(i / 10000),
    Math.floor(i / 1000) % 10,
    Math.floor(i / 100) % 10,
    Math.floor(i / 10) % 10,
    i % 10,
  ]));
function mask(prepared: ReturnType<typeof fitFilter>): {
  bits: Uint8Array;
  count: number;
} {
  const bits = new Uint8Array(100000),
    all = digits();
  let count = 0;
  for (let i = 0; i < 100000; i++)
    if (prepared.testDigits(all[i])) {
      bits[i] = 1;
      count++;
    }
  return { bits, count };
}
function hits(bits: Uint8Array, rows: HistoryRecord[]): number {
  return rows.reduce((n, r) => n + bits[Number(r.number)], 0);
}
export function tuneResearch(
  config: ResearchConfig,
  rows: HistoryRecord[],
): { selected: FilterSpec[]; diagnostics: ResearchDiagnostics } {
  const folds = validationFolds(config, rows),
    stats = folds.map((f) => buildStats(f.training));
  const foldInfo = folds.map((f) => ({
    trainingCount: f.training.length,
    trainingEnd: f.training.at(-1)!.issue,
    validationStart: f.validation[0].issue,
    validationEnd: f.validation.at(-1)!.issue,
    validationCount: f.validation.length,
  }));
  const total = folds.reduce((n, f) => n + f.validation.length, 0);
  if (config.method === "auto") {
    const entries = parameterGrids[config.family].map((parameter) => {
      const outcomes = stats.map((s, i) => {
        const prepared = fitFilter(config.family, parameter, s),
          m = mask(prepared);
        return { count: m.count, hits: hits(m.bits, folds[i].validation) };
      });
      const hit = outcomes.reduce((n, o) => n + o.hits, 0);
      return {
        parameter,
        coverage: hit / total,
        averageCount: outcomes.reduce((n, o) => n + o.count, 0) / folds.length,
        allHit: hit === total,
      };
    });
    const chosen = chooseParameter(entries, config.selection);
    return {
      selected: [{ method: config.family, parameter: chosen.entry.parameter }],
      diagnostics: {
        strategy: config.selection,
        fallback: chosen.fallback,
        selectedParameter: chosen.entry.parameter,
        validationCoverage: chosen.entry.coverage,
        validationCount: total,
        averageCount: chosen.entry.averageCount,
        folds: foldInfo,
        candidates: entries,
      },
    };
  }
  const candidateMasks = pool.map((spec) =>
    stats.map((s) => mask(fitFilter(spec.method, spec.parameter, s)).bits),
  );
  let current = folds.map(() => new Uint8Array(100000).fill(1));
  let currentHits = total,
    currentCount = 100000 * folds.length;
  const chosen: number[] = [],
    steps: ResearchDiagnostics[] = [];
  for (let step = 0; step < config.maxSteps; step++) {
    let best:
      { index: number; ratio: number; hit: number; count: number } | undefined;
    for (let k = 0; k < pool.length; k++) {
      if (chosen.includes(k)) continue;
      let count = 0,
        hit = 0;
      for (let f = 0; f < folds.length; f++) {
        const a = current[f],
          b = candidateMasks[k][f];
        for (let n = 0; n < 100000; n++) count += a[n] & b[n];
        for (const row of folds[f].validation) {
          const n = Number(row.number);
          hit += a[n] & b[n];
        }
      }
      const removed = currentCount - count;
      if (removed <= 0) continue;
      const ratio = removed / folds.length / (currentHits - hit + 1);
      if (!best || ratio > best.ratio) best = { index: k, ratio, hit, count };
    }
    if (!best || best.hit / total < config.targetCoverage) break;
    chosen.push(best.index);
    currentHits = best.hit;
    currentCount = best.count;
    current = current.map((a, f) =>
      a.map((v, n) => v & candidateMasks[best!.index][f][n]),
    );
    steps.push({
      step: step + 1,
      ...pool[best.index],
      coverage: currentHits / total,
      averageCount: currentCount / folds.length,
    });
    if (currentCount <= folds.length) break;
  }
  return {
    selected: chosen.map((i) => ({ ...pool[i] })),
    diagnostics: {
      selected: chosen.map((i) => ({ ...pool[i] })),
      steps,
      validationCoverage: currentHits / total,
      validationCount: total,
      averageCount: currentCount / folds.length,
      folds: foldInfo,
      targetCoverage: config.targetCoverage,
      emptySelection: !chosen.length,
      selectionPolicy:
        "各折先训练后验证；每步最大淘汰/损失比，不能达到覆盖目标则停止",
    },
  };
}
