import { fitPotential } from "./potential";
import type { ResearchConfig, ResearchStats, ScoreModel } from "./types";

// Lanczos approximation, valid for positive Dirichlet concentrations.
export function logGamma(z: number): number {
  const c = [
    676.5203681218851, -1259.1392167224028, 771.32342877765313,
    -176.6150291621406, 12.507343278686905, -0.13857109526572012,
    9.984369578019572e-6, 1.5056327351493116e-7,
  ];
  if (z < 0.5)
    return (
      Math.log(Math.PI) - Math.log(Math.sin(Math.PI * z)) - logGamma(1 - z)
    );
  z -= 1;
  let x = 0.99999999999980993;
  for (let i = 0; i < c.length; i++) x += c[i] / (z + i + 1);
  const t = z + 7.5;
  return (
    0.5 * Math.log(2 * Math.PI) + (z + 0.5) * Math.log(t) - t + Math.log(x)
  );
}
const uniform = () =>
  Array.from({ length: 5 }, () => Array(10).fill(0.1) as number[]);
function marginal(row: number[], a: number): number {
  return (
    logGamma(10 * a) -
    logGamma(10 * a + row.reduce((x, y) => x + y, 0)) +
    row.reduce((s, n) => s + logGamma(a + n) - logGamma(a), 0)
  );
}
function iid(s: ResearchStats, a: number) {
  return s.counts.map((row) => row.map((c) => (c + a) / (s.n + 10 * a)));
}
function sumScore(table: number[][], number: string) {
  let value = 0;
  for (let p = 0; p < 5; p++) value += table[p][Number(number[p])];
  return value;
}
function product(table: number[][], number: string) {
  let value = 1;
  for (let p = 0; p < 5; p++) value *= table[p][Number(number[p])];
  return value;
}
function logTable(table: number[][]) {
  return table.map((row) =>
    row.map((x) => (x === 0 ? -Infinity : Math.log(x))),
  );
}
function normalize(logs: number[]) {
  const max = Math.max(...logs),
    values = logs.map((x) => Math.exp(x - max)),
    total = values.reduce((a, b) => a + b, 0);
  return values.map((x) => x / total);
}

/** Dempster combination of singleton masses and the remaining frame mass. */
export function combineDempster(
  mass: number[],
  theta: number,
  other: number[],
  otherTheta: number,
) {
  let conflict = 0;
  for (let d = 0; d < 10; d++)
    for (let e = 0; e < 10; e++) if (d !== e) conflict += mass[d] * other[e];
  if (!Number.isFinite(conflict) || 1 - conflict <= 1e-12)
    throw new Error("D-S 证据接近完全冲突，无法可靠归一化");
  const den = 1 - conflict;
  return {
    mass: mass.map(
      (m, d) => (m * other[d] + m * otherTheta + theta * other[d]) / den,
    ),
    theta: (theta * otherTheta) / den,
    conflict,
  };
}

