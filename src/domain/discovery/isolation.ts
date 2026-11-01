import { seededRandom } from "../selection/config";
export type IsolationNode = {
  size: number;
  feature?: number;
  split?: number;
  left?: IsolationNode;
  right?: IsolationNode;
};
export function pathCorrection(n: number) {
  if (n <= 1) return 0;
  let h = 0;
  for (let i = 1; i < n; i++) h += 1 / i;
  return 2 * h - (2 * (n - 1)) / n;
}
export function fitIsolation(rows: string[], seed: number) {
  const rng = seededRandom(seed),
    sampleSize = Math.min(64, rows.length),
    height = Math.ceil(Math.log2(sampleSize)),
    data = rows.map((s) => [...s].map(Number));
  const tree = (xs: number[][], depth: number): IsolationNode => {
    const ranges = Array.from({ length: 5 }, (_, p) => ({
      p,
      min: Math.min(...xs.map((x) => x[p])),
      max: Math.max(...xs.map((x) => x[p])),
    })).filter((r) => r.max > r.min);
    if (xs.length <= 1 || depth >= height || !ranges.length)
      return { size: xs.length };
    const r = ranges[Math.floor(rng() * ranges.length)],
      split = r.min + (r.max - r.min) * Math.max(1e-12, rng()),
      left = xs.filter((x) => x[r.p] < split),
      right = xs.filter((x) => x[r.p] >= split);
    return {
      size: xs.length,
      feature: r.p,
      split,
      left: tree(left, depth + 1),
      right: tree(right, depth + 1),
    };
  };
  const forest = Array.from({ length: 32 }, () => {
    const indices = Array.from({ length: data.length }, (_, i) => i);
    for (let i = 0; i < sampleSize; i++) {
      const j = i + Math.floor(rng() * (indices.length - i));
      [indices[i], indices[j]] = [indices[j], indices[i]];
    }
    return tree(
      indices.slice(0, sampleSize).map((i) => data[i]),
      0,
    );
  });
  const path = (node: IsolationNode, x: number[], depth = 0): number =>
    node.feature === undefined
      ? depth + pathCorrection(node.size)
      : path(
          x[node.feature] < node.split! ? node.left! : node.right!,
          x,
          depth + 1,
        );
  const anomaly = (s: string) =>
    sampleSize <= 1
      ? 0.5
      : 2 **
        (-forest.reduce((v, t) => v + path(t, [...s].map(Number)), 0) /
          forest.length /
          pathCorrection(sampleSize));
  return {
    anomaly,
    score: (s: string) => -8 * anomaly(s),
    forest,
    parameterCount: forest.reduce((n, t) => {
      const count = (x: IsolationNode): number =>
        1 + (x.left ? count(x.left) : 0) + (x.right ? count(x.right) : 0);
      return n + count(t);
    }, 0),
    settings: { trees: 32, sampleSize, height, seed, energyScale: 8 },
    kind: "ordinal-position-isolation-forest",
    note: "路径隔离异常分不是密度估计；数字按有序数值分割，未使用One-class SVM。score=-8*异常分，全集正规化仅为研究能量分布。",
  };
}
