import { filter, validateInput, type FilterInput } from "../pick5";
import { researchHistory } from "../research/statistics";
import { defaultResearch } from "../research/types";
import { rulesAtCutoff } from "../backtest";
import { conformal } from "../probability/sets";
import { seededRandom } from "../selection/config";
import { fitRatio, fitTensor, auc, diversify } from "./models";
import { validateDiscovery, type DiscoveryConfig } from "./config";
export type FoldReceipt = {
  start: string;
  end: string;
  hits: number;
  periods: number;
  expected: number;
  numbers: string[];
  ranges: Record<string, { start: string; end: string; count: number }>;
  modelDigest: string;
  validation: unknown;
  calibration: unknown;
  config: DiscoveryConfig;
};
export function analyzeDiscovery(
  input: FilterInput,
  c: DiscoveryConfig,
  progress?: (s: string) => void,
) {
  validateDiscovery(c);
  validateInput(input);
  const latest = researchHistory(
    { ...defaultResearch, window: 1, referenceIssue: c.referenceIssue },
    input.history,
  )[0];
  const total = c.train + c.validation + c.calibration + c.test;
  const all = input
    .history!.filter((r) => r.date <= latest.date)
    .sort((a, b) => a.date.localeCompare(b.date));
  if (all.length < total)
    throw Error(`历史不足：需要${total}期，实际${all.length}期`);
  const rows = all.slice(-total),
    train = rows.slice(0, c.train),
    val = rows.slice(c.train, c.train + c.validation),
    cal = rows.slice(c.train + c.validation, -c.test),
    test = rows.slice(-c.test);
  progress?.("只在训练段拟合对抗MLP与非负张量链");
  const ratio = fitRatio(
      train.map((r) => r.number),
      c.seed,
    ),
    tt = fitTensor(
      train.map((r) => r.number),
      c.rank,
      c.seed,
    );
  const rng = seededRandom(c.seed + 1),
    pairs = val.flatMap((r) => [
      { number: r.number, y: 1 },
      { number: String(Math.floor(rng() * 100000)).padStart(5, "0"), y: 0 },
    ]);
  const valAuc = auc(
    pairs.map((r) => ratio.score(r.number)),
    pairs.map((r) => r.y),
  );
  const bce =
    pairs.reduce((s, r) => {
      const z = ratio.score(r.number);
      return s + Math.log(1 + Math.exp(z)) - r.y * z;
    }, 0) / pairs.length;
  progress?.("全十万组合正规化；验证段选择均匀混合");
  const raw = Float64Array.from({ length: 100000 }, (_, i) =>
    c.model === "tensor"
      ? tt.prob(String(i).padStart(5, "0"))
      : Math.exp(ratio.score(String(i).padStart(5, "0"))),
  );
  const z = raw.reduce((s, x) => s + x, 0);
  for (let i = 0; i < raw.length; i++) raw[i] /= z;
  const trials = [0, 0.25, 0.5, 0.75, 1].map((weight) => ({
    weight,
    loss:
      val.reduce(
        (s, r) =>
          s - Math.log(weight * raw[Number(r.number)] + (1 - weight) / 100000),
        0,
      ) / val.length,
  }));
  trials.sort((a, b) => a.loss - b.loss || a.weight - b.weight);
  const weight = trials[0].weight;
  const pmf = Float64Array.from(raw, (p) => weight * p + (1 - weight) / 100000);
  const set = conformal(
      pmf,
      cal.map((r) => Number(r.number)),
      c.coverage,
    ),
    mask = new Set(set.indices);
  const cutoff = cal.at(-1)!.issue;
  const eligible = filter({
    ...input,
    history: all.filter((r) => r.date <= cal.at(-1)!.date),
    rules: rulesAtCutoff(input.rules, cutoff),
  }).numbers;
  const pool = eligible
    .filter((n) => mask.has(Number(n)))
    .sort((a, b) => pmf[Number(b)] - pmf[Number(a)] || a.localeCompare(b))
    .slice(0, c.pool);
  if (!pool.length)
    throw Error("当前来源域与校准集合交集为空，不能生成预算输出");
  progress?.("有界DPP贪心MAP；冻结集合时间外评估");
  const dpp = diversify(
      pool,
      pool.map((n) => Math.log(pmf[Number(n)])),
      Math.min(c.budget, pool.length),
      c.sigma,
    ),
    numbers = dpp.numbers;
  const budgetSet = new Set(numbers),
    covered = test.filter((r) => mask.has(Number(r.number))).length,
    hits = test.filter((r) => budgetSet.has(r.number)).length;
  const range = (rs: typeof rows) => ({
    start: rs[0].issue,
    end: rs.at(-1)!.issue,
    count: rs.length,
  });
  return {
    walkForward: undefined as undefined | FoldReceipt[],
    version: "discovery-v1",
    config: c,
    source: input.historySource ?? "未标注",
    cutoff: latest.issue,
    ranges: {
      train: range(train),
      validation: range(val),
      calibration: range(cal),
      test: range(test),
    },
    modelDigest: JSON.stringify({ ratio: ratio.parameters, tt: tt.parameters }),
    training: {
      ratioSamples: ratio.samples,
      tensorParameters: tt.count,
      tensorTrace: tt.trace,
    },
    validation: { auc: valAuc, bce, uniformBce: Math.log(2), trials, weight },
    calibration: {
      k: set.k,
      threshold: set.threshold,
      size: set.indices.length,
      indices: set.indices,
      coverageTarget: c.coverage,
    },
    dpp,
    pool,
    numbers,
    sourceSize: eligible.length,
    intersectionSize: eligible.filter((n) => mask.has(Number(n))).length,
    subsetGuarantee: false,
    evaluation: {
      periods: test.length,
      calibratedHits: covered,
      budgetHits: hits,
      expectedHits: (test.length * numbers.length) / 100000,
      lift: hits / ((test.length * numbers.length) / 100000),
      retention: numbers.length / 100000,
      elimination: 1 - numbers.length / 100000,
      loss:
        test.reduce((s, r) => s - Math.log(pmf[Number(r.number)]), 0) /
        test.length,
      uniformLoss: Math.log(100000),
    },
    note: "模型在训练后冻结，验证只选混合，校准和最终测试不参与拟合。本次预算输出属于该历史检验块之前锁定的集合，不是基于最新答案重拟合的下一期推荐。DPP后子集不继承校准覆盖保证。",
  };
}
export type DiscoveryResult = ReturnType<typeof analyzeDiscovery>;

