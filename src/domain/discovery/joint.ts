import { Tape } from "../selection/autodiff";
import { init, update, changed } from "./neural-common";
export function initialJoint(seed: number) {
  const w = init(262, seed);
  w.fill(1, 128, 132);
  return w;
}
function forward(w: Float64Array, prefix: string) {
  if (!/^\d{0,4}$/.test(prefix) || w.length !== 262)
    throw Error("联合模型只接受0至4位已生成前缀");
  const t = new Tape(),
    p = (o: number, n: number) => t.param(w, o, n),
    emb = p(0, 44),
    pos = p(44, 20),
    tokens = [10, ...[...prefix].map(Number)],
    xs = tokens.map((d, i) =>
      t.add(t.embedding(emb, d), t.slice(pos, i * 4, 4)),
    ),
    zero = t.constant([0, 0, 0, 0]);
  const keys = xs.map((x) => t.affine(x, p(80, 16), zero)),
    values = xs.map((x) => t.affine(x, p(96, 16), zero)),
    last = xs.at(-1)!,
    q = t.affine(last, p(64, 16), zero),
    attention = t.attention(q, keys, values);
  const h = t.norm(
      t.add(last, t.affine(attention.out, p(112, 16), zero)),
      p(128, 4),
      p(132, 4),
    ),
    ff = t.affine(
      t.activate(t.affine(h, p(136, 32), p(168, 8)), "tanh"),
      p(176, 32),
      p(208, 4),
    ),
    out = t.affine(t.add(h, ff), p(212, 40), p(252, 10));
  return { t, out, attention: attention.weights.v };
}
export function jointForward(w: Float64Array, prefix: string) {
  const f = forward(w, prefix);
  return { probabilities: f.t.softmax(f.out).v, attention: f.attention };
}
export function jointLoss(w: Float64Array, prefix: string, target: number) {
  const f = forward(w, prefix);
  return f.t.backward(f.out, target, w.length);
}
export function fitJoint(rows: string[], seed: number) {
  const w = initialJoint(seed),
    old = w.slice(),
    trace: number[] = [];
  for (let epoch = 0; epoch < 3; epoch++) {
    let loss = 0;
    for (const s of rows)
      for (let p = 0; p < 5; p++) {
        const r = jointLoss(w, s.slice(0, p), Number(s[p]));
        loss += r.loss;
        update(w, r.gradient, 0.02);
      }
    trace.push(loss / (rows.length * 5));
  }
  const cache = new Map<string, number[]>(),
    prob = (s: string) => {
      let v = 1;
      for (let p = 0; p < 5; p++) {
        const key = s.slice(0, p);
        let q = cache.get(key);
        if (!q) {
          q = jointForward(w, key).probabilities;
          cache.set(key, q);
        }
        v *= q[Number(s[p])];
      }
      return v;
    };
  return {
    prob,
    parameters: Array.from(w),
    changed: changed(w, old),
    trace,
    parameterCount: w.length,
    settings: {
      epochs: 3,
      rate: 0.02,
      l2: 0.0001,
      gradientClip: 5,
      hidden: 4,
      heads: 1,
    },
    parameterChanges: {
      embedding: changed(w.slice(0, 44), old.slice(0, 44)),
      attention: changed(w.slice(64, 128), old.slice(64, 128)),
      head: changed(w.slice(212), old.slice(212)),
    },
    kind: "joint-autoregressive-attention",
    context: "整注前缀；训练历史为固定窗口，不额外输入跨期状态",
  };
}
