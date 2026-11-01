import { Tape, type Vector } from "./autodiff";
import { seededRandom } from "./config";
import type { HistoryRecord } from "../pick5";
export type SequenceKind = "lstm" | "transformer";
import {
  defaultSequence,
  validateSequence,
  type SequenceConfig,
} from "./sequence-config";
export function initialSequence(kind: SequenceKind, seed: number) {
  const random = seededRandom(seed),
    w = Float64Array.from(
      { length: kind === "lstm" ? 234 : 246 },
      () => (random() - 0.5) * 0.4,
    );
  if (kind === "lstm") {
    for (let i = 168; i < 184; i++) w[i] = i >= 172 && i < 176 ? 1 : 0;
    for (let i = 224; i < 234; i++) w[i] = 0;
  } else {
    for (const o of [104, 188]) {
      for (let i = 0; i < 4; i++) {
        w[o + i] = 1;
        w[o + 4 + i] = 0;
      }
    }
    for (let i = 236; i < 246; i++) w[i] = 0;
  }
  return w;
}
function forward(kind: SequenceKind, w: Float64Array, context: number[]) {
  if (
    !context.length ||
    context.some((d) => !Number.isInteger(d) || d < 0 || d > 9) ||
    w.length !== (kind === "lstm" ? 234 : 246)
  )
    throw Error("时序模型输入错误");
  const t = new Tape(),
    p = (o: number, n: number) => t.param(w, o, n),
    e = p(0, 40),
    zero = (n = 4) => t.constant(Array(n).fill(0));
  let states: Vector[] = [],
    attention: number[][] = [];
  if (kind === "lstm") {
    let h = zero(),
      c = zero();
    for (const d of context) {
      const gates = t.affine(
          t.concat(t.embedding(e, d), h),
          p(40, 128),
          p(168, 16),
        ),
        i = t.activate(t.slice(gates, 0, 4), "sigmoid"),
        f = t.activate(t.slice(gates, 4, 4), "sigmoid"),
        g = t.activate(t.slice(gates, 8, 4), "tanh"),
        o = t.activate(t.slice(gates, 12, 4), "sigmoid");
      c = t.add(t.mul(f, c), t.mul(i, g));
      h = t.mul(o, t.activate(c, "tanh"));
      states.push(h);
    }
    return {
      t,
      states,
      attention,
      logits: t.affine(h, p(184, 40), p(224, 10)),
    };
  }
  const x = context.map((d, pos) =>
      t.add(
        t.embedding(e, d),
        t.constant(
          Array.from({ length: 4 }, (_, i) => {
            const phase = pos / 10000 ** ((2 * Math.floor(i / 2)) / 4);
            return i % 2 ? Math.cos(phase) : Math.sin(phase);
          }),
        ),
      ),
    ),
    q = x.map((v) => t.affine(v, p(40, 16), zero(0))),
    k = x.map((v) => t.affine(v, p(56, 16), zero(0))),
    v = x.map((v) => t.affine(v, p(72, 16), zero(0)));
  states = x.map((xx, pos) => {
    const a = t.attention(q[pos], k.slice(0, pos + 1), v.slice(0, pos + 1));
    attention.push(a.weights.v.concat(Array(context.length - pos - 1).fill(0)));
    const r = t.norm(
        t.add(xx, t.affine(a.out, p(88, 16), zero(0))),
        p(104, 4),
        p(108, 4),
      ),
      ff = t.affine(
        t.activate(t.affine(r, p(112, 32), p(144, 8)), "tanh"),
        p(152, 32),
        p(184, 4),
      );
    return t.norm(t.add(r, ff), p(188, 4), p(192, 4));
  });
  return {
    t,
    states,
    attention,
    logits: t.affine(states.at(-1)!, p(196, 40), p(236, 10)),
  };
}
export function sequencePredict(
  kind: SequenceKind,
  w: Float64Array,
  context: number[],
) {
  const f = forward(kind, w, context);
  return {
    probabilities: f.t.softmax(f.logits).v,
    tokenStates: f.states.map((s) => s.v),
    attention: f.attention,
  };
}
export function sequenceLoss(
  kind: SequenceKind,
  w: Float64Array,
  context: number[],
  target: number,
) {
  if (!Number.isInteger(target) || target < 0 || target > 9)
    throw Error("训练目标错误");
  const f = forward(kind, w, context);
  return {
    ...f.t.backward(f.logits, target, w.length),
    attention: f.attention,
  };
}
export function fitSequence(
  rows: HistoryRecord[],
  kind: SequenceKind,
  seed: number,
  config: SequenceConfig = defaultSequence,
) {
  validateSequence(config);
  if (rows.length < 80 || rows.length > 500)
    throw Error("时序评分历史须80—500期");
  const n = rows.length,
    trainEnd = Math.floor(n * 0.6),
    valEnd = Math.floor(n * 0.8),
    digits = rows.map((r) => [...r.number].map(Number)),
    initial = Array.from({ length: 5 }, (_, p) =>
      initialSequence(kind, seed + p * 991),
    ),
    weights = initial.map((w) => w.slice()),
    curves: { epoch: number; train: number; validation: number }[] = [];
  const contexts = (j: number, p: number) =>
    digits.slice(j - config.context, j).map((d) => d[p]);
  const evaluate = (ww: Float64Array[], start: number, end: number) => {
    let loss = 0,
      brier = 0;
    for (let j = start; j < end; j++)
      for (let p = 0; p < 5; p++) {
        const probs = sequencePredict(
          kind,
          ww[p],
          contexts(j, p),
        ).probabilities;
        loss -= Math.log(Math.max(probs[digits[j][p]], 1e-300));
        brier += probs.reduce(
          (s, a, d) => s + (a - Number(d === digits[j][p])) ** 2,
          0,
        );
      }
    return {
      loss: loss / ((end - start) * 5),
      brier: brier / ((end - start) * 5),
    };
  };
  const epoch = (ww: Float64Array[], end: number) => {
    let loss = 0;
    for (let j = config.context; j < end; j++) {
      const results = ww.map((w, p) =>
          sequenceLoss(kind, w, contexts(j, p), digits[j][p]),
        ),
        norm = Math.sqrt(
          results.reduce(
            (s, r) => s + r.gradient.reduce((a, g) => a + (g / 5) ** 2, 0),
            0,
          ),
        ),
        scale = Math.min(1, 5 / (norm || 1));
      results.forEach((r, p) => {
        loss += r.loss / 5;
        ww[p].forEach(
          (a, i) =>
            (ww[p][i] -= 0.02 * ((scale * r.gradient[i]) / 5 + 1e-4 * a)),
        );
      });
    }
    return loss / (end - config.context);
  };
  let best = Infinity,
    bestEpoch = 1,
    stale = 0,
    bestWeights = weights.map((w) => w.slice());
  for (let e = 1; e <= config.epochs; e++) {
    const train = epoch(weights, trainEnd),
      validation = evaluate(weights, trainEnd, valEnd).loss;
    curves.push({ epoch: e, train, validation });
    if (validation < best - 1e-5) {
      best = validation;
      bestEpoch = e;
      bestWeights = weights.map((w) => w.slice());
      stale = 0;
    } else if (++stale >= 3) break;
  }
  // Epoch is locked before the final diagnostic. Refit only training+validation, then freeze.
  const refit = initial.map((w) => w.slice());
  for (let e = 0; e < bestEpoch; e++) epoch(refit, valEnd);
  const diagnostic = evaluate(refit, valEnd, n),
    validationPredictions = [] as { probs: number[][]; target: number[] }[];
  for (let j = trainEnd; j < valEnd; j++)
    validationPredictions.push({
      probs: bestWeights.map(
        (w, p) => sequencePredict(kind, w, contexts(j, p)).probabilities,
      ),
      target: digits[j],
    });
  const candidates = [0, 0.25, 0.5, 0.75, 1].map((weight) => ({
      weight,
      loss:
        validationPredictions.reduce(
          (s, r) =>
            s +
            r.probs.reduce(
              (a, pp, p) =>
                a - Math.log((1 - weight) * 0.1 + weight * pp[r.target[p]]),
              0,
            ) /
              5,
          0,
        ) / validationPredictions.length,
    })),
    selected = candidates.reduce((a, b) => (b.loss < a.loss - 1e-12 ? b : a)),
    comparisons = candidates.map((x) => ({
      weight: x.weight,
      validationLoss: x.loss,
      loss: 0,
      brier: 0,
    }));
  for (let j = valEnd; j < n; j++)
    for (let p = 0; p < 5; p++) {
      const base = sequencePredict(
        kind,
        refit[p],
        contexts(j, p),
      ).probabilities;
      for (const r of comparisons) {
        const pp = base.map((a) => (1 - r.weight) * 0.1 + r.weight * a);
        r.loss -= Math.log(pp[digits[j][p]]) / ((n - valEnd) * 5);
        r.brier +=
          pp.reduce((s, a, d) => s + (a - Number(d === digits[j][p])) ** 2, 0) /
          ((n - valEnd) * 5);
      }
    }
  const blendedTest = comparisons.find((x) => x.weight === selected.weight)!;
  const predictions = refit.map((w, p) =>
      sequencePredict(
        kind,
        w,
        digits.slice(-config.context).map((d) => d[p]),
      ),
    ),
    probabilities = predictions.map((x) => x.probabilities),
    head = kind === "lstm" ? 184 : 196,
    changed = { embedding: 0, body: 0, head: 0 };
  refit.forEach((w, p) =>
    w.forEach((a, i) => {
      const key = i < 40 ? "embedding" : i < head ? "body" : "head";
      changed[key] += Math.abs(a - initial[p][i]);
    }),
  );
  return {
    probabilities,
    score: (number: string) =>
      [...number].reduce(
        (s, d, p) => s + Math.log(probabilities[p][Number(d)]),
        0,
      ),
    weights: probabilities,
    diagnostics: {
      model:
        kind === "lstm"
          ? "微型LSTM（全参数训练）"
          : "微型因果Transformer（全参数训练）",
      kind,
      seed,
      samples: {
        train: trainEnd - config.context,
        validation: valEnd - trainEnd,
        diagnostic: n - valEnd,
      },
      parameters: refit.reduce((s, w) => s + w.length, 0),
      context: config.context,
      epochs: curves.length,
      bestEpoch,
      curves,
      training: [rows[config.context].issue, rows[trainEnd - 1].issue],
      validation: [rows[trainEnd].issue, rows[valEnd - 1].issue],
      diagnostic: [rows[valEnd].issue, rows.at(-1)!.issue],
      validationLoss: best,
      diagnosticLoss: diagnostic.loss,
      diagnosticBrier: diagnostic.brier,
      uniformLoss: Math.log(10),
      uniformBrier: 0.9,
      mixture: {
        weight: selected.weight,
        trials: candidates,
        diagnostic: blendedTest,
        comparisons,
      },
      changed,
      probabilities,
      attention: predictions.map((x) => x.attention),
      currentContext: rows.slice(-config.context),
      identity:
        "TypeScript独立小模型，无预训练；窗口状态重置；冻结训练+验证重拟合模型；最后诊断段只评估。当前一步评分使用该冻结模型及最新已观察上下文。注意力不是因果解释。",
    },
  };
}
