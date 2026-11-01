import { Tape, type Vector } from "../selection/autodiff";
import { seededRandom } from "../selection/config";
export function init(size: number, seed: number) {
  const rng = seededRandom(seed);
  return Float64Array.from({ length: size }, () => 0.2 * (rng() - 0.5));
}
export function scale(t: Tape, x: Vector, s: number) {
  return t.mul(x, t.constant(x.v.map(() => s)));
}
export function sum(t: Tape, vs: Vector[]) {
  return vs.reduce((a, b) => t.add(a, b), t.constant(vs[0].v.map(() => 0)));
}
export function update(w: Float64Array, g: Float64Array, rate = 0.03) {
  const norm = Math.sqrt(g.reduce((s, x) => s + x * x, 0)),
    clip = Math.min(1, 5 / Math.max(norm, 1e-30));
  for (let i = 0; i < w.length; i++)
    w[i] -= rate * (g[i] * clip + 0.0001 * w[i]);
}
export function changed(w: Float64Array, old: Float64Array) {
  return w.reduce((s, x, i) => s + Math.abs(x - old[i]), 0);
}
export function cosine(a: number[], b: number[]) {
  const na = Math.sqrt(a.reduce((s, x) => s + x * x, 0) + 1e-8),
    nb = Math.sqrt(b.reduce((s, x) => s + x * x, 0) + 1e-8);
  return a.reduce((s, x, i) => s + x * b[i], 0) / (na * nb);
}
