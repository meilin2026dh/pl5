import {
  filter,
  validateInput,
  type FilterInput,
  type HistoryRecord,
} from "../pick5";
import { rulesAtCutoff } from "../backtest";
import { researchHistory } from "../research/statistics";
import { defaultResearch } from "../research/types";
import { inspectQuality } from "../evidence/statistics";
import { validateProbability, type ProbabilityConfig } from "./config";
import {
  evidence,
  fitModel,
  kinds,
  priors,
  names,
  pmf,
  probability,
  updateModel,
  type Kind,
} from "./models";
import { conformal, numberAt, wilson, rng } from "./sets";
import { transportProfile, transportBounds } from "./transport";
import { onlineReplay, type OnlineState } from "./online";
import { diversify, hypergraphCoverage } from "./hypergraph";
const range = (r: HistoryRecord[]) => [r[0].issue, r.at(-1)!.issue];
function gainSummary(g: number[]) {
  const mean = g.reduce((a, b) => a + b, 0) / g.length,
    variance = g.reduce((a, b) => a + (b - mean) ** 2, 0) / (g.length - 1);
  return {
    mean,
    low: mean - 1.96 * Math.sqrt(variance / g.length),
    blocks: [0, 20, 40].map(
      (i) => g.slice(i, i + 20).reduce((a, b) => a + b, 0) / 20,
    ),
  };
}
export function analyzeProbability(
  input: FilterInput,
  c: ProbabilityConfig,
  progress?: (s: string) => void,
  previous?: OnlineState,
) {
  validateProbability(c);
  validateInput({ ...input, probability: c });
  const fullQuality = inspectQuality(input.history);
  if (fullQuality.errors.length)
    throw Error("历史数据质量错误：" + fullQuality.errors.join("；"));
  if (input.history!.length > 10000) throw Error("概率实验最多10000条历史");
  const last = researchHistory(
      { ...defaultResearch, window: 1, referenceIssue: c.referenceIssue },
      input.history,
    )[0],
    rows = input
      .history!.filter((r) => r.date <= last.date)
      .sort((a, b) => a.date.localeCompare(b.date));
  if (rows.length < c.train + c.calibration + c.test)
    throw Error("历史不足训练、校准和测试窗口");
  const all = rows.slice(-c.train - c.calibration - c.test),
    train = all.slice(0, c.train),
    fit = train.slice(0, -60),
    gateRows = train.slice(-60),
    cal = all.slice(c.train, c.train + c.calibration),
    test = all.slice(c.train + c.calibration);
  progress?.("拟合有限联合模型与贝叶斯证据");
  const ev = evidence(fit, c.strength),
    chosen = ev.slice(1).reduce((a, b) => (a.posterior >= b.posterior ? a : b)),
    m = fitModel(chosen.kind, fit, c.strength),
    gains: number[] = [];
  for (const r of gateRows) {
    gains.push(Math.log(probability(m, r.number) * 100000));
    updateModel(m, r.number);
  }
  const gain = gainSummary(gains),
    reasons: string[] = [];
  if (ev[0].posterior >= 0.05) reasons.push("训练前部均匀模型后验不低于5%");
  if (chosen.logBF < Math.log(20)) reasons.push("最佳替代模型BF不足20");
  if (gain.low <= 0) reasons.push("训练内60期门控增益近似区间未通过");
  if (gain.blocks.some((x) => x <= 0)) reasons.push("门控20期分块存在非正增益");
  if (c.uniformOnly) reasons.push("用户选择只用均匀基线");
  const useBias = !reasons.length,
    kind: Kind = useBias ? chosen.kind : "U",
    models = kinds.map((k) => fitModel(k, train, c.strength)),
    ps = models.map(pmf),
    p = ps[kinds.indexOf(kind)],
    calIds = cal.map((r) => Number(r.number));
  progress?.("冻结模型并校准完整十万候选");
  const cs = conformal(p, calIds, c.target),
    mask = new Uint8Array(100000);
  cs.indices.forEach((i) => (mask[i] = 1));
  const hits = test.filter((r) => mask[Number(r.number)]).length,
    testLoss =
      test.reduce((a, r) => a - Math.log(p[Number(r.number)]), 0) / test.length;
  const individual = ps.map((p) => conformal(p, calIds, c.target));
  const mixture = (omit = -1) =>
    Float64Array.from(
      { length: 100000 },
      (_, n) =>
        ps.reduce((s, p, i) => s + (i === omit ? 0 : p[n]), 0) /
        (omit < 0 ? 4 : 3),
    );
  const mixed = conformal(mixture(), calIds, c.target),
    mixedMask = new Uint8Array(100000);
  mixed.indices.forEach((i) => (mixedMask[i] = 1));
  const sensitivity = kinds.map((k, i) => {
    const s = conformal(mixture(i), calIds, c.target),
      m = new Uint8Array(100000);
    s.indices.forEach((n) => (m[n] = 1));
    let changed = 0;
    for (let n = 0; n < m.length; n++) changed += Number(m[n] !== mixedMask[n]);
    return { removed: k, size: s.indices.length, changed };
  });
  let js = 0;
  const top: {
    number: string;
    probabilities: number[];
    contribution: number;
  }[] = [];
  for (let n = 0; n < 100000; n++) {
    const pp = ps.map((p) => p[n]),
      mean = pp.reduce((a, b) => a + b, 0) / 4,
      contribution = pp.reduce((a, p) => a + (p * Math.log(p / mean)) / 4, 0);
    js += contribution;
    if (top.length < 20 || contribution > top.at(-1)!.contribution) {
      top.push({ number: numberAt(n), probabilities: pp, contribution });
      top.sort((a, b) => b.contribution - a.contribution);
      if (top.length > 20) top.pop();
    }
  }
  progress?.("预算、二三元结构覆盖与来源约束");
  const source = filter({
      ...input,
      probability: c,
      history: rows.filter((r) => r.date <= cal.at(-1)!.date),
      rules: rulesAtCutoff(input.rules, cal.at(-1)!.issue),
    }).numbers.map(Number),
    eligible = new Set(source),
    random = rng(c.seed),
    order = [...source];
  for (let i = order.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [order[i], order[j]] = [order[j], order[i]];
  }
  let ids: number[];
  const selectionStages: Record<string, string> = {},
    searchShortlist: number[] = [];
  const onPick = (n: number, stage: string) => {
    selectionStages[numberAt(n)] = stage;
  };
  if (!useBias) {
    ids = order.slice(0, c.budget);
    ids.forEach((n) => onPick(n, "uniform"));
  } else {
    const ranked = order.sort((a, b) => p[b] - p[a]),
      inside = ranked.filter((n) => mask[n]),
      outside = ranked.filter((n) => !mask[n]);
    searchShortlist.push(
      ...(inside.length <= c.budget ? outside : inside).slice(0, 512),
    );
    if (inside.length <= c.budget) {
      inside.forEach((n) => onPick(n, "conformal-retain"));
      ids = inside.concat(diversify(outside, c.budget - inside.length, onPick));
    } else ids = diversify(inside, c.budget, onPick);
  }
  const selected = new Set(ids),
    budgetMask = new Uint8Array(100000);
  ids.forEach((n) => (budgetMask[n] = 1));
  const inheritsCoverage = cs.indices.every((n) => selected.has(n));
  const portfolio = {
    numbers: ids.map(numberAt),
    base: source.length,
    exactProbability: ids.length / 100000,
    missProbability: 1 - ids.length / 100000,
    inheritsCoverage,
    policy: useBias
      ? "门控模型排序；前512短名单最多100轮超图贪心，余量按模型分填充"
      : "证据不足：来源域内均匀无放回抽样（结构覆盖仅测量）",
  };
  const hypergraph = hypergraphCoverage(ids),
    sourceRestricted = eligible.size < 100000;
  progress?.("汉明最优传输压力认证");
  const profile = transportProfile(budgetMask, ps),
    radii = [...new Set([0, 0.005, 0.01, 0.05, c.radius])].sort(
      (a, b) => a - b,
    ),
    robustness = radii.map((radius) => {
      const bounds = transportBounds(profile, radius);
      return {
        radius,
        bounds,
        worstLower: Math.min(...bounds.map((x) => x.lower)),
      };
    });
  progress?.("逐期在线专家与遗憾核查");
  const online = onlineReplay(
    train,
    cal.concat(test),
    c.strength,
    input.historySource ?? "未标注",
    previous,
  );
  const codeModels = kinds.map((k) => fitModel(k, [], c.strength)),
    codeCurve = fit.map((r) => {
      codeModels.forEach((m) => updateModel(m, r.number));
      return {
        issue: r.issue,
        bits: codeModels.map(
          (m, i) => (-m.logEvidence - Math.log(priors[i])) / Math.LN2,
        ),
      };
    });
  const sensitivityPrior = [c.strength / 2, c.strength, c.strength * 2].map(
    (strength) => ({ strength, evidence: evidence(fit, strength) }),
  );
  return {
    version: "probability-v1" as const,
    source: input.historySource ?? "未标注",
    cutoff: last.issue,
    config: c,
    quality: inspectQuality(rows),
    ranges: {
      fit: range(fit),
      gate: range(gateRows),
      train: range(train),
      calibration: range(cal),
      test: range(test),
    },
    evidence: ev,
    sensitivityPrior,
    codeCurve,
    gate: { kind, useBias, reasons, gain, chosen: chosen.kind },
    models,
    conformal: cs,
    conformalByModel: individual.map((s, i) => ({
      kind: kinds[i],
      size: s.indices.length,
      threshold: s.threshold,
    })),
    calibrationNumbers: calIds,
    validation: {
      hits,
      n: test.length,
      coverage: hits / test.length,
      wilson: wilson(hits, test.length),
      testLoss,
      budgetHits: test.filter((r) => selected.has(Number(r.number))).length,
      budgetWilson: wilson(
        test.filter((r) => selected.has(Number(r.number))).length,
        test.length,
      ),
      uniformLoss: Math.log(100000),
      uniformSetCoverage: cs.indices.length / 100000,
    },
    disagreement: { js, top, mixtureSize: mixed.indices.length, sensitivity },
    ranking: order,
    rankBasis: useBias ? "模型概率降序，种子打破并列" : "均匀种子随机顺序",
    selectionStages,
    searchShortlist,
    sourceIndices: source,
    sourceRestricted,
    conflict: cs.indices.length > c.budget,
    portfolio,
    hypergraph,
    transport: profile,
    robustness,
    online: {
      ...online,
      outputLoss: cal
        .concat(test)
        .reduce((a, r) => a - Math.log(p[Number(r.number)]), 0),
      outputPolicy: kind,
    },
    guard: {
      unique: selected.size === ids.length,
      withinBudget: ids.length <= c.budget,
      source: ids.every((n) => eligible.has(n)),
    },
    notice: useBias
      ? "预设门控通过；仅启用研究偏置，不证明预测优势"
      : "证据不足，采用均匀基线；完整校准集合与预算组合分开报告",
  };
}
export type ProbabilityResult = ReturnType<typeof analyzeProbability>;
export function inspectNumber(r: ProbabilityResult, n: string) {
  if (!/^\d{5}$/.test(n)) throw Error("请输入五位号码");
  const ps = r.models.map((m) => probability(m, n)),
    p = ps[kinds.indexOf(r.gate.kind)],
    score = -Math.log(p),
    threshold = r.conformal.threshold;
  return {
    number: n,
    probabilities: ps,
    score,
    threshold,
    conformal: threshold === null || score <= threshold + 1e-12,
    boundary: threshold !== null && Math.abs(score - threshold) < 1e-12,
    rank:
      r.ranking.indexOf(Number(n)) < 0
        ? null
        : r.ranking.indexOf(Number(n)) + 1,
    rankBasis: r.rankBasis,
    stage: r.selectionStages[n] ?? "not-selected",
    shortlisted: r.searchShortlist.includes(Number(n)),
    sourceEligible: r.sourceIndices.includes(Number(n)),
    selected: r.portfolio.numbers.includes(n),
    reason: !r.sourceIndices.includes(Number(n))
      ? "原始来源/规则域不允许；校准全集声明不适用于此相交集合"
      : r.portfolio.numbers.includes(n)
        ? "预算组合已选"
        : r.conformal.indices.includes(Number(n))
          ? "校准集合保留；预算/来源或排序未选"
          : "校准分数超过阈值；不代表更难开奖",
  };
}
