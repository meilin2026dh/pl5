import { rulesAtCutoff, type ReplayRow } from "../backtest";
import { filter, type FilterInput } from "../pick5";
import { researchHistory } from "../research/statistics";
import { defaultResearch } from "../research/types";
import { structure } from "../structure";
import { learnScorer } from "./learning";
import {
  seededRandom,
  validateSelection,
  type SelectionConfig,
} from "./config";
export { structure };
export type SelectionResult = {
  numbers: string[];
  diagnostics: {
    config: SelectionConfig;
    inputCount: number;
    coarseCount: number;
    feasibleCount: number;
    searchedCount: number;
    requested: number;
    actual: number;
    bestGap: number | null;
    firstIssue: string;
    lastIssue: string;
    method: string;
    scorer: Record<string, unknown>;
    samples: number;
    attempts: number;
    oracleBest: number | null;
    searchBest: number | null;
    shortfall: boolean;
    exactSeedFallback: boolean;
  };
};
const bitCounts = Array.from(
  { length: 1024 },
  (_, n) => n.toString(2).replace(/0/g, "").length,
);
const mask = (n: string) => [...n].reduce((a, d) => a | (1 << Number(d)), 0);
export const samePositions = (a: string, b: string) =>
  [...a].filter((d, p) => d === b[p]).length;
export function jaccard(a: string, b: string) {
  const x = mask(a),
    y = mask(b);
  return bitCounts[x & y] / bitCounts[x | y];
}
export function selectPortfolio(
  input: FilterInput,
  c: SelectionConfig,
  progress?: (s: string) => void,
): SelectionResult {
  validateSelection(c);
  progress?.("载入截止期与硬约束");
  const last = researchHistory(
    { ...defaultResearch, window: 1, referenceIssue: c.referenceIssue },
    input.history,
  )[0];
  const past = input
    .history!.filter((r) => r.date <= last.date)
    .sort((a, b) => a.date.localeCompare(b.date));
  if (past.length < Math.max(c.window, c.recent))
    throw new Error("历史不足：精选评分窗口或近期约束超出截止期历史");
  const rows = past.slice(-c.window),
    recent = past
      .slice(-c.recent || past.length)
      .map((r) => ({ number: r.number, mask: mask(r.number) }));
  const initial = filter({
    ...input,
    history: past,
    selection: undefined,
  }).numbers;
  const coarse = initial.filter((n) => {
    const s = structure(n, c.gapThreshold);
    return (
      s.ac >= c.acMin &&
      s.ac <= c.acMax &&
      s.large >= c.minLarge &&
      s.large <= c.maxLarge
    );
  });
  const feasible = coarse.filter((n) => {
    const m = mask(n);
    return recent.every(
      (r) =>
        samePositions(n, r.number) <= c.historySame &&
        bitCounts[m & r.mask] / bitCounts[m | r.mask] <= c.jaccard,
    );
  });
  const diagnostics: SelectionResult["diagnostics"] = {
    config: { ...c },
    inputCount: initial.length,
    coarseCount: coarse.length,
    feasibleCount: feasible.length,
    searchedCount: 0,
    requested: c.budget,
    actual: 0,
    bestGap: null,
    firstIssue: rows[0].issue,
    lastIssue: last.issue,
    method: c.method,
    scorer: {},
    samples: 0,
    attempts: 0,
    oracleBest: null,
    searchBest: null,
    shortfall: true,
    exactSeedFallback: false,
  };
  if (!feasible.length) return { numbers: [], diagnostics };
  progress?.("拟合评分模型与全遍历对照");
  const model = learnScorer(rows, c.scorer, c.autoTune, c.seed);
  diagnostics.scorer = model.diagnostics;
  const scores = new Map(feasible.map((n) => [n, model.score(n)]));
  const compare = (a: string, b: string) =>
    scores.get(b)! - scores.get(a)! || (a < b ? -1 : a > b ? 1 : 0);
  const ranked = [...feasible].sort(compare);
  diagnostics.oracleBest = scores.get(ranked[0])!;
  let searched: string[];
  const random = seededRandom(c.seed),
    seen = new Set<string>();
  const randomNumber = () =>
    model.weights
      .map((weights) => {
        let u = random();
        for (let d = 0; d < 9; d++) {
          u -= weights[d];
          if (u < 0) return String(d);
        }
        return "9";
      })
      .join("");
  const mutate = (n: string) => {
    const p = Math.floor(random() * 5);
    return n.slice(0, p) + Math.floor(random() * 10) + n.slice(p + 1);
  };
  if (c.method === "exact") searched = ranked;
  else if (c.method === "mcga") {
    progress?.("加权蒙特卡洛候选池");
    for (let i = 0; i < c.samples; i++) {
      const n = randomNumber();
      if (scores.has(n)) seen.add(n);
    }
    diagnostics.samples = c.samples;
    let population = [...seen].sort(compare).slice(0, c.population);
    if (!population.length) {
      diagnostics.exactSeedFallback = true;
      population = [ranked[0]];
      seen.add(ranked[0]);
    }
    progress?.("遗传算法精化（全部后代重新过硬约束）");
    for (let g = 0; g < c.generations; g++) {
      const children = new Set(
        population.slice(0, Math.max(1, Math.floor(c.population / 5))),
      );
      for (let k = 0; k < c.population * 3; k++) {
        const a = population[Math.floor(random() * population.length)],
          b = population[Math.floor(random() * population.length)],
          cut = 1 + Math.floor(random() * 4);
        let child = a.slice(0, cut) + b.slice(cut);
        if (random() < 0.3) child = mutate(child);
        diagnostics.attempts++;
        if (scores.has(child)) {
          children.add(child);
          seen.add(child);
        }
      }
      population = [...children].sort(compare).slice(0, c.population);
    }
    searched = [...seen].sort(compare);
  } else {
    progress?.("模拟退火（可行域拒绝非法移动）");
    let current = feasible[Math.floor(random() * feasible.length)];
    seen.add(current);
    const total = c.generations * c.population;
    for (let i = 0; i < total; i++) {
      const next = mutate(current);
      diagnostics.attempts++;
      if (!scores.has(next)) continue;
      const delta = scores.get(next)! - scores.get(current)!,
        temperature = Math.max(0.001, 1 - i / total);
      if (delta >= 0 || random() < Math.exp(delta / temperature)) {
        current = next;
        seen.add(current);
      }
    }
    searched = [...seen].sort(compare);
  }
  progress?.("按分数贪心构造多样性组合");
  const selected: string[] = [];
  for (const n of searched) {
    if (
      selected.every(
        (m) =>
          samePositions(n, m) <= c.maxSame &&
          jaccard(n, m) <= (c.outputJaccard ?? 1),
      )
    )
      selected.push(n);
    if (selected.length >= c.budget) break;
  }
  diagnostics.searchedCount = searched.length;
  diagnostics.searchBest = scores.get(searched[0])!;
  diagnostics.bestGap = Math.max(
    0,
    diagnostics.oracleBest - diagnostics.searchBest,
  );
  diagnostics.actual = selected.length;
  diagnostics.shortfall = selected.length < c.budget;
  return { numbers: selected, diagnostics };
}

