import { it, expect } from "vitest";
import { betaCDF, betaQuantile } from "../src/domain/lab/beta";
import { updatePosterior } from "../src/domain/lab/posterior";
import { solveCover } from "../src/domain/lab/cover";
const rows = Array.from({ length: 40 }, (_, i) => ({
  issue: String(i + 1),
  date: new Date(Date.UTC(2025, 0, i + 1)).toISOString().slice(0, 10),
  number: String(i % 10).repeat(5),
}));
it("inverts independent analytic Beta cases including asymmetric tails", () => {
  for (const p of [0.025, 0.5, 0.975]) {
    expect(betaQuantile(p, 1, 1)).toBeCloseTo(p, 9);
    expect(betaQuantile(p, 1, 9)).toBeCloseTo(1 - (1 - p) ** (1 / 9), 9);
    expect(betaQuantile(p, 2, 2)).toBeCloseTo(
      p === 0.5 ? 0.5 : p === 0.025 ? 0.094299324050246 : 0.905700675949754,
      9,
    );
  }
  expect(betaCDF(0.3, 2, 2)).toBeCloseTo(0.216, 10);
  expect(() => betaQuantile(0.5, 0, 1)).toThrow();
});
it("appends only new observations, handles sliding windows, revisions and untrusted counts", () => {
  const c = { mode: "all" as const, window: 20, alpha: 1 };
  const a = updatePosterior(rows.slice(0, 20), c, "x");
  const b = updatePosterior(rows, c, "x", a.state),
    full = updatePosterior(rows, c, "x");
  expect(b.added).toBe(20);
  expect(b.action).toBe("append");
  expect(b.cells).toEqual(full.cells);
  expect(updatePosterior(rows, c, "x", b.state).added).toBe(0);
  const changed = rows.map((r, i) => (i ? r : { ...r, number: "99999" }));
  expect(updatePosterior(changed, c, "x", b.state).action).toBe("rebuild");
  const corrupt = structuredClone(b.state);
  corrupt.counts[0][0]++;
  expect(updatePosterior(rows, c, "x", corrupt).action).toBe("rebuild");
  expect(updatePosterior(rows, c, "x", corrupt).reason).toMatch(/计数/);
  const w = updatePosterior(rows, { ...c, mode: "window" }, "x", b.state);
  expect(w.used).toBe(20);
  expect(w.cells[0].mean).toBeCloseTo(0.1);
});
it("matches brute force minimum and maximum coverage for every budget", () => {
  const candidates = ["00000", "00001", "00010", "00100", "11111"],
    targets = ["00000", "00011", "00110", "11111"];
  const h = (a: string, b: string) =>
    [...a].filter((d, i) => d !== b[i]).length;
  for (let b = 0; b <= 5; b++) {
    let max = 0,
      min = 99;
    for (let m = 0; m < 32; m++) {
      const selected = candidates.filter((_, i) => m & (1 << i));
      const n = targets.filter((t) =>
        selected.some((s) => h(s, t) <= 1),
      ).length;
      if (selected.length <= b) max = Math.max(max, n);
      if (n === targets.length) min = Math.min(min, selected.length);
    }
    const r = solveCover(candidates, targets, {
      mode: "max",
      budget: b,
      radius: 1,
      nodes: 100000,
      milliseconds: 5000,
    });
    expect(r.status).toBe("OPTIMAL");
    expect(r.objective).toBe(max);
    expect(r.bound).toBe(max);
    const q = solveCover(candidates, targets, {
      mode: "min",
      budget: b,
      radius: 1,
      nodes: 100000,
      milliseconds: 5000,
    });
    expect(q.status).toBe(b >= min ? "OPTIMAL" : "INFEASIBLE");
    if (b >= min) expect(q.objective).toBe(min);
  }
});
it("reports valid global bounds at limits and handles empty/invalid domains", () => {
  const c = {
    mode: "min" as const,
    budget: 3,
    radius: 0,
    nodes: 1,
    milliseconds: 5000,
  };
  expect(solveCover([], [], c).objective).toBe(0);
  expect(solveCover([], ["00000"], c).status).toBe("INFEASIBLE");
  expect(solveCover(["00000"], ["00000"], { ...c, budget: 0 }).status).toBe(
    "INFEASIBLE",
  );
  expect(() => solveCover(["123"], [], c)).toThrow();
  const r = solveCover(
    ["00000", "11111", "22222"],
    ["00000", "11111", "22222"],
    { ...c, mode: "max", budget: 1 },
  );
  expect(r.bound).toBeGreaterThanOrEqual(r.objective!);
  expect(r.covered).toBe(r.objective);
  expect(r.gap).toBeGreaterThanOrEqual(0);
});
it("checks posterior-scale Beta quantiles with an independent binomial-tail identity", () => {
  const fact = [0];
  for (let i = 1; i <= 2200; i++) fact[i] = fact[i - 1] + Math.log(i);
  for (const [a, b] of [
    [21, 189],
    [200, 1800],
    [2, 20],
  ])
    for (const p of [0.025, 0.975]) {
      const x = betaQuantile(p, a, b),
        n = a + b - 1;
      let sum = 0;
      for (let k = a; k <= n; k++)
        sum += Math.exp(
          fact[n] -
            fact[k] -
            fact[n - k] +
            k * Math.log(x) +
            (n - k) * Math.log1p(-x),
        );
      expect(sum).toBeCloseTo(p, 7);
    }
});
it("certifies global bounds against exhaustive optima on many small set systems", () => {
  let state = 91;
  const random = () => {
      state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
      return state / 4294967296;
    },
    number = () =>
      Array.from({ length: 5 }, () => Math.floor(random() * 3)).join("");
  for (let trial = 0; trial < 12; trial++) {
    const cs = [...new Set(Array.from({ length: 8 }, number))],
      ts = [...new Set(Array.from({ length: 10 }, number))],
      B = 3,
      radius = 2;
    let optimumMax = 0,
      optimumMin = Infinity;
    for (let m = 0; m < 2 ** cs.length; m++) {
      const ns = cs.filter((_, i) => m & (1 << i));
      if (ns.length > B) continue;
      const hits = ts.filter((t) =>
        ns.some((s) => [...t].filter((d, p) => d !== s[p]).length <= radius),
      ).length;
      optimumMax = Math.max(optimumMax, hits);
      if (hits === ts.length) optimumMin = Math.min(optimumMin, ns.length);
    }
    for (const mode of ["min", "max"] as const) {
      const c = { mode, budget: B, radius, nodes: 100000, milliseconds: 5000 },
        full = solveCover(cs, ts, c),
        limited = solveCover(cs, ts, { ...c, nodes: 1 });
      if (mode === "max") {
        expect(full.objective).toBe(optimumMax);
        expect(limited.bound!).toBeGreaterThanOrEqual(optimumMax);
        expect(limited.objective!).toBeLessThanOrEqual(optimumMax);
      } else if (Number.isFinite(optimumMin)) {
        expect(full.objective).toBe(optimumMin);
        expect(limited.bound!).toBeLessThanOrEqual(optimumMin);
      } else expect(full.status).toBe("INFEASIBLE");
    }
  }
});
