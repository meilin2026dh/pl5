import { Tape, type Vector } from "../selection/autodiff";
import { init, scale, sum, update, changed, cosine } from "./neural-common";
import { seededRandom } from "../selection/config";
export const contrastInitial = (seed: number) => init(220, seed);
function encode(t: Tape, w: Float64Array, s: string) {
  const emb = t.param(w, 0, 200),
    xs = [...s].map((d, p) =>
      d === "?"
        ? t.constant([0, 0, 0, 0])
        : t.slice(emb, (p * 10 + Number(d)) * 4, 4),
    );
  return t.activate(
    t.affine(
      scale(t, sum(t, xs), 0.2),
      t.param(w, 200, 16),
      t.param(w, 216, 4),
    ),
    "tanh",
  );
}
function similarities(t: Tape, a: Vector, bs: Vector[]) {
  return t.node(
    bs.map((b) => cosine(a.v, b.v) / 0.2),
    (n) => {
      bs.forEach((b, j) => {
        const na = Math.sqrt(a.v.reduce((s, x) => s + x * x, 0) + 1e-8),
          nb = Math.sqrt(b.v.reduce((s, x) => s + x * x, 0) + 1e-8),
          c = cosine(a.v, b.v),
          g = n.g[j] / 0.2;
        for (let k = 0; k < 4; k++) {
          a.g[k] += g * (b.v[k] / (na * nb) - (c * a.v[k]) / (na * na));
          b.g[k] += g * (a.v[k] / (na * nb) - (c * b.v[k]) / (nb * nb));
        }
      });
    },
  );
}
export function contrastLoss(w: Float64Array, batch: string[]) {
  const t = new Tape(),
    vectors = batch.map((s) => encode(t, w, s)),
    out = similarities(t, vectors[0], vectors.slice(1));
  return t.backward(out, 0, w.length);
}
function numeric(w: Float64Array, s: string) {
  const pooled = [0, 0, 0, 0];
  for (let p = 0; p < 5; p++)
    if (s[p] !== "?")
      for (let k = 0; k < 4; k++)
        pooled[k] += 0.2 * w[(p * 10 + Number(s[p])) * 4 + k];
  return pooled.map((_, o) =>
    Math.tanh(
      w[216 + o] + pooled.reduce((s, v, k) => s + v * w[200 + o * 4 + k], 0),
    ),
  );
}
export function fitContrast(rows: string[], seed: number) {
  const unique = [...new Set(rows)];
  if (unique.length < 3)
    throw Error("对比表示至少需要3种不同历史号码，不能制造伪异常标签");
  const w = contrastInitial(seed),
    old = w.slice(),
    rng = seededRandom(seed),
    trace: number[] = [];
  for (let epoch = 0; epoch < 3; epoch++) {
    let loss = 0;
    for (let i = 0; i < rows.length; i++) {
      const s = rows[i],
        p = Math.floor(rng() * 5),
        positive = s.slice(0, p) + "?" + s.slice(p + 1),
        negatives = unique.filter((n) => n !== s),
        j = Math.floor(rng() * negatives.length),
        r = contrastLoss(w, [
          s,
          positive,
          negatives[j],
          negatives[(j + 1) % negatives.length],
        ]);
      loss += r.loss;
      update(w, r.gradient, 0.005);
    }
    trace.push(loss / rows.length);
  }
  const prototypes = unique.map((s) => numeric(w, s));
  return {
    score: (s: string) => {
      const v = numeric(w, s);
      return Math.max(...prototypes.map((p) => cosine(v, p))) / 0.2;
    },
    parameters: Array.from(w),
    prototypes,
    trace,
    changed: changed(w, old),
    parameterCount: w.length,
    settings: {
      epochs: 3,
      rate: 0.005,
      l2: 0.0001,
      gradientClip: 5,
      temperature: 0.2,
      maskPositions: 1,
      negatives: 2,
    },
    parameterChanges: {
      embedding: changed(w.slice(0, 200), old.slice(0, 200)),
      encoder: changed(w.slice(200), old.slice(200)),
    },
    task: "同一样本与遮一位视图为正对，其他历史样本只作表示对照，不是异常真值",
  };
}
