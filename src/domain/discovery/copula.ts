import { seededRandom } from "../selection/config";
export function normalCDF(x: number) {
  const a = Math.abs(x),
    t = 1 / (1 + 0.2316419 * a),
    p =
      1 -
      (Math.exp((-a * a) / 2) / Math.sqrt(2 * Math.PI)) *
        (0.31938153 * t -
          0.356563782 * t * t +
          1.781477937 * t ** 3 -
          1.821255978 * t ** 4 +
          1.330274429 * t ** 5);
  return x >= 0 ? p : 1 - p;
}
export function normalQuantile(p: number) {
  if (p <= 0) return -Infinity;
  if (p >= 1) return Infinity;
  let lo = -9,
    hi = 9;
  for (let i = 0; i < 60; i++) {
    const m = (lo + hi) / 2;
    if (normalCDF(m) < p) lo = m;
    else hi = m;
  }
  return (lo + hi) / 2;
}
export function fitCopula(rows: string[], seed: number) {
  const n = rows.length,
    counts = Array.from({ length: 5 }, () => Array(10).fill(1) as number[]);
  for (const s of rows) for (let p = 0; p < 5; p++) counts[p][Number(s[p])]++;
  const margins = counts.map((r) => r.map((v) => v / (n + 10))),
    midpoints = margins.map((r) => {
      let sum = 0;
      return r.map((v) => {
        const z = normalQuantile(sum + v / 2);
        sum += v;
        return z;
      });
    }),
    thresholds = margins.map((r) => {
      let sum = 0;
      return r.slice(0, 9).map((v) => normalQuantile((sum += v)));
    }),
    data = rows.map((s) => [...s].map((d, p) => midpoints[p][Number(d)])),
    means = Array.from(
      { length: 5 },
      (_, p) => data.reduce((s, x) => s + x[p], 0) / n,
    ),
    cov = Array.from({ length: 5 }, (_, p) =>
      Array.from(
        { length: 5 },
        (_, q) =>
          data.reduce((s, x) => s + (x[p] - means[p]) * (x[q] - means[q]), 0) /
          n,
      ),
    ),
    correlation = cov.map((r, p) =>
      r.map((v, q) =>
        p === q
          ? 1
          : cov[p][p] * cov[q][q] > 1e-20
            ? (0.5 * v) / Math.sqrt(cov[p][p] * cov[q][q])
            : 0,
      ),
    ),
    L = Array.from({ length: 5 }, () => Array(5).fill(0) as number[]);
  for (let i = 0; i < 5; i++)
    for (let j = 0; j <= i; j++) {
      let x = correlation[i][j];
      for (let k = 0; k < j; k++) x -= L[i][k] * L[j][k];
      L[i][j] = i === j ? Math.sqrt(Math.max(1e-12, x)) : x / L[j][j];
    }
  const rng = seededRandom(seed),
    hist = new Uint32Array(100000),
    samples = 250000;
  for (let draw = 0; draw < samples; draw++) {
    const z = Array.from(
      { length: 5 },
      () =>
        Math.sqrt(-2 * Math.log(Math.max(1e-15, rng()))) *
        Math.cos(2 * Math.PI * rng()),
    );
    let index = 0;
    for (let p = 0; p < 5; p++) {
      const latent = L[p].reduce((s, v, k) => s + v * z[k], 0);
      let d = 0;
      while (d < 9 && latent > thresholds[p][d]) d++;
      index = index * 10 + d;
    }
    hist[index]++;
  }
  return {
    prob: (s: string) => (hist[Number(s)] + 1) / (samples + 100000),
    histogram: Array.from(hist),
    margins,
    thresholds,
    correlation,
    cholesky: L,
    parameterCount: 60,
    settings: {
      samples,
      seed,
      correlationShrinkage: 0.5,
      marginAlpha: 1,
      histogramAlpha: 1,
      fit: "离散边缘中点normal-score相关近似；非矩形似然最优化",
    },
    note: "Gaussian潜变量经离散阈值分箱，25万采样直方图+均匀伪计数近似PMF。非连续copula密度直接作五位概率；有限采样有噪声且平滑有偏。不实现t-Copula，不声称已发现尾部依赖。",
  };
}
