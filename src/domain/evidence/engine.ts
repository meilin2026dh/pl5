import { filter, type FilterInput, type HistoryRecord } from "../pick5";
import { rulesAtCutoff } from "../backtest";
import { researchHistory } from "../research/statistics";
import { defaultResearch } from "../research/types";
import { seededRandom } from "../selection/config";
import { hamming } from "../innovation/engine";
import { validateEvidence, type EvidenceConfig } from "./config";
import {
  inspectQuality,
  frequencyStatistic,
  repeatStatistic,
  serialStatistic,
  changeStatistic,
  randomizationP,
  holm,
  uniformMartingale,
} from "./statistics";
import {
  probabilities,
  blend,
  evaluate,
  summarize,
  improvement,
  chooseModel,
  calibrate,
  modelName,
  mean,
  type Hypothesis,
} from "./models";
export type Check = {
  label: string;
  nullModel: string;
  stat: number;
  p: number;
  adjusted: number;
  end: string;
  split?: string;
};
function range(rows: HistoryRecord[], a: number, b: number) {
  return [rows[a].issue, rows[b - 1].issue];
}
export function temporalValidation(rows: HistoryRecord[], c: EvidenceConfig) {
  const end = rows.length,
    testStart = end - c.test,
    calStart = testStart - c.calibration,
    tuneStart = calStart - c.tune;
  if (tuneStart < c.window)
    throw Error("历史不足：需要训练窗＋调参段＋校准段＋最终检验段");
  const selection = chooseModel(rows, tuneStart, calStart, c.window),
    calibration = calibrate(rows, calStart, testStart, selection.model),
    scores = evaluate(
      rows,
      testStart,
      end,
      selection.model,
      calibration.weight,
    ),
    metrics = summarize(scores),
    gain = improvement(scores);
  const blocks = Array.from({ length: 3 }, (_, j) => {
    const start = testStart + Math.floor((j * c.test) / 3),
      stop = testStart + Math.floor(((j + 1) * c.test) / 3);
    const ownCalStart = start - c.calibration,
      ownTuneStart = ownCalStart - c.tune,
      localSelection = chooseModel(rows, ownTuneStart, ownCalStart, c.window),
      localCal = calibrate(rows, ownCalStart, start, localSelection.model);
    return {
      range: range(rows, start, stop),
      locked: improvement(scores.slice(start - testStart, stop - testStart)),
      reselected: modelName(localSelection.model),
      weight: localCal.weight,
      selectionRange: range(rows, ownTuneStart, ownCalStart),
      calibrationRange: range(rows, ownCalStart, start),
      reselectedGain: improvement(
        evaluate(rows, start, stop, localSelection.model, localCal.weight),
      ),
    };
  });
  const variants = [
    ...new Set([
      Math.max(40, selection.model.window - 20),
      selection.model.window,
      Math.min(c.window, selection.model.window + 20),
    ]),
  ].map((window) => ({
    window,
    ...improvement(
      evaluate(
        rows,
        testStart,
        end,
        { ...selection.model, window },
        calibration.weight,
      ),
    ),
  }));
  const comparisons = (["uniform", "iid", "markov"] as const).map((kind) => ({
    name: kind,
    ...summarize(
      evaluate(rows, testStart, end, { kind, window: c.window, alpha: 1 }),
    ),
  }));
  const reasons: string[] = [];
  if (selection.model.kind === "uniform" || calibration.weight === 0)
    reasons.push("调参或校准选择了均匀基线");
  if (c.test < 60) reasons.push("最终检验少于60期");
  if (gain.low <= 0) reasons.push("按开奖期聚合的增益近似95%区间未完全大于0");
  if (blocks.some((b) => b.locked.mean <= 0))
    reasons.push("至少一个最终时间片没有优于均匀评分");
  if (variants.some((v) => v.mean <= 0)) reasons.push("邻近历史窗口存在退化");
  if (metrics.ece > 0.05) reasons.push("顶标签校准偏差大于预设0.05");
  if (gain.maxSingleShare > 0.2 || gain.leaveOneWorst <= 0)
    reasons.push("增益依赖少数期或删除单期后不稳健");
  return {
    ranges: {
      tune: range(rows, tuneStart, calStart),
      calibration: range(rows, calStart, testStart),
      test: range(rows, testStart, end),
    },
    model: selection.model,
    modelName: modelName(selection.model),
    selection: selection.trials,
    calibration,
    metrics,
    gain,
    blocks,
    variants,
    comparisons,
    reasons,
    independentTest: true,
    policy:
      "逐期只读取此前记录；模型/混合权重在最终段锁定，计数随已公布记录滚动更新。区间是按期配对正态近似，不是时间一致证明。",
  };
}
export function analyzeEvidence(
  input: FilterInput,
  c: EvidenceConfig,
  progress?: (s: string) => void,
) {
  validateEvidence(c);
  const quality = inspectQuality(input.history);
  if (quality.errors.length)
    return {
      quality,
      blocked: true as const,
      notice: "数据质量未通过；未运行统计检验",
    };
  if (input.history!.length > 10000) throw Error("证据体检最多10000条历史快照");
  const latest = researchHistory(
      { ...defaultResearch, window: 1, referenceIssue: c.referenceIssue },
      input.history,
    )[0],
    rows = input
      .history!.filter((r) => r.date <= latest.date)
      .sort((a, b) => a.date.localeCompare(b.date));
  if (
    rows.length <
    Math.max(
      c.window + c.tune + c.calibration + c.test,
      c.monitor + (c.checks - 1) * 20,
    )
  )
    throw Error("历史不足：请减少训练/校准/检验窗口或滚动检查数");
  const checks: Check[] = [],
    monitor = rows.slice(-c.monitor),
    digits = monitor.map((r) => [...r.number].map(Number));
  progress?.("均匀频率零假设模拟");
  const frequency = randomizationP(
    digits,
    frequencyStatistic,
    c.resamples,
    c.seed,
    true,
  );
  checks.push({
    label: "逐位均匀频率",
    nullModel: "五位置、各期独立均匀",
    ...frequency,
    adjusted: 1,
    end: latest.issue,
  });
  const repeat = randomizationP(
    digits,
    repeatStatistic,
    c.resamples,
    c.seed ^ 0x77777777,
    true,
  );
  checks.push({
    label: "单期重复结构",
    nullModel: "五位置独立均匀；不同数字数分布",
    ...repeat,
    adjusted: 1,
    end: latest.issue,
  });
  progress?.("保留整期向量的时间置换");
  const serial = randomizationP(
    digits,
    serialStatistic,
    c.resamples,
    c.seed ^ 0x11223344,
  );
  checks.push({
    label: "相邻期依赖",
    nullModel: "整期记录可交换（保留每期五位联合结构）",
    ...serial,
    adjusted: 1,
    end: latest.issue,
  });
  for (let j = 0; j < c.checks; j++) {
    progress?.(`滚动变点检查 ${j + 1}/${c.checks}`);
    const end = rows.length - (c.checks - 1 - j) * 20,
      window = rows.slice(end - c.monitor, end),
      d = window.map((r) => [...r.number].map(Number)),
      observed = changeStatistic(d),
      permutation = randomizationP(
        d,
        (r) => changeStatistic(r).stat,
        c.resamples,
        (c.seed + j + 1) >>> 0,
      );
    checks.push({
      label: `滚动变点 ${j + 1}`,
      nullModel: "窗口内整期记录可交换，最大统计量包含所有候选切点",
      ...permutation,
      adjusted: 1,
      end: window.at(-1)!.issue,
      split: window[observed.cut].issue,
    });
  }
  const martingale = uniformMartingale(rows);
  checks.push({
    label: "固定起点均匀性序贯证据",
    nullModel: "从所示固定起点开始各期五位独立均匀",
    stat: martingale.maxLogE,
    p: martingale.anytimeP,
    adjusted: 1,
    end: latest.issue,
  });
  const adjusted = holm(checks.map((t) => t.p));
  checks.forEach((t, i) => (t.adjusted = adjusted[i]));
  progress?.("调参→校准→最终时间外检验");
  const validation = temporalValidation(rows, c),
    randomnessEvidence = checks.some((t) => t.adjusted <= c.alpha),
    reasons = [...validation.reasons];
  if (!randomnessEvidence) reasons.push("本次多重校正检验没有异常证据");
  const useBias = reasons.length === 0;
  const latestChange = checks.find((t) => t.label === `滚动变点 ${c.checks}`),
    changeCount = checks.filter(
      (t) => t.label.startsWith("滚动变点") && t.adjusted <= c.alpha,
    ).length;
  const recommendedWindow =
    latestChange && latestChange.adjusted <= c.alpha
      ? Math.min(
          c.window,
          Math.max(
            40,
            rows.length - rows.findIndex((r) => r.issue === latestChange.split),
          ),
        )
      : c.window;
  const hypotheses: Hypothesis[] = [
      { kind: "uniform", window: c.window, alpha: 1 },
      { kind: "iid", window: c.window, alpha: 1 },
      { kind: "markov", window: c.window, alpha: 1 },
    ],
    tables = hypotheses.map((m) => probabilities(rows, m));
  progress?.("完整号码空间的模型分歧");
  let js = 0;
  const disputed: {
    number: string;
    probabilities: number[];
    contribution: number;
    logRange: number;
  }[] = [];
  for (let i = 0; i < 100000; i++) {
    const number = String(i).padStart(5, "0"),
      ps = tables.map((table) =>
        [...number].reduce((p, d, j) => p * table[j][Number(d)], 1),
      ),
      m = mean(ps),
      contribution = ps.reduce((s, p) => s + (p * Math.log(p / m)) / 3, 0);
    js += contribution;
    disputed.push({
      number,
      probabilities: ps,
      contribution,
      logRange: Math.log(Math.max(...ps) / Math.min(...ps)),
    });
  }
  disputed.sort(
    (a, b) =>
      b.contribution - a.contribution || a.number.localeCompare(b.number),
  );
  progress?.("最大最小距离候选组合与预算核验");
  const base = filter({
    ...input,
    history: rows,
    rules: rulesAtCutoff(input.rules, latest.issue),
    evidence: undefined,
  }).numbers;
  const random = seededRandom(c.seed ^ 0x55aa55aa),
    shuffled = [...base];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  const table = useBias
      ? blend(
          probabilities(rows, validation.model),
          validation.calibration.weight,
        )
      : tables[0],
    score = (n: string) =>
      [...n].reduce((s, d, p) => s + Math.log(table[p][Number(d)]), 0);
  const ranked = useBias
    ? [...base]
        .sort((a, b) => score(b) - score(a) || a.localeCompare(b))
        .slice(0, 256)
    : [];
  const pool = [
      ...new Set([...ranked, ...shuffled.slice(0, useBias ? 256 : 512)]),
    ],
    selected: string[] = [];
  while (selected.length < Math.min(c.budget, pool.length)) {
    let best: string | null = null,
      distance = -1,
      bestScore = -Infinity;
    for (const n of pool)
      if (!selected.includes(n)) {
        const d = selected.length
            ? Math.min(...selected.map((s) => hamming(n, s)))
            : 5,
          v = score(n);
        if (d > distance || (d === distance && v > bestScore)) {
          distance = d;
          bestScore = v;
          best = n;
        }
      }
    if (best === null) break;
    selected.push(best);
  }
  const minDistance =
    selected.length < 2
      ? null
      : Math.min(
          ...selected.flatMap((a, i) =>
            selected.slice(i + 1).map((b) => hamming(a, b)),
          ),
        );
  if (
    selected.length > c.budget ||
    new Set(selected).size !== selected.length ||
    selected.some((n) => !base.includes(n))
  )
    throw Error("证据组合Guard失败");
  return {
    quality,
    blocked: false as const,
    notice: "体检完成；统计告警不等于预测优势",
    cutoff: latest.issue,
    source: input.historySource ?? "未标注",
    config: c,
    checks,
    martingale,
    validation,
    recommendation: {
      useBias,
      policy: useBias ? "通过预设实验门槛的校准评分" : "均匀评分回退",
      reasons,
      changeCount,
      recommendedWindow,
      windowApplied: false,
      warning: "缩窗只作复核建议，未在最终检验后改动已锁定策略；需重新验证",
    },
    disagreement: {
      js,
      models: hypotheses.map(modelName),
      top: disputed.slice(0, 20),
      interpretation: "三模型全空间JS分歧；高分是复核优先级，不是中奖概率",
    },
    portfolio: {
      numbers: selected,
      base: base.length,
      pool: pool.length,
      minDistance,
      budget: c.budget,
      exactProbability: selected.length / 100000,
      policy: useBias
        ? "锁定校准评分＋短名单最大最小距离"
        : "均匀评分＋固定种子抽样短名单最大最小距离",
      guard: true,
    },
    limits:
      "检验不证明公平或不公平。多重校正仅本次预设检验家族；滚动置换不是任意停止保证。最终段用于门槛决策，不可反复调参后仍称未见测试。",
  };
}
export type EvidenceResult = ReturnType<typeof analyzeEvidence>;
