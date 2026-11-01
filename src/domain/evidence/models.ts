import type { HistoryRecord } from "../pick5";
export type Hypothesis = {
  kind: "uniform" | "iid" | "markov";
  window: number;
  alpha: number;
};
export const modelName = (m: Hypothesis) =>
  m.kind === "uniform"
    ? "独立均匀"
    : `${m.kind === "iid" ? "位置频率" : "一步转移"} W${m.window} α${m.alpha}`;
export function probabilities(past: HistoryRecord[], m: Hypothesis) {
  const rows = past.slice(-m.window),
    counts = Array.from(
      { length: 5 },
      () => Array(10).fill(m.alpha) as number[],
    );
  if (m.kind === "uniform")
    return counts.map(() => Array(10).fill(0.1) as number[]);
  if (m.kind === "iid")
    for (const r of rows)
      for (let p = 0; p < 5; p++) counts[p][Number(r.number[p])]++;
  else
    for (let p = 0; p < 5; p++) {
      const last = rows.at(-1)!.number[p];
      for (let t = 1; t < rows.length; t++)
        if (rows[t - 1].number[p] === last)
          counts[p][Number(rows[t].number[p])]++;
    }
  return counts.map((row) => {
    const total = row.reduce((a, b) => a + b, 0);
    return row.map((v) => v / total);
  });
}
export function blend(p: number[][], weight: number) {
  return p.map((row) => row.map((v) => 0.1 + weight * (v - 0.1)));
}
export function scoreProbabilities(p: number[][], number: string) {
  let logLoss = 0,
    brier = 0;
  const confidence: { q: number; hit: number }[] = [];
  for (let j = 0; j < 5; j++) {
    const d = Number(number[j]);
    logLoss -= Math.log(p[j][d]) / 5;
    brier += p[j].reduce((s, v, k) => s + (v - Number(k === d)) ** 2, 0) / 5;
    const max = Math.max(...p[j]),
      top = p[j].indexOf(max);
    confidence.push({ q: max, hit: Number(top === d) });
  }
  return { logLoss, brier, confidence };
}
export function evaluate(
  rows: HistoryRecord[],
  start: number,
  end: number,
  m: Hypothesis,
  weight = 1,
) {
  return rows.slice(start, end).map((r, i) => ({
    issue: r.issue,
    ...scoreProbabilities(
      blend(probabilities(rows.slice(0, start + i), m), weight),
      r.number,
    ),
  }));
}
export function mean(a: number[]) {
  return a.reduce((s, v) => s + v, 0) / a.length;
}
export function summarize(scores: ReturnType<typeof evaluate>) {
  const bins = Array.from({ length: 10 }, (_, i) => ({
    lo: i / 10,
    hi: (i + 1) / 10,
    n: 0,
    predicted: 0,
    observed: 0,
  }));
  for (const row of scores)
    for (const c of row.confidence) {
      const b = bins[Math.min(9, Math.floor(c.q * 10))];
      b.n++;
      b.predicted += c.q;
      b.observed += c.hit;
    }
  const reliability = bins
    .filter((b) => b.n)
    .map((b) => ({
      ...b,
      predicted: b.predicted / b.n,
      observed: b.observed / b.n,
    }));
  return {
    logLoss: mean(scores.map((s) => s.logLoss)),
    brier: mean(scores.map((s) => s.brier)),
    ece:
      reliability.reduce(
        (s, b) => s + b.n * Math.abs(b.predicted - b.observed),
        0,
      ) /
      (scores.length * 5),
    reliability,
  };
}
export function improvement(scores: ReturnType<typeof evaluate>) {
  const delta = scores.map((s) => {
      const d = Math.log(10) - s.logLoss;
      return Math.abs(d) < 1e-12 ? 0 : d;
    }),
    avg = mean(delta),
    variance =
      delta.reduce((s, v) => s + (v - avg) ** 2, 0) / (delta.length - 1),
    se = Math.sqrt(variance / delta.length),
    absolute = delta.reduce((s, v) => s + Math.abs(v), 0);
  return {
    mean: avg,
    low: avg - 1.96 * se,
    high: avg + 1.96 * se,
    maxSingleShare: absolute ? Math.max(...delta.map(Math.abs)) / absolute : 0,
    leaveOneWorst: Math.min(
      ...delta.map((v) => (avg * delta.length - v) / (delta.length - 1)),
    ),
  };
}
export function candidates(window: number): Hypothesis[] {
  return [
    { kind: "uniform", window, alpha: 1 },
    ...[...new Set([Math.max(40, Math.floor(window / 2)), window])].flatMap(
      (w) =>
        [1, 5].flatMap((alpha) =>
          (["iid", "markov"] as const).map((kind) => ({
            kind,
            window: w,
            alpha,
          })),
        ),
    ),
  ];
}
export function chooseModel(
  rows: HistoryRecord[],
  start: number,
  end: number,
  window: number,
) {
  const trials = candidates(window).map((model) => ({
    model,
    name: modelName(model),
    ...summarize(evaluate(rows, start, end, model)),
  }));
  const winner = trials.reduce((a, b) =>
    b.logLoss < a.logLoss - 1e-12 ? b : a,
  );
  return { model: winner.model, trials };
}
export function calibrate(
  rows: HistoryRecord[],
  start: number,
  end: number,
  m: Hypothesis,
) {
  const trials = [0, 0.25, 0.5, 0.75, 1].map((weight) => ({
    weight,
    ...summarize(evaluate(rows, start, end, m, weight)),
  }));
  return trials.reduce((a, b) => (b.logLoss < a.logLoss - 1e-12 ? b : a));
}
