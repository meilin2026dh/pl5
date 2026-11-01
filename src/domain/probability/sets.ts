export function conformal(
  p: Float64Array,
  calibration: number[],
  target: number,
) {
  const scores = calibration.map((i) => -Math.log(p[i])).sort((a, b) => a - b),
    k = Math.ceil((scores.length + 1) * target),
    threshold = k > scores.length ? null : scores[k - 1];
  const indices: number[] = [];
  for (let i = 0; i < p.length; i++)
    if (threshold === null || -Math.log(p[i]) <= threshold + 1e-12)
      indices.push(i);
  return { k, threshold, indices };
}
export function wilson(hits: number, n: number) {
  if (!n) return [0, 1];
  const z = 1.96,
    den = 1 + (z * z) / n,
    mid = (hits / n + (z * z) / (2 * n)) / den,
    half =
      (z *
        Math.sqrt(((hits / n) * (1 - hits / n)) / n + (z * z) / (4 * n * n))) /
      den;
  return [Math.max(0, mid - half), Math.min(1, mid + half)];
}
export const numberAt = (i: number) => String(i).padStart(5, "0");
export { seededRandom as rng } from "../selection/config";