export function walkDiscovery(
  input: FilterInput,
  c: DiscoveryConfig,
  progress?: (s: string) => void,
) {
  validateDiscovery(c);
  const latest = researchHistory(
    { ...defaultResearch, window: 1, referenceIssue: c.referenceIssue },
    input.history,
  )[0];
  const history = input
    .history!.filter((r) => r.date <= latest.date)
    .sort((a, b) => a.date.localeCompare(b.date));
  if (history.length < c.train + c.validation + c.calibration + 3 * c.test)
    throw Error("三折回放历史不足");
  const runs = [2, 1, 0].map((offset, i) => {
    progress?.(`第${i + 1}/3折重新训练`);
    const rows = history.slice(0, history.length - offset * c.test);
    return analyzeDiscovery(
      { ...input, history: rows },
      { ...c, referenceIssue: rows.at(-1)!.issue },
    );
  });
  const last = runs[2];
  return {
    ...last,
    walkForward: runs.map((r) => ({
      start: r.ranges.test.start,
      end: r.ranges.test.end,
      hits: r.evaluation.budgetHits,
      periods: r.evaluation.periods,
      expected: r.evaluation.expectedHits,
      numbers: r.numbers,
      ranges: r.ranges,
      modelDigest: r.modelDigest,
      validation: r.validation,
      calibration: r.calibration,
      config: r.config,
    })),
  };
}
