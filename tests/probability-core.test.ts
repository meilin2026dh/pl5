import { it, expect } from "vitest";
import {
  fitModel,
  pmf,
  probability,
  updateModel,
  kinds,
  priors,
  evidence,
} from "../src/domain/probability/models";
import { conformal } from "../src/domain/probability/sets";
import {
  transportProfile,
  transportBounds,
} from "../src/domain/probability/transport";
import { onlineReplay } from "../src/domain/probability/online";
const rows = Array.from({ length: 80 }, (_, i) => ({
  issue: String(i + 1),
  date: new Date(Date.UTC(2025, 0, i + 1)).toISOString().slice(0, 10),
  number: i % 2 ? "11111" : "00000",
}));
it("normalizes all four complete joint distributions and preserves unseen contexts", () => {
  for (const kind of kinds) {
    const m = fitModel(kind, rows, 10),
      p = pmf(m);
    expect(p.length).toBe(100000);
    expect(p.reduce((a, b) => a + b, 0)).toBeCloseTo(1, 10);
    expect(p.every((x) => x > 0)).toBe(true);
    expect(p[0]).toBeCloseTo(probability(m, "00000"), 14);
  }
});
it("integrates sequence probability rather than multiplying a multinomial coefficient", () => {
  const m = fitModel("I", rows.slice(0, 2), 10);
  // Each position observes 0 then 1: (1/10)*(1/11), independent Dirichlet(1).
  expect(m.logEvidence).toBeCloseTo(5 * Math.log(1 / 110), 12);
  const empty = fitModel("J2", [], 10);
  let l = 0;
  for (const r of rows) {
    l += Math.log(probability(empty, r.number));
    updateModel(empty, r.number);
  }
  expect(l).toBeCloseTo(fitModel("J2", rows, 10).logEvidence, 10);
  const e = evidence(rows, 10);
  const best = e.reduce((a, b) => (a.bits < b.bits ? a : b));
  expect(best.posterior).toBe(Math.max(...e.map((x) => x.posterior)));
  expect(e.find((x) => x.kind === "U")!.bits).toBeCloseTo(
    1 + rows.length * 5 * Math.log2(10),
    9,
  );
  expect(priors).toEqual([0.5, 1 / 6, 1 / 6, 1 / 6]);
});
it("uses finite sample quantile, inclusive ties, and infinite threshold", () => {
  const p = Float64Array.from([0.5, 0.3, 0.2]);
  expect(conformal(p, [0, 1, 2], 0.5).indices).toEqual([0, 1]);
  expect(conformal(p, [0, 1], 0.99).threshold).toBeNull();
  const uniform = conformal(
    new Float64Array(100000).fill(0.00001),
    [1, 99, 555],
    0.5,
  );
  expect(uniform.indices).toHaveLength(100000);
});
it("certifies exact W1 event mass using distances to the complement", () => {
  // Alphabet 10, 2 positions. S consists of strings with at least one zero.
  const mask = Uint8Array.from({ length: 100 }, (_, i) =>
    Number(i < 10 || i % 10 === 0),
  );
  const p = new Float64Array(100).fill(0.01),
    profile = transportProfile(mask, [p], 2);
  expect(profile.inside[0][1]).toBeCloseTo(0.18);
  expect(profile.inside[0][2]).toBeCloseTo(0.01);
  expect(transportBounds(profile, 0)[0]).toMatchObject({
    lower: expect.any(Number),
  });
  expect(transportBounds(profile, 0)[0].lower).toBeCloseTo(0.19);
  expect(transportBounds(profile, 0.18)[0].lower).toBeCloseTo(0.01);
  expect(transportBounds(profile, 0.19)[0].lower).toBeCloseTo(0.005);
  expect(transportBounds(profile, 0.2)[0].lower).toBeCloseTo(0);
  expect(
    transportBounds(transportProfile(new Uint8Array(100).fill(1), [p], 2), 5)[0]
      .lower,
  ).toBe(1);
  expect(
    transportBounds(transportProfile(new Uint8Array(100), [p], 2), 5)[0].upper,
  ).toBe(0);
});
it("keeps online prefixes causal, replay idempotent, revisions rebuilt and regret bounded", () => {
  const a = onlineReplay(rows.slice(0, 40), rows.slice(40, 60), 10, "test");
  const b = onlineReplay(
    rows.slice(0, 40),
    rows.slice(40),
    10,
    "test",
    a.state,
  );
  expect(b.trace.slice(0, 20)).toEqual(a.trace);
  expect(b.regret).toBeLessThanOrEqual(b.bound + 1e-9);
  expect(
    onlineReplay(rows.slice(0, 40), rows.slice(40), 10, "test", b.state).trace,
  ).toEqual(b.trace);
  const revised = rows
    .slice(40)
    .map((r, i) => (i ? r : { ...r, number: "99999" }));
  const c = onlineReplay(rows.slice(0, 40), revised, 10, "test", b.state);
  expect(c.rebuilt).toBe(true);
  expect(c.trace).not.toEqual(b.trace);
});
it("matches an independent Dirichlet gamma-product calculation for the joint graph", () => {
  const logGammaInteger = (n: number) => {
    let s = 0;
    for (let k = 1; k < n; k++) s += Math.log(k);
    return s;
  };
  let logE = 0;
  for (let pos = 0; pos < 5; pos++) {
    const parents = Math.min(pos, 2),
      q = 10 ** parents,
      a = 1000 / q,
      cell = a / 10,
      tables = new Map<string, number[]>();
    for (const r of rows) {
      const key = r.number.slice(pos - parents, pos),
        counts = tables.get(key) ?? Array(10).fill(0);
      counts[Number(r.number[pos])]++;
      tables.set(key, counts);
    }
    for (const counts of tables.values()) {
      logE +=
        logGammaInteger(a) -
        logGammaInteger(a + counts.reduce((x, y) => x + y, 0));
      for (const n of counts)
        logE += logGammaInteger(cell + n) - logGammaInteger(cell);
    }
  }
  expect(fitModel("J2", rows, 1000).logEvidence).toBeCloseTo(logE, 9);
});
