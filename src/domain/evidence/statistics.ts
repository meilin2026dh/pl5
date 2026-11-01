import type { HistoryRecord } from "../pick5";
import { seededRandom } from "../selection/config";
export function inspectQuality(rows: HistoryRecord[] | undefined) {
  const errors: string[] = [],
    issues = new Set<string>(),
    dates = new Set<string>();
  let outOfOrder = 0;
  if (!Array.isArray(rows) || !rows.length)
    return { count: 0, errors: ["没有历史数据"], gaps: 0, outOfOrder: 0 };
  for (let i = 0; i < rows.length; i++) {
    const r = rows[i];
    if (
      !r ||
      typeof r.issue !== "string" ||
      !r.issue.trim() ||
      typeof r.date !== "string" ||
      !/^\d{4}-\d{2}-\d{2}$/.test(r.date) ||
      !Number.isFinite(Date.parse(r.date)) ||
      new Date(r.date).toISOString().slice(0, 10) !== r.date ||
      typeof r.number !== "string" ||
      !/^\d{5}$/.test(r.number)
    ) {
      errors.push(`第${i + 1}条格式或日期错误`);
      continue;
    }
    if (issues.has(r.issue)) errors.push(`期号重复：${r.issue}`);
    if (dates.has(r.date)) errors.push(`日期重复：${r.date}`);
    issues.add(r.issue);
    dates.add(r.date);
    if (i && rows[i - 1]?.date > r.date) outOfOrder++;
  }
  const sorted = [...dates].sort(),
    gaps = sorted
      .slice(1)
      .filter(
        (d, i) => Date.parse(d) - Date.parse(sorted[i]) > 86400000,
      ).length;
  return { count: rows.length, errors, gaps, outOfOrder };
}
export function frequencyStatistic(rows: number[][]) {
  const n = rows.length,
    counts = Array.from({ length: 5 }, () => Array(10).fill(0) as number[]);
  for (const row of rows) row.forEach((d, p) => counts[p][d]++);
  return counts.flat().reduce((s, v) => s + (v - n / 10) ** 2 / (n / 10), 0);
}
export function serialStatistic(rows: number[][]) {
  const n = rows.length - 1;
  let stat = 0;
  for (let p = 0; p < 5; p++) {
    const pairs = Array(100).fill(0),
      a = Array(10).fill(0),
      b = Array(10).fill(0);
    for (let i = 1; i < rows.length; i++) {
      const x = rows[i - 1][p],
        y = rows[i][p];
      pairs[x * 10 + y]++;
      a[x]++;
      b[y]++;
    }
    for (let x = 0; x < 10; x++)
      for (let y = 0; y < 10; y++) {
        const v = pairs[x * 10 + y];
        if (v) stat += 2 * v * Math.log((v * n) / (a[x] * b[y]));
      }
  }
  return stat;
}
export function changeStatistic(rows: number[][]) {
  const n = rows.length,
    all = Array(50).fill(0),
    left = Array(50).fill(0);
  for (const row of rows) row.forEach((d, p) => all[p * 10 + d]++);
  let stat = -1,
    cut = 20;
  for (let k = 1; k < n; k++) {
    rows[k - 1].forEach((d, p) => left[p * 10 + d]++);
    if (k < 20 || n - k < 20) continue;
    const v =
      (all.reduce(
        (s, a, i) => s + (left[i] / k - (a - left[i]) / (n - k)) ** 2,
        0,
      ) *
        k *
        (n - k)) /
      n;
    if (v > stat) {
      stat = v;
      cut = k;
    }
  }
  return { stat, cut };
}
export function monteCarloP(observed: number, simulated: number[]) {
  return (
    (1 + simulated.filter((v) => v >= observed - 1e-12).length) /
    (simulated.length + 1)
  );
}
export function randomizationP(
  rows: number[][],
  stat: (r: number[][]) => number,
  B: number,
  seed: number,
  uniform = false,
) {
  const random = seededRandom(seed),
    observed = stat(rows),
    simulated: number[] = [];
  for (let b = 0; b < B; b++) {
    let sample: number[][];
    if (uniform)
      sample = rows.map(() =>
        Array.from({ length: 5 }, () => Math.floor(random() * 10)),
      );
    else {
      sample = [...rows];
      for (let i = sample.length - 1; i > 0; i--) {
        const j = Math.floor(random() * (i + 1));
        [sample[i], sample[j]] = [sample[j], sample[i]];
      }
    }
    simulated.push(stat(sample));
  }
  return { stat: observed, p: monteCarloP(observed, simulated) };
}
export function holm(pvalues: number[]) {
  const order = pvalues.map((p, i) => ({ p, i })).sort((a, b) => a.p - b.p),
    out = pvalues.map(() => 1);
  let last = 0;
  order.forEach(({ p, i }, j) => {
    last = Math.max(last, Math.min(1, p * (pvalues.length - j)));
    out[i] = last;
  });
  return out;
}
export function uniformMartingale(rows: HistoryRecord[]) {
  const counts = Array.from({ length: 5 }, () => Array(10).fill(0)),
    trace: { issue: string; logE: number }[] = [];
  let logE = 0,
    maxLogE = 0;
  for (let t = 0; t < rows.length; t++) {
    for (let p = 0; p < 5; p++) {
      const d = Number(rows[t].number[p]);
      logE += Math.log((counts[p][d] + 1) / (t + 10) / 0.1);
      counts[p][d]++;
    }
    maxLogE = Math.max(maxLogE, logE);
    trace.push({ issue: rows[t].issue, logE });
  }
  return {
    logE,
    maxLogE,
    anytimeP: Math.exp(-Math.min(700, maxLogE)),
    trace,
    origin: rows[0].issue,
  };
}

export function repeatStatistic(rows: number[][]) {
  const expected = [0.0001, 0.0135, 0.18, 0.504, 0.3024],
    counts = Array(5).fill(0);
  for (const row of rows) counts[new Set(row).size - 1]++;
  return counts.reduce(
    (s, v, i) =>
      s + (v - rows.length * expected[i]) ** 2 / (rows.length * expected[i]),
    0,
  );
}
