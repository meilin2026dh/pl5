import { seededRandom } from "../selection/config";
const digits = (s: string) => [...s].map(Number);
export function auc(scores: number[], labels: number[]) {
  const rows = scores
    .map((s, i) => ({ s, y: labels[i] }))
    .sort((a, b) => a.s - b.s);
  let rank = 0,
    pos = 0,
    neg = 0;
  for (let i = 0; i < rows.length;) {
    let j = i;
    while (j < rows.length && rows[j].s === rows[i].s) j++;
    for (let k = i; k < j; k++) {
      if (rows[k].y) {
        rank += (i + 1 + j) / 2;
        pos++;
      } else neg++;
    }
    i = j;
  }
  return pos && neg ? (rank - (pos * (pos + 1)) / 2) / (pos * neg) : 0.5;
}
export function fitRatio(rows: string[], seed: number) {
  const rng = seededRandom(seed),
    hidden = 8,
    w = Array.from({ length: hidden }, () =>
      Array.from({ length: 50 }, () => 0.2 * (rng() - 0.5)),
    ),
    b = Array(hidden).fill(0) as number[],
    v = Array.from({ length: hidden }, () => 0.2 * (rng() - 0.5));
  let bias = 0;
  const forward = (s: string) => {
    const d = digits(s),
      h = w.map((r, j) =>
        Math.tanh(b[j] + d.reduce((t, x, p) => t + r[p * 10 + x], 0)),
      );
    const z = Math.max(
      -25,
      Math.min(25, bias + h.reduce((t, x, j) => t + x * v[j], 0)),
    );
    return { h, z, p: 1 / (1 + Math.exp(-z)) };
  };
  const data = rows.flatMap((s) => [
    { s, y: 1 },
    { s: String(Math.floor(rng() * 100000)).padStart(5, "0"), y: 0 },
  ]);
  for (let epoch = 0; epoch < 5; epoch++)
    for (const { s, y } of data) {
      const { h, p } = forward(s),
        e = p - y,
        d = digits(s);
      for (let j = 0; j < hidden; j++) {
        const dh = e * v[j] * (1 - h[j] * h[j]);
        for (let k = 0; k < 50; k++)
          w[j][k] -=
            0.03 *
            (dh * Number(d[Math.floor(k / 10)] === k % 10) + 0.001 * w[j][k]);
        b[j] -= 0.03 * dh;
        v[j] -= 0.03 * (e * h[j] + 0.001 * v[j]);
      }
      bias -= 0.03 * e;
    }
  return {
    score: (s: string) => forward(s).z,
    parameters: JSON.stringify({ w, b, v, bias }),
    samples: data.length,
  };
}
export function fitTensor(rows: string[], rank: number, seed: number) {
  const rng = seededRandom(seed),
    sizes = [1, rank, rank, rank, rank, 1];
  let cores = Array.from({ length: 5 }, (_, p) =>
    Array.from({ length: sizes[p] }, () =>
      Array.from({ length: 10 }, () =>
        Array.from({ length: sizes[p + 1] }, () => 0.1 + rng()),
      ),
    ),
  );
  const normalize = () => {
    for (const core of cores)
      for (const a of core) {
        const z = a.flat().reduce((s, x) => s + x, 0);
        for (const row of a) for (let j = 0; j < row.length; j++) row[j] /= z;
      }
  };
  normalize();
  const pass = (s: string) => {
    const d = digits(s),
      f: number[][] = [[1]];
    for (let p = 0; p < 5; p++) {
      const out = Array(sizes[p + 1]).fill(0) as number[];
      for (let a = 0; a < sizes[p]; a++)
        for (let b = 0; b < out.length; b++)
          out[b] += f[p][a] * cores[p][a][d[p]][b];
      f.push(out);
    }
    return f;
  };
  const trace: number[] = [];
  for (let epoch = 0; epoch < 8; epoch++) {
    const counts = cores.map((core) =>
      core.map((a) => a.map((row) => row.map(() => 0.05))),
    );
    let loss = 0;
    for (const s of rows) {
      const d = digits(s),
        f = pass(s),
        z = Math.max(1e-300, f[5][0]);
      loss -= Math.log(z);
      let back = [1];
      for (let p = 4; p >= 0; p--) {
        const prev = Array(sizes[p]).fill(0) as number[];
        for (let a = 0; a < sizes[p]; a++)
          for (let b = 0; b < sizes[p + 1]; b++) {
            const edge = cores[p][a][d[p]][b] * back[b];
            counts[p][a][d[p]][b] += (f[p][a] * edge) / z;
            prev[a] += edge;
          }
        back = prev;
      }
    }
    trace.push(loss / rows.length);
    cores = counts;
    normalize();
  }
  return {
    prob: (s: string) => pass(s)[5][0],
    trace,
    parameters: JSON.stringify(cores),
    count: 20 * rank + 30 * rank * rank,
  };
}
/** Deterministic greedy approximate MAP for an L-ensemble, not k-DPP sampling. */
export function diversify(
  numbers: string[],
  logScores: number[],
  k: number,
  sigma: number,
) {
  if (
    k < 1 ||
    k > numbers.length ||
    k > 64 ||
    numbers.length > 256 ||
    sigma <= 0 ||
    logScores.length !== numbers.length
  )
    throw Error("DPP规模或参数错误");
  const top = Math.max(...logScores),
    q = logScores.map((s) => Math.exp(Math.max(-30, (s - top) / 2))),
    n = numbers.length,
    residual = q.map((x) => x * x),
    coeff = Array.from({ length: n }, () => [] as number[]),
    selected: number[] = [],
    gains: number[] = [];
  const kernel = (i: number, j: number) =>
    q[i] *
    q[j] *
    Math.exp(
      -digits(numbers[i]).reduce(
        (s, d, p) => s + Number(d !== Number(numbers[j][p])),
        0,
      ) /
        (sigma * sigma),
    );
  for (let t = 0; t < k; t++) {
    let best = -1;
    for (let i = 0; i < n; i++)
      if (
        !selected.includes(i) &&
        (best < 0 || residual[i] > residual[best] + 1e-15)
      )
        best = i;
    if (best < 0 || residual[best] <= 1e-14) break;
    const pivot = Math.sqrt(residual[best]);
    gains.push(Math.log(residual[best]));
    selected.push(best);
    for (let i = 0; i < n; i++)
      if (!selected.includes(i)) {
        const dot = coeff[i].reduce((s, x, j) => s + x * coeff[best][j], 0),
          value = (kernel(i, best) - dot) / pivot;
        coeff[i].push(value);
        residual[i] = Math.max(0, residual[i] - value * value);
      }
  }
  return {
    numbers: selected.map((i) => numbers[i]),
    indices: selected,
    gains,
    stop: selected.length === k ? "budget" : "numerical-rank",
  };
}
