import type { HistoryRecord } from "../pick5";
import { seededRandom } from "./config";
// One chain: 10x4 projection, two causal k=3 convolutions, skip, pooling, 4x10 head.
const SIZE = 198,
  C = 4,
  L = 8;
export function initialResidual(seed: number): Float64Array {
  const random = seededRandom(seed);
  return Float64Array.from({ length: SIZE }, () => (random() - 0.5) * 0.2);
}
export function residualLoss(
  w: Float64Array,
  context: number[],
  target: number,
) {
  const n = context.length,
    zeros = () => Array.from({ length: n }, () => Array(C).fill(0) as number[]),
    h0 = zeros(),
    h1 = zeros(),
    res = zeros();
  for (let t = 0; t < n; t++)
    for (let o = 0; o < C; o++)
      h0[t][o] = Math.tanh(w[context[t] * C + o] + w[40 + o]);
  for (let t = 0; t < n; t++)
    for (let o = 0; o < C; o++) {
      let a = w[92 + o];
      for (let k = 0; k < 3; k++)
        if (t >= k)
          for (let i = 0; i < C; i++)
            a += w[44 + k * 16 + o * C + i] * h0[t - k][i];
      h1[t][o] = Math.tanh(a);
    }
  for (let t = 0; t < n; t++)
    for (let o = 0; o < C; o++) {
      let a = h0[t][o] + w[144 + o];
      for (let k = 0; k < 3; k++)
        if (t >= k)
          for (let i = 0; i < C; i++)
            a += w[96 + k * 16 + o * C + i] * h1[t - k][i];
      res[t][o] = Math.tanh(a);
    }
  const pool = Array.from(
      { length: C },
      (_, i) => res.reduce((s, row) => s + row[i], 0) / n,
    ),
    logits = Array.from({ length: 10 }, (_, d) =>
      pool.reduce((s, v, i) => s + v * w[148 + i * 10 + d], w[188 + d]),
    );
  const max = Math.max(...logits),
    exp = logits.map((v) => Math.exp(v - max)),
    total = exp.reduce((a, b) => a + b, 0),
    probabilities = exp.map((v) => v / total);
  const loss = max + Math.log(total) - logits[target],
    gradient = new Float64Array(SIZE),
    dpool = Array(C).fill(0) as number[];
  for (let d = 0; d < 10; d++) {
    const g = probabilities[d] - Number(d === target);
    gradient[188 + d] = g;
    for (let i = 0; i < C; i++) {
      gradient[148 + i * 10 + d] = g * pool[i];
      dpool[i] += g * w[148 + i * 10 + d];
    }
  }
  const d0 = zeros(),
    d1 = zeros();
  for (let t = 0; t < n; t++)
    for (let o = 0; o < C; o++) {
      const g = (dpool[o] / n) * (1 - res[t][o] * res[t][o]);
      d0[t][o] = g;
      gradient[144 + o] += g;
      for (let k = 0; k < 3; k++)
        if (t >= k)
          for (let i = 0; i < C; i++) {
            gradient[96 + k * 16 + o * C + i] += g * h1[t - k][i];
            d1[t - k][i] += g * w[96 + k * 16 + o * C + i];
          }
    }
  for (let t = 0; t < n; t++)
    for (let o = 0; o < C; o++) {
      const g = d1[t][o] * (1 - h1[t][o] * h1[t][o]);
      gradient[92 + o] += g;
      for (let k = 0; k < 3; k++)
        if (t >= k)
          for (let i = 0; i < C; i++) {
            gradient[44 + k * 16 + o * C + i] += g * h0[t - k][i];
            d0[t - k][i] += g * w[44 + k * 16 + o * C + i];
          }
    }
  for (let t = 0; t < n; t++)
    for (let o = 0; o < C; o++) {
      const g = d0[t][o] * (1 - h0[t][o] * h0[t][o]);
      gradient[context[t] * C + o] += g;
      gradient[40 + o] += g;
    }
  return { loss, gradient, probabilities };
}
function train(chain: number[], end: number, seed: number) {
  const w = initialResidual(seed);
  for (let epoch = 0; epoch < 15; epoch++)
    for (let t = L; t < end; t++) {
      const { gradient } = residualLoss(w, chain.slice(t - L, t), chain[t]);
      for (let i = 0; i < SIZE; i++)
        w[i] -= 0.02 * (gradient[i] + 0.001 * w[i]);
    }
  return w;
}
export function fitResidual(rows: HistoryRecord[], seed: number) {
  if (rows.length < 40 || rows.length > 500)
    throw new Error("残差模型需要40—500期历史");
  const cut = L + Math.floor((rows.length - L) * 0.8),
    chains = Array.from({ length: 5 }, (_, p) =>
      rows.map((r) => Number(r.number[p])),
    );
  let validationLoss = 0,
    markovLoss = 0;
  const probabilities = chains.map((chain, p) => {
    const trained = train(chain, cut, (seed + p) >>> 0),
      matrix = Array.from({ length: 10 }, () => Array(10).fill(0) as number[]);
    for (let t = 1; t < cut; t++) matrix[chain[t - 1]][chain[t]]++;
    for (let t = cut; t < chain.length; t++) {
      validationLoss += residualLoss(
        trained,
        chain.slice(t - L, t),
        chain[t],
      ).loss;
      const row = matrix[chain[t - 1]],
        count = row.reduce((a, b) => a + b, 0);
      markovLoss -= Math.log((row[chain[t]] + 1) / (count + 10));
    }
    const final = train(chain, chain.length, (seed + p) >>> 0);
    return residualLoss(final, chain.slice(-L), 0).probabilities;
  });
  return {
    probabilities,
    diagnostics: {
      model: "微型因果Conv1D残差网络：五条位置链独立训练",
      context: L,
      channels: C,
      kernel: 3,
      residualBlocks: 1,
      parameters: SIZE * 5,
      epochs: 15,
      learningRate: 0.02,
      seed,
      trainingTargets: rows.length - L,
      trainingEnd: rows.at(-1)!.issue,
      validationStart: rows[cut].issue,
      validationEnd: rows.at(-1)!.issue,
      validationLoss: validationLoss / ((rows.length - cut) * 5),
      markovValidationLoss: markovLoss / ((rows.length - cut) * 5),
      uniformLoss: Math.log(10),
      policy:
        "前80%目标训练、后20%时间留出；再用全部截止期数据重训。五位置log后验相加作为形态分，不证明预测优势。",
    },
  };
}
