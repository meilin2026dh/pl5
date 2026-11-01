import { fitResidual } from "./residual";
import type { HistoryRecord } from "../pick5";
import { seededRandom } from "./config";
function snapshot(rows: HistoryRecord[]) {
  const digits = rows.map((r) => [...r.number].map(Number)),
    n = rows.length;
  const windows = [
    Math.max(1, Math.floor(n / 4)),
    Math.max(1, Math.floor(n / 2)),
    n,
  ];
  const counts = windows.map((w) =>
    Array.from({ length: 5 }, (_, p) =>
      Array.from(
        { length: 10 },
        (_, d) => digits.slice(-w).filter((r) => r[p] === d).length,
      ),
    ),
  );
  const ages = Array.from({ length: 5 }, (_, p) =>
    Array.from({ length: 10 }, (_, d) => {
      let i = digits.length - 1;
      while (i >= 0 && digits[i][p] !== d) i--;
      return i < 0 ? n : n - 1 - i;
    }),
  );
  const pairs = Array.from({ length: 5 }, () =>
    Array.from({ length: 5 }, () => Array(100).fill(0) as number[]),
  );
  for (const row of digits)
    for (let p = 0; p < 5; p++)
      for (let q = p + 1; q < 5; q++) pairs[p][q][row[p] * 10 + row[q]]++;
  const weights = counts[2].map((row) => row.map((c) => (c + 1) / (n + 10)));
  const features = (number: string) => {
    const d = [...number].map(Number),
      x: number[] = [];
    for (let p = 0; p < 5; p++) {
      for (let k = 0; k < 3; k++)
        x.push(((counts[k][p][d[p]] + 1) / (windows[k] + 10) - 0.1) * 10);
      const prob = weights[p][d[p]],
        mean = (1 - prob) / prob,
        sd = Math.sqrt(1 - prob) / prob;
      x.push(
        Math.max(-5, Math.min(5, (ages[p][d[p]] - mean) / sd)) / 5,
        Number(ages[p][d[p]] === n),
      );
    }
    for (let p = 0; p < 5; p++)
      for (let q = p + 1; q < 5; q++) {
        const joint = (pairs[p][q][d[p] * 10 + d[q]] + 1) / (n + 100);
        x.push(
          Math.max(
            -5,
            Math.min(
              5,
              Math.log(joint / (weights[p][d[p]] * weights[q][d[q]])),
            ),
          ) / 5,
        );
      }
    return x;
  };
  return { weights, features };
}
const sigmoid = (x: number) =>
  1 / (1 + Math.exp(-Math.max(-30, Math.min(30, x))));
type Sample = { x: number[]; y: number; issue: string };
function train(data: Sample[], hidden: number, rate: number, seed: number) {
  const random = seededRandom(seed),
    w = Array.from({ length: hidden }, () =>
      Array.from({ length: 35 }, () => (random() - 0.5) * 0.2),
    ),
    b = Array(hidden).fill(0) as number[],
    v = Array.from({ length: hidden }, () => (random() - 0.5) * 0.2);
  let out = 0;
  const forward = (x: number[]) => {
    const h = w.map((row, j) =>
      Math.tanh(row.reduce((s, a, i) => s + a * x[i], b[j])),
    );
    return { h, prob: sigmoid(h.reduce((s, a, j) => s + a * v[j], out)) };
  };
  for (let epoch = 0; epoch < 30; epoch++)
    for (const sample of data) {
      const { h, prob } = forward(sample.x),
        error = prob - sample.y;
      for (let j = 0; j < hidden; j++) {
        const dh = error * v[j] * (1 - h[j] * h[j]);
        for (let i = 0; i < 35; i++)
          w[j][i] -= rate * (dh * sample.x[i] + 0.001 * w[j][i]);
        b[j] -= rate * dh;
        v[j] -= rate * (error * h[j] + 0.001 * v[j]);
      }
      out -= rate * error;
    }
  return (x: number[]) => forward(x).prob;
}
export function learnScorer(
  rows: HistoryRecord[],
  kind: "bayes" | "neural" | "resnet",
  autoTune: boolean,
  seed: number,
) {
  if (rows.length < 40 || rows.length > 500)
    throw new Error("评分历史窗口须为40至500期");
  const current = snapshot(rows);
  if (kind === "bayes")
    return {
      weights: current.weights,
      score: (n: string) =>
        [...n].reduce(
          (s, d, p) => s + Math.log(current.weights[p][Number(d)]),
          0,
        ),
      diagnostics: {
        model: "Dirichlet逐位后验（每数字先验1）",
        trainingEnd: rows.at(-1)!.issue,
        features: 5,
        posteriorWeights: current.weights,
      },
    };
  if (kind === "resnet") {
    const fitted = fitResidual(rows, seed);
    return {
      weights: current.weights,
      score: (n: string) =>
        [...n].reduce(
          (s, d, p) => s + Math.log(fitted.probabilities[p][Number(d)]),
          0,
        ),
      diagnostics: {
        ...fitted.diagnostics,
        probabilities: fitted.probabilities,
      },
    };
  }
  const random = seededRandom(seed),
    samples: Sample[] = [];
  for (let t = 20; t < rows.length; t++) {
    const past = snapshot(rows.slice(0, t));
    let negative = String(Math.floor(random() * 100000)).padStart(5, "0");
    if (negative === rows[t].number)
      negative = String((Number(negative) + 1) % 100000).padStart(5, "0");
    samples.push(
      { x: past.features(rows[t].number), y: 1, issue: rows[t].issue },
      { x: past.features(negative), y: 0, issue: rows[t].issue },
    );
  }
  const split = Math.floor((rows.length - 20) * 0.8) * 2,
    trainSet = samples.slice(0, split),
    validation = samples.slice(split);
  const grid = autoTune
    ? [
        { hidden: 4, rate: 0.01 },
        { hidden: 4, rate: 0.03 },
        { hidden: 8, rate: 0.01 },
        { hidden: 8, rate: 0.03 },
      ]
    : [{ hidden: 8, rate: 0.01 }];
  const trials = grid.map((p) => {
    const predict = train(trainSet, p.hidden, p.rate, seed);
    const loss =
      validation.reduce((s, r) => {
        const v = Math.max(1e-9, Math.min(1 - 1e-9, predict(r.x)));
        return s - r.y * Math.log(v) - (1 - r.y) * Math.log(1 - v);
      }, 0) / validation.length;
    return { ...p, loss };
  });
  trials.sort((a, b) => a.loss - b.loss);
  const best = trials[0],
    predict = train(samples, best.hidden, best.rate, seed);
  return {
    weights: current.weights,
    score: (n: string) => predict(current.features(n)),
    diagnostics: {
      model: "35维特征→tanh浅层网络→对比结构分（非中奖概率）",
      trainingEnd: rows.at(-1)!.issue,
      features: 35,
      trainingTargets: samples.length / 2,
      validationStart: validation[0].issue,
      validationEnd: validation.at(-1)!.issue,
      trials,
      best,
      uniformLoss: Math.log(2),
      validationBeatsUniform: best.loss < Math.log(2),
      tuning: "时间留出网格比较；不是Optuna或贝叶斯优化",
      refit: "选参后用截止期内全部样本重新训练；留出损失来自重拟合前",
    },
  };
}