export function fitScores(
  config: ResearchConfig,
  s: ResearchStats,
): ScoreModel {
  if (!s.n || s.counts.length !== 5) throw new Error("评分需要历史数据");
  if (config.method === "potential")
    return fitPotential(s.rows, config.potential!);
  if (config.method === "markovScore") {
    const counts = s.transitions.map((matrix, p) => matrix[s.last[p]]);
    const probabilities = counts.map((row) => {
      const total = row.reduce((a, b) => a + b, 0);
      return row.map((v) => (v + 1) / (total + 10));
    });
    return {
      score: (n) =>
        [...n].reduce(
          (total, d, p) => total + Math.log(probabilities[p][Number(d)]),
          0,
        ),
      details: {
        model: "五位置一步转移后验路径log似然",
        referenceNumber: s.last.join(""),
        alpha: 1,
        transitions: s.transitions,
        probabilities,
        observedOutCounts: counts.map((row) => row.reduce((a, b) => a + b, 0)),
        policy: "无出边的当前状态采用均匀后验；按观测相邻记录定义转移",
      },
    };
  }
  if (config.method === "heatScore") {
    const table = logTable(iid(s, 0.5));
    return {
      score: (n) => sumScore(table, n),
      details: { alpha: 0.5, scoreScale: "logProbability" },
    };
  }
  if (config.method === "bma") {
    const names = [
      "uniform",
      "iid_a0.5",
      "iid_a1.0",
      "iid_a2.0",
      "iid_a5.0",
      "mkv_a1.0",
      "mkv_a5.0",
    ];
    const logs = [-5 * s.n * Math.log(10)],
      predictions = [uniform()];
    for (const a of [0.5, 1, 2, 5]) {
      logs.push(s.counts.reduce((total, row) => total + marginal(row, a), 0));
      predictions.push(iid(s, a));
    }
    for (const a of [1, 5]) {
      logs.push(
        s.transitions.reduce(
          (total, position) =>
            total + position.reduce((v, row) => v + marginal(row, a), 0),
          0,
        ) -
          5 * Math.log(10),
      );
      predictions.push(
        s.transitions.map((position, p) => {
          const row = position[s.last[p]],
            den = row.reduce((x, y) => x + y, 0) + 10 * a;
          return row.map((c) => (c + a) / den);
        }),
      );
    }
    const weights = normalize(logs);
    return {
      score: (n) =>
        predictions.reduce((v, p, k) => v + weights[k] * product(p, n), 0),
      details: {
        models: names,
        weights,
        logMarginals: logs,
        logBayesFactorUniformVsIID1: logs[0] - logs[2],
        scoreScale: "probability",
      },
    };
  }
  if (config.method === "sparseBest") {
    const logs = [
      -5 * s.n * Math.log(10),
      ...s.counts.map((row) => marginal(row, 1) - 4 * s.n * Math.log(10)),
    ];
    let selected = 0;
    for (let i = 1; i < logs.length; i++)
      if (logs[i] > logs[selected]) selected = i;
    const predictions = uniform();
    if (selected) predictions[selected - 1] = iid(s, 1)[selected - 1];
    return {
      score: (n) => product(predictions, n),
      details: {
        selectedPosition: selected - 1,
        logMarginals: logs,
        model: "best-of-uniform-and-five-single-position-iid",
        scoreScale: "probability",
      },
    };
  }
  if (config.method === "dsPlausibility" || config.method === "dsBelief") {
    const plus = config.method === "dsPlausibility" ? 10 : 0;
    const table = logTable(s.counts.map((row) => row.map((c) => c + plus)));
    return {
      score: (n) => sumScore(table, n),
      details: {
        strength: 10,
        uncertaintyWidth: 10 / (s.n + 10),
        scoreScale: "logUnnormalized",
        omittedLogDenominator: 5 * Math.log(s.n + 10),
      },
    };
  }
  if (config.method === "dsDempster") {
    const windows = config.windows;
    if (
      !Number.isInteger(windows) ||
      windows < 1 ||
      Math.floor(s.n / windows) < 5
    )
      throw new Error("D-S 每个分窗至少需要5期历史");
    const sizes = Array.from(
      { length: windows },
      (_, i) => Math.floor(s.n / windows) + (i < s.n % windows ? 1 : 0),
    );
    let offset = 0;
    const counts = sizes.map((size) => {
      const table = Array.from(
        { length: 5 },
        () => Array(10).fill(0) as number[],
      );
      for (const row of s.rows.slice(offset, offset + size))
        for (let p = 0; p < 5; p++) table[p][Number(row.number[p])]++;
      offset += size;
      return table;
    });
    const conflicts: number[][] = [];
    const finalMasses: number[][] = [];
    const ignorance: number[] = [];
    const table = Array.from({ length: 5 }, (_, p) => {
      let mass = counts[0][p].map((c) => c / (sizes[0] + 10)),
        theta = 10 / (sizes[0] + 10);
      const chain: number[] = [];
      for (let w = 1; w < windows; w++) {
        const other = counts[w][p].map((c) => c / (sizes[w] + 10)),
          otherTheta = 10 / (sizes[w] + 10);
        const combined = combineDempster(mass, theta, other, otherTheta);
        chain.push(combined.conflict);
        mass = combined.mass;
        theta = combined.theta;
      }
      conflicts.push(chain);
      finalMasses.push(mass);
      ignorance.push(theta);
      return mass.map((m) => m + theta);
    });
    const logs = logTable(table);
    return {
      score: (n) => sumScore(logs, n),
      details: {
        windowSizes: sizes,
        conflicts,
        finalMasses,
        ignorance,
        scoreScale: "logPlausibility",
        evidenceIndependence: "assumed-not-established",
      },
    };
  }
  throw new Error("不是评分研究方法");
}
