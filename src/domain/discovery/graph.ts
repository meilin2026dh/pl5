import { Tape } from "../selection/autodiff";
import { init, scale, sum, update, changed } from "./neural-common";
import { seededRandom } from "../selection/config";
export function buildGraph(rows: string[]) {
  const edges = Array.from(
    { length: 50 },
    () => Array(50).fill(0.5) as number[],
  );
  for (const s of rows)
    for (let p = 0; p < 5; p++)
      for (let q = p + 1; q < 5; q++) {
        const a = p * 10 + Number(s[p]),
          b = q * 10 + Number(s[q]);
        edges[a][b]++;
        edges[b][a]++;
      }
  return edges;
}
export const graphInitial = (seed: number) => init(241, seed);
function forward(w: Float64Array, edges: number[][], s: string) {
  const t = new Tape(),
    p = (o: number, n: number) => t.param(w, o, n),
    emb = p(0, 200),
    ids = [...s].map((d, i) => i * 10 + Number(d)),
    xs = ids.map((i) => t.slice(emb, i * 4, 4)),
    hs = xs.map((x, i) => {
      const weights = ids.map((id, j) => (i === j ? 1 : edges[ids[i]][id])),
        total = weights.reduce((a, b) => a + b, 0),
        message = sum(
          t,
          xs.map((v, j) => scale(t, v, weights[j] / total)),
        );
      return t.activate(
        t.add(
          t.affine(x, p(200, 16), p(232, 4)),
          t.affine(message, p(216, 16), t.constant([0, 0, 0, 0])),
        ),
        "tanh",
      );
    });
  const pooled = scale(t, sum(t, hs), 0.2),
    score = t.affine(pooled, p(236, 4), p(240, 1)),
    out = t.concat(t.constant([0]), score);
  return { t, out };
}
export function graphLoss(
  w: Float64Array,
  g: number[][],
  s: string,
  target: number,
) {
  const f = forward(w, g, s);
  return f.t.backward(f.out, target, w.length);
}
function numeric(w: Float64Array, g: number[][], s: string) {
  const ids = [...s].map((d, i) => i * 10 + Number(d)),
    x = ids.map((i) => Array.from(w.slice(i * 4, i * 4 + 4))),
    pooled = [0, 0, 0, 0];
  for (let i = 0; i < 5; i++) {
    const weights = ids.map((id, j) => (i === j ? 1 : g[ids[i]][id])),
      total = weights.reduce((a, b) => a + b, 0),
      msg = [0, 0, 0, 0];
    for (let j = 0; j < 5; j++)
      for (let k = 0; k < 4; k++) msg[k] += (weights[j] * x[j][k]) / total;
    for (let o = 0; o < 4; o++)
      pooled[o] +=
        0.2 *
        Math.tanh(
          w[232 + o] +
            x[i].reduce((s, v, k) => s + v * w[200 + o * 4 + k], 0) +
            msg.reduce((s, v, k) => s + v * w[216 + o * 4 + k], 0),
        );
  }
  return w[240] + pooled.reduce((s, v, k) => s + v * w[236 + k], 0);
}
export function fitGraph(rows: string[], seed: number) {
  const edges = buildGraph(rows),
    w = graphInitial(seed),
    old = w.slice(),
    rng = seededRandom(seed),
    trace: number[] = [];
  const samples = rows.flatMap((s) => [
    { s, y: 1 },
    { s: String(Math.floor(rng() * 100000)).padStart(5, "0"), y: 0 },
  ]);
  for (let epoch = 0; epoch < 3; epoch++) {
    let loss = 0;
    for (const r of samples) {
      const out = graphLoss(w, edges, r.s, r.y);
      loss += out.loss;
      update(w, out.gradient);
    }
    trace.push(loss / samples.length);
  }
  return {
    score: (s: string) => numeric(w, edges, s),
    parameters: Array.from(w),
    edges,
    trace,
    changed: changed(w, old),
    parameterCount: w.length,
    settings: {
      epochs: 3,
      rate: 0.03,
      l2: 0.0001,
      gradientClip: 5,
      graphSmoothing: 0.5,
      layers: 1,
      hidden: 4,
    },
    parameterChanges: {
      embedding: changed(w.slice(0, 200), old.slice(0, 200)),
      message: changed(w.slice(216, 232), old.slice(216, 232)),
      head: changed(w.slice(236), old.slice(236)),
    },
    kind: "position-digit-one-layer-message-passing",
  };
}
