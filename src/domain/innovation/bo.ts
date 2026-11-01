import { seededRandom } from "../selection/config";
const kernel = (a: number[], b: number[]) =>
  Math.exp(-a.reduce((s, v, i) => s + (v - b[i]) ** 2, 0) / 0.5);
function solve(a: number[][], b: number[]) {
  const n = b.length,
    L = Array.from({ length: n }, () => Array(n).fill(0) as number[]);
  for (let i = 0; i < n; i++)
    for (let j = 0; j <= i; j++) {
      let v = a[i][j];
      for (let k = 0; k < j; k++) v -= L[i][k] * L[j][k];
      L[i][j] = i === j ? Math.sqrt(Math.max(v, 1e-12)) : v / L[j][j];
    }
  const y = [...b],
    x = Array(n).fill(0) as number[];
  for (let i = 0; i < n; i++) {
    for (let k = 0; k < i; k++) y[i] -= L[i][k] * y[k];
    y[i] /= L[i][i];
  }
  for (let i = n - 1; i >= 0; i--) {
    let v = y[i];
    for (let k = i + 1; k < n; k++) v -= L[k][i] * x[k];
    x[i] = v / L[i][i];
  }
  return x;
}
export function posterior(xs: number[][], ys: number[], x: number[]) {
  if (!xs.length) return { mean: 0, sd: 1 };
  const K = xs.map((a, i) =>
      xs.map((b, j) => kernel(a, b) + (i === j ? 1e-6 : 0)),
    ),
    k = xs.map((a) => kernel(a, x));
  const alpha = solve(K, ys),
    beta = solve(K, k);
  return {
    mean: k.reduce((s, v, i) => s + v * alpha[i], 0),
    sd: Math.sqrt(Math.max(0, 1 - k.reduce((s, v, i) => s + v * beta[i], 0))),
  };
}
export function optimizeWeights(
  initial: number[],
  seed: number,
  evaluate: (w: number[]) => number,
) {
  const random = seededRandom(seed),
    normalize = (w: number[]) => w.map((v) => v / w.reduce((a, b) => a + b, 0));
  const candidates = [
    normalize(initial),
    ...[0, 1, 2, 3].map((i) => [0, 1, 2, 3].map((j) => Number(i === j))),
    ...Array.from({ length: 27 }, () =>
      normalize(Array.from({ length: 4 }, () => 0.01 + random())),
    ),
  ];
  const xs: number[][] = [],
    ys: number[] = [],
    trials: { weights: number[]; reward: number; mean: number; sd: number }[] =
      [];
  for (let t = 0; t < 12; t++) {
    const available = candidates.filter(
      (w) => !xs.some((x) => x.every((v, i) => v === w[i])),
    );
    const choices = available
      .map((weights) => ({ weights, ...posterior(xs, ys, weights) }))
      .sort((a, b) => b.mean + 2 * b.sd - (a.mean + 2 * a.sd));
    const next = choices[0],
      reward = evaluate(next.weights);
    xs.push(next.weights);
    ys.push(reward);
    trials.push({ ...next, reward });
  }
  const best = trials.reduce((a, b) => (b.reward > a.reward ? b : a));
  return {
    weights: best.weights,
    trials,
    kernel: "RBF lengthscale 0.5, jitter 1e-6",
    acquisition: "GP-UCB: mean + 2sd",
    policy: "12次有限权重策略实验；代理不确定性仅针对结构目标，不是中奖置信度",
  };
}
