import { Tape } from "../selection/autodiff";
import { init, update, changed } from "./neural-common";
export const aeInitial = (seed: number) => init(454, seed);
function forward(w: Float64Array, s: string) {
  const t = new Tape(),
    x = t.constant(
      Array.from({ length: 50 }, (_, i) =>
        Number(Number(s[Math.floor(i / 10)]) === i % 10),
      ),
    ),
    h = t.activate(t.affine(x, t.param(w, 0, 200), t.param(w, 200, 4)), "tanh"),
    out = t.affine(h, t.param(w, 204, 200), t.param(w, 404, 50));
  return { t, out };
}
export function aeLoss(w: Float64Array, s: string, p: number) {
  const f = forward(w, s);
  return f.t.backward(f.t.slice(f.out, p * 10, 10), Number(s[p]), w.length);
}
function reconstruction(w: Float64Array, s: string) {
  const h = Array.from({ length: 4 }, (_, o) =>
    Math.tanh(
      w[200 + o] +
        [...s].reduce((v, d, p) => v + w[o * 50 + p * 10 + Number(d)], 0),
    ),
  );
  let loss = 0;
  for (let p = 0; p < 5; p++) {
    const logits = Array.from({ length: 10 }, (_, d) => {
        const o = p * 10 + d;
        return (
          w[404 + o] + h.reduce((v, x, k) => v + x * w[204 + o * 4 + k], 0)
        );
      }),
      m = Math.max(...logits);
    loss +=
      m +
      Math.log(logits.reduce((v, x) => v + Math.exp(x - m), 0)) -
      logits[Number(s[p])];
  }
  return loss / 5;
}
export function fitAutoencoder(rows: string[], seed: number) {
  const w = aeInitial(seed),
    old = w.slice(),
    trace: number[] = [];
  for (let epoch = 0; epoch < 3; epoch++) {
    let loss = 0;
    for (const s of rows)
      for (let p = 0; p < 5; p++) {
        const r = aeLoss(w, s, p);
        loss += r.loss;
        update(w, r.gradient, 0.02);
      }
    trace.push(loss / (rows.length * 5));
  }
  return {
    score: (s: string) => -reconstruction(w, s),
    reconstruction: (s: string) => reconstruction(w, s),
    parameters: Array.from(w),
    parameterCount: w.length,
    parameterChanges: {
      encoder: changed(w.slice(0, 204), old.slice(0, 204)),
      decoder: changed(w.slice(204), old.slice(204)),
    },
    trace,
    settings: {
      epochs: 3,
      rate: 0.02,
      l2: 0.0001,
      gradientClip: 5,
      encoder: [50, 4],
      decoder: [4, 50],
      loss: "五位置softmax平均重构交叉熵",
      seed,
    },
    note: "重构误差是能量，非已校准联合似然；不证明数据位于低维流形。",
  };
}