export function replaySelection(
  input: FilterInput,
  c: SelectionConfig,
  progress?: (s: string) => void,
): (ReplayRow & { selected: number })[] {
  validateSelection(c);
  const last = researchHistory(
    { ...defaultResearch, window: 1, referenceIssue: c.referenceIssue },
    input.history,
  )[0];
  const rows = input
    .history!.filter((r) => r.date <= last.date)
    .sort((a, b) => a.date.localeCompare(b.date));
  return rows.slice(-10).map((row) => {
    const index = rows.indexOf(row),
      past = rows.slice(0, index),
      referenceIssue = past.at(-1)?.issue;
    const base = {
      ...row,
      referenceIssue: referenceIssue ?? "无",
      selected: 0,
    };
    const allowed = input.candidates
      ? input.candidates.includes(row.number)
      : [...row.number].every((d, p) =>
          input.positions[p]?.includes(Number(d)),
        );
    if (!allowed) return { ...base, status: "outside" as const };
    try {
      const result = selectPortfolio(
        {
          ...input,
          history: past,
          rules: rulesAtCutoff(input.rules, referenceIssue),
        },
        { ...c, referenceIssue },
        (stage) => progress?.(`${row.issue}：${stage}`),
      );
      return {
        ...base,
        selected: result.numbers.length,
        status: result.numbers.includes(row.number)
          ? ("retained" as const)
          : ("removed" as const),
      };
    } catch (e) {
      const reason = (e as Error).message;
      return {
        ...base,
        reason,
        status: /历史不足|研究方法需要历史/.test(reason)
          ? ("insufficient" as const)
          : ("error" as const),
      };
    }
  });
}
