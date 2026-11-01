import { filter, defaultPositions, type FilterInput } from "../pick5";
import { rulesAtCutoff } from "../backtest";
import { researchHistory } from "../research/statistics";
import { defaultResearch } from "../research/types";
import { seededRandom } from "../selection/config";
import { validateInnovation, type InnovationConfig } from "./config";
import { optimizeWeights } from "./bo";
export function hamming(a: string, b: string) {
  let d = 0;
  for (let p = 0; p < 5; p++) d += Number(a[p] !== b[p]);
  return d;
}
export function neighbors(n: string) {
  const out: string[] = [];
  for (let p = 0; p < 5; p++)
    for (let d = 0; d < 10; d++)
      if (String(d) !== n[p]) out.push(n.slice(0, p) + d + n.slice(p + 1));
  return out;
}
function ball(n: string, matches: number) {
  const out = [n, ...(matches < 5 ? neighbors(n) : [])];
  if (matches === 3)
    for (let p = 0; p < 5; p++)
      for (let q = p + 1; q < 5; q++)
        for (let a = 0; a < 10; a++)
          if (String(a) !== n[p])
            for (let b = 0; b < 10; b++)
              if (String(b) !== n[q]) {
                const s = [...n];
                s[p] = String(a);
                s[q] = String(b);
                out.push(s.join(""));
              }
  return out;
}
export function exactCoverage(
  selected: string[],
  targets: string[],
  matches: number,
) {
  const set = new Set(selected.flatMap((n) => ball(n, matches))),
    covered = targets.filter((t) => set.has(t)).length;
  return {
    covered,
    total: targets.length,
    guaranteed: covered === targets.length,
    witness: targets.find((t) => !set.has(t)) ?? null,
  };
}
export function freeEnergy(
  p: number[],
  links: number[][],
  budget: number,
  temperature: number,
) {
  const gradient = p.map(() => 0);
  let loss = 0;
  for (const row of links) {
    const product = row.reduce((s, i) => s * (1 - p[i]), 1);
    loss += product / links.length;
    for (const i of row) gradient[i] -= product / (1 - p[i]) / links.length;
  }
  const delta = p.reduce((a, b) => a + b, 0) - budget,
    penalty = 2 / Math.max(1, budget * budget);
  loss += penalty * delta * delta;
  for (let i = 0; i < p.length; i++) {
    loss +=
      (temperature *
        (p[i] * Math.log(p[i]) + (1 - p[i]) * Math.log(1 - p[i]))) /
      p.length;
    gradient[i] +=
      2 * penalty * delta +
      (temperature * Math.log(p[i] / (1 - p[i]))) / p.length;
  }
  return { loss, gradient };
}
function shape(n: string) {
  let s = 0;
  for (let p = 1; p < 5; p++) s += (Number(n[p]) - Number(n[p - 1])) ** 2;
  return s / 324;
}
export function graphFeatures(n: string, allowed: Set<string>) {
  const ns = neighbors(n),
    mean = ns.reduce((s, v) => s + shape(v), 0) / 45;
  return {
    degree: ns.filter((v) => allowed.has(v)).length,
    residual: Math.abs(shape(n) - mean),
  };
}
function wilson(hits: number, n: number) {
  const z = 1.96,
    p = hits / n,
    den = 1 + (z * z) / n,
    center = (p + (z * z) / (2 * n)) / den,
    half = (z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n))) / den;
  return [Math.max(0, center - half), Math.min(1, center + half)];
}
export function runInnovation(
  input: FilterInput,
  c: InnovationConfig,
  progress?: (s: string) => void,
) {
  validateInnovation(c);
  if (input.rules.filter((r) => r.enabled).length > 20)
    throw Error("覆盖实验最多分析20条启用条件");
  const history = researchHistory(
      {
        ...defaultResearch,
        window: c.window,
        referenceIssue: c.referenceIssue,
      },
      input.history,
    ),
    last = history.at(-1)!.issue;
  // Preserve the full prefix for existing rule windows; the new features use only c.window rows.
  const rows = input.history!.filter((r) => r.date <= history.at(-1)!.date),
    rules = rulesAtCutoff(input.rules, last),
    bounded = { ...input, history: rows, rules, innovation: undefined };
  const base = filter({
      ...bounded,
      rules: [],
      combination: undefined,
    }).numbers,
    hard = filter({
      ...bounded,
      combination: { mode: "strict", minimum: 0 },
    }).numbers,
    hardSet = new Set(hard),
    eligible = c.rules === "hard" ? hard : base,
    eligibleSet = new Set(eligible);
  if (!eligible.length) throw Error("硬约束后没有候选；不放松条件或越界回捞");
  const active = rules.filter((r) => r.enabled),
    masks = active.map((r, i) => {
      progress?.(`条件审计 ${i + 1}/${active.length}`);
      const bits = new Uint8Array(100000);
      for (const n of filter({
        ...bounded,
        positions: defaultPositions(),
        candidates: undefined,
        rules: [r],
        combination: undefined,
      }).numbers)
        bits[Number(n)] = 1;
      return bits;
    });
  const features = new Float32Array(400000),
    stages = new Uint8Array(100000),
    scores = new Float64Array(100000);
  scores.fill(Number.NaN);
  for (const n of base) stages[Number(n)] = hardSet.has(n) ? 2 : 1;
  for (let i = 0; i < eligible.length; i++) {
    if (i % 5000 === 0) progress?.(`图特征与软评分 ${i}/${eligible.length}`);
    const n = eligible[i],
      key = Number(n),
      g = graphFeatures(n, eligibleSet),
      distance = Math.min(...history.map((r) => hamming(n, r.number))) / 5;
    features[key * 4] = active.length
      ? masks.reduce((s, m) => s + m[key], 0) / active.length
      : 1;
    features[key * 4 + 1] = g.residual;
    features[key * 4 + 2] = distance;
    features[key * 4 + 3] = 1 - g.degree / 45;
  }
  const targets = filter({
    positions: Array.from({ length: 5 }, () => [...c.digits].map(Number)),
    rules: [],
  }).numbers;
  const score = (n: string, w: number[]) =>
    w.reduce((s, v, i) => s + v * features[Number(n) * 4 + i], 0) /
    w.reduce((a, b) => a + b, 0);
  const trainTargets = targets.filter((_, i) => i % 5 !== 0),
    testTargets = targets.filter((_, i) => i % 5 === 0);
  const tuning = c.tune
    ? optimizeWeights(c.weights, c.seed, (w) => {
        const ns = [...eligible]
          .sort((a, b) => score(b, w) - score(a, w) || a.localeCompare(b))
          .slice(0, c.budget);
        return (
          exactCoverage(
            ns,
            trainTargets.length ? trainTargets : targets,
            c.matches,
          ).covered / (trainTargets.length || targets.length)
        );
      })
    : null;
  const weights = tuning?.weights ?? c.weights;
  const sorted = [...eligible].sort(
    (a, b) => score(b, weights) - score(a, weights) || a.localeCompare(b),
  );
  for (const n of eligible) {
    scores[Number(n)] = score(n, weights);
    stages[Number(n)] = 2;
  }
  const random = seededRandom(c.seed),
    half = Math.ceil(c.shortlist / 2),
    pool = sorted.slice(0, c.solver === "rank" ? c.shortlist : half),
    reservoir = sorted.slice(half);
  // Seeded breadth is retained so score extremes cannot monopolize the coverage search.
  for (let i = reservoir.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [reservoir[i], reservoir[j]] = [reservoir[j], reservoir[i]];
  }
  if (c.solver !== "rank")
    pool.push(...reservoir.slice(0, Math.max(0, c.shortlist - pool.length)));
  pool.sort(
    (a, b) => scores[Number(b)] - scores[Number(a)] || a.localeCompare(b),
  );
  for (const n of pool) stages[Number(n)] = 3;
  const targetIndex = new Int32Array(100000);
  targetIndex.fill(-1);
  targets.forEach((n, i) => (targetIndex[Number(n)] = i));
  const coverageLists = pool.map((n) =>
    ball(n, c.matches)
      .map((t) => targetIndex[Number(t)])
      .filter((i) => i >= 0),
  );
  let relaxed: number[] | null = null;
  const energyTrace: number[] = [];
  if (c.solver === "entropy") {
    const sample = Array.from(
        { length: Math.min(512, targets.length) },
        (_, i) =>
          Math.floor((i * targets.length) / Math.min(512, targets.length)),
      ),
      index = new Map(sample.map((v, i) => [v, i])),
      links = sample.map(() => [] as number[]);
    coverageLists.forEach((row, i) =>
      row.forEach((t) => {
        const j = index.get(t);
        if (j !== undefined) links[j].push(i);
      }),
    );
    relaxed = pool.map(() => Math.min(0.9, c.budget / pool.length));
    for (let t = 0; t < 120; t++) {
      const f = freeEnergy(
        relaxed,
        links,
        c.budget,
        0.2 * (1 - t / 120) + 0.005,
      );
      if (t % 20 === 0) energyTrace.push(f.loss);
      relaxed = relaxed.map((p, i) =>
        Math.max(1e-5, Math.min(1 - 1e-5, p - 0.2 * f.gradient[i])),
      );
    }
  }
  const selected: number[] = [],
    counts = new Uint16Array(targets.length),
    steps: { role: string; number: string; gain: number; reason: string }[] =
      [];
  const add = (i: number, reason: string) => {
    const gain = coverageLists[i].filter((t) => counts[t] === 0).length;
    selected.push(i);
    for (const t of coverageLists[i]) counts[t]++;
    steps.push({ role: "Selector", number: pool[i], gain, reason });
  };
  if (c.solver === "rank")
    for (let i = 0; i < Math.min(c.budget, pool.length); i++)
      add(i, "加权软分排序");
  else if (c.solver === "sample") {
    const order = pool
      .map((n, i) => ({
        i,
        key:
          Math.log(Math.max(1e-12, random())) /
          Math.max(1e-6, Math.exp(scores[Number(n)] * 3)),
      }))
      .sort((a, b) => b.key - a.key);
    for (const { i } of order.slice(0, c.budget))
      add(i, "固定种子加权无放回抽样");
  } else {
    while (
      selected.length < Math.min(c.budget, pool.length) &&
      counts.some((v) => !v)
    ) {
      let best = -1,
        gain = -1,
        value = -Infinity;
      for (let i = 0; i < pool.length; i++)
        if (!selected.includes(i)) {
          const g = coverageLists[i].filter((t) => counts[t] === 0).length,
            v =
              g + (relaxed?.[i] ?? 0) * 0.25 + scores[Number(pool[i])] * 0.001;
          if (v > value) {
            best = i;
            gain = g;
            value = v;
          }
        }
      if (best < 0 || gain <= 0) break;
      add(
        best,
        relaxed ? "熵松弛偏好＋精确边际覆盖离散化" : "精确边际覆盖贪心",
      );
    }
  }
  const beforeRescue = counts.filter((v) => v > 0).length,
    rescues: { removed: string; added: string; gain: number }[] = [];
  if (c.rescue && selected.length) {
    // At most 128 exact local comparisons; only positive coverage gains may replace an entry.
    const excluded = pool
      .map((_, i) => i)
      .filter((i) => !selected.includes(i))
      .slice(0, 8);
    let best: { slot: number; incoming: number; gain: number } | null = null;
    for (const incoming of excluded)
      for (
        let slot = Math.max(0, selected.length - 16);
        slot < selected.length;
        slot++
      ) {
        const outgoing = selected[slot],
          lost = coverageLists[outgoing].filter((t) => counts[t] === 1),
          incomingSet = new Set(coverageLists[incoming]);
        const gain =
          coverageLists[incoming].filter((t) => counts[t] === 0).length -
          lost.filter((t) => !incomingSet.has(t)).length;
        if (gain > 0 && (!best || gain > best.gain))
          best = { slot, incoming, gain };
      }
    if (best) {
      const outgoing = selected[best.slot];
      for (const t of coverageLists[outgoing]) counts[t]--;
      for (const t of coverageLists[best.incoming]) counts[t]++;
      rescues.push({
        removed: pool[outgoing],
        added: pool[best.incoming],
        gain: best.gain,
      });
      selected[best.slot] = best.incoming;
      stages[Number(pool[best.incoming])] = 5;
    }
  }
  const numbers = selected.map((i) => pool[i]);
  for (const n of numbers) if (stages[Number(n)] !== 5) stages[Number(n)] = 4;
  const coverage = exactCoverage(numbers, targets, c.matches),
    chosen = new Set(numbers),
    globalRandom = seededRandom(c.seed ^ 0xa5a5a5a5),
    targetRandom = seededRandom(c.seed ^ 0x12345678),
    coveredTargets = new Set(targets.filter((_, i) => counts[i] > 0));
  let hits = 0,
    geometry = 0;
  for (let i = 0; i < c.simulations; i++) {
    hits += Number(
      chosen.has(String(Math.floor(globalRandom() * 100000)).padStart(5, "0")),
    );
    geometry += Number(
      coveredTargets.has(targets[Math.floor(targetRandom() * targets.length)]),
    );
  }
  const guard = {
    ok:
      numbers.length <= c.budget &&
      new Set(numbers).size === numbers.length &&
      numbers.every((n) => eligibleSet.has(n)) &&
      (c.rules !== "hard" ||
        numbers.every((n) => masks.every((m) => m[Number(n)] === 1))),
    budget: c.budget,
    actual: numbers.length,
    rulePolicy: c.rules,
  };
  if (!guard.ok) throw Error("Guard校验失败，结果不交付");
  return {
    numbers,
    coverage,
    risk: {
      exactHit: numbers.length / 100000,
      exactMiss: 1 - numbers.length / 100000,
      conditionalExact:
        targets.filter((t) => chosen.has(t)).length / targets.length,
      simulations: c.simulations,
      hits,
      estimate: hits / c.simulations,
      wilson95: wilson(hits, c.simulations),
      geometryEstimate: geometry / c.simulations,
      geometryWilson95: wilson(geometry, c.simulations),
    },
    audit: {
      algorithmVersion: "coverage-audit-v1",
      config: c,
      weights,
      historyStart: history[0].issue,
      historyEnd: last,
      source: input.historySource ?? "未标注",
      base: base.length,
      hard: hard.length,
      eligible: eligible.length,
      shortlist: pool.length,
      scoreFeatures: [
        "条件通过比例",
        "局部形态残差",
        "历史最近距离",
        "候选图稀疏度",
      ],
      stopReason:
        numbers.length >= c.budget
          ? "达到注数预算"
          : coverage.guaranteed
            ? "目标域已全覆盖"
            : "候选短名单中没有新增覆盖；不是全域无解证明",
      graph: "完整汉明距离1图每节点45度；密度是候选诱导子图度数/45，非销量",
      tuning,
      weightValidation: tuning
        ? exactCoverage(sorted.slice(0, c.budget), testTargets, c.matches)
        : null,
      energyTrace,
      rescues,
      beforeRescue,
      guard,
      steps,
      limits:
        "短名单启发式，不证明全局最优；3/4位匹配是几何覆盖，不是排列五奖级；没有销量、GNN、LLM代理或GPU FEM",
    },
    trace: {
      features,
      scores,
      stages,
      masks,
      ruleIds: active.map((r) => r.id),
    },
  };
}
export type InnovationResult = ReturnType<typeof runInnovation>;
export function explainInnovation(result: InnovationResult, n: string) {
  if (!/^\d{5}$/.test(n)) throw Error("请输入完整五位号码，保留前导零");
  const i = Number(n),
    stage = result.trace.stages[i],
    features = Array.from(result.trace.features.slice(i * 4, i * 4 + 4)),
    score = result.trace.scores[i];
  const failures = result.trace.masks
    .map((m, j) => (m[i] ? null : result.trace.ruleIds[j]))
    .filter(Boolean);
  return {
    number: n,
    stage: [
      "原始大底外",
      "硬条件未通过",
      "可行但未入短名单",
      "短名单未选",
      "已选",
      "覆盖交换回捞",
    ][stage],
    features: stage >= 2 ? features : null,
    score: Number.isFinite(score) ? score : null,
    ruleFailures: stage ? failures : [],
    components:
      stage >= 2
        ? features.map((value, j) => ({
            name: result.audit.scoreFeatures[j],
            value,
            weight: result.audit.weights[j],
            contribution:
              (value * result.audit.weights[j]) /
              result.audit.weights.reduce((a, b) => a + b, 0),
          }))
        : null,
    disagreement:
      stage >= 2 && features[0] < 1
        ? "软排序参与但部分原条件不通过；保留异议"
        : "无条件判定异议",
    guard: result.audit.guard,
    selection: result.audit.steps.find((s) => s.number === n) ?? null,
    rescue:
      result.audit.rescues.find((s) => s.added === n || s.removed === n) ??
      null,
  };
}
