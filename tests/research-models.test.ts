import reference from "./fixtures/research-model-reference.json";
import { describe, expect, it } from "vitest";
import { fitScores, combineDempster } from "../src/domain/research/models";
import { rankSelection } from "../src/domain/research/ranking";
import {
  defaultResearch,
  type ResearchStats,
} from "../src/domain/research/types";
function stats(numbers: string[]): ResearchStats {
  const digits = numbers.map((x) => [...x].map(Number));
  const counts = Array.from({ length: 5 }, () => Array(10).fill(0));
  const transitions = Array.from({ length: 5 }, () =>
    Array.from({ length: 10 }, () => Array(10).fill(0)),
  );
  digits.forEach((ds, i) =>
    ds.forEach((d, p) => {
      counts[p][d]++;
      if (i) transitions[p][digits[i - 1][p]][d]++;
    }),
  );
  return {
    rows: numbers.map((number, i) => ({
      issue: String(i),
      date: "2026-01-01",
      number,
    })),
    digits,
    n: numbers.length,
    counts,
    transitions,
    last: digits.at(-1)!,
    omissions: [],
    sums: [],
    spans: [],
    mean: 0,
    sd: 0,
    frequencies: {},
    multisets: new Map(),
  };
}
const config = { ...defaultResearch, method: "heatScore" as const };
describe("research scores and complete-universe ranking", () => {
  it("refuses near-total conflict instead of dividing by zero", () => {
    const a = Array(10).fill(0),
      b = Array(10).fill(0);
    a[0] = 1;
    b[9] = 1;
    expect(() => combineDempster(a, 0, b, 0)).toThrow(/冲突/);
    a[0] = 1 - 1e-14;
    b[9] = 1 - 1e-14;
    expect(() => combineDempster(a, 1e-14, b, 1e-14)).toThrow(/冲突/);
    const result = combineDempster(
      [0.5, ...Array(9).fill(0)],
      0.5,
      [0, 0.5, ...Array(8).fill(0)],
      0.5,
    );
    expect(result.mass.reduce((x, y) => x + y, 0) + result.theta).toBeCloseTo(
      1,
      12,
    );
  });
  it("matches independent Python source scores and exact marginal weights", () => {
    const st = stats(reference.numbers);
    for (const method of [
      "bma",
      "dsPlausibility",
      "dsBelief",
      "dsDempster",
    ] as const) {
      const model = fitScores({ ...config, method, windows: 5 }, st);
      for (const row of reference.scores) {
        const expected: number | string = row[method] as number | string;
        if (expected === "-Infinity")
          expect(model.score(row.number)).toBe(-Infinity);
        else
          expect(model.score(row.number)).toBeCloseTo(
            expected as number,
            method === "bma" ? 14 : 10,
          );
      }
      if (method === "bma")
        (model.details.weights as number[]).forEach((w, i) =>
          expect(w).toBeCloseTo(reference.weights[i], 10),
        );
    }
  });
  it("uses alpha .5 heat log likelihood and keeps leading zero", () => {
    const m = fitScores(config, stats(["00000", "12345"]));
    expect(m.score("00000")).toBeCloseTo(5 * Math.log(1.5 / 7), 12);
    expect(m.score("99999")).toBeLessThan(m.score("00000"));
  });
  it("normalizes seven BMA weights and predictive mass", () => {
    const m = fitScores(
      { ...config, method: "bma" },
      stats(["00000", "12345", "12345", "99999"]),
    );
    const weights = m.details.weights as number[];
    expect(weights).toHaveLength(7);
    expect(weights.reduce((a, b) => a + b, 0)).toBeCloseTo(1, 12);
    let sum = 0;
    for (let i = 0; i < 100000; i++) sum += m.score(String(i).padStart(5, "0"));
    expect(sum).toBeCloseTo(1, 10);
  });
  it("allows zero belief as negative infinity", () => {
    const m = fitScores({ ...config, method: "dsBelief" }, stats(["00000"]));
    expect(m.score("11111")).toBe(-Infinity);
    expect(m.score("00000")).toBe(0);
  });
  it("balanced windows cover remainder and reject insufficient windows", () => {
    const m = fitScores(
      { ...config, method: "dsDempster", windows: 2 },
      stats(Array(11).fill("01234")),
    );
    expect(m.details.windowSizes).toEqual([6, 5]);
    expect((m.details.conflicts as number[][])[0]).toHaveLength(1);
    expect(() =>
      fitScores(
        { ...config, method: "dsDempster", windows: 3 },
        stats(Array(11).fill("01234")),
      ),
    ).toThrow();
  });
  it("single-position model selects true strongest position", () => {
    const nums = Array.from(
      { length: 100 },
      (_, i) => `0${i % 10}${(i * 3) % 10}${(i * 7) % 10}${(i * 9) % 10}`,
    );
    const m = fitScores({ ...config, method: "sparseBest" }, stats(nums));
    expect(m.details.selectedPosition).toBe(0);
    expect(m.score("00000")).toBeGreaterThan(m.score("10000"));
  });
  it("inclusive and seeded ties report exact intended semantics", () => {
    const m = { score: () => 1, details: {} };
    const inclusive = rankSelection({ ...config, retain: 0.01 }, m);
    expect(inclusive.diagnostics.actualCount).toBe(100000);
    expect(inclusive.diagnostics.allUniform).toBe(true);
    const a = rankSelection({ ...config, ties: "seeded", retain: 0.01 }, m),
      b = rankSelection({ ...config, ties: "seeded", retain: 0.01 }, m),
      c = rankSelection(
        { ...config, ties: "seeded", retain: 0.01, seed: 7 },
        m,
      );
    let count = 0,
      difference = 0;
    for (let i = 0; i < 100000; i++) {
      const n = String(i).padStart(5, "0");
      count += Number(a.test(n));
      expect(a.test(n)).toBe(b.test(n));
      difference += Number(a.test(n) !== c.test(n));
    }
    expect(count).toBe(1000);
    expect(difference).toBeGreaterThan(0);
  });
  it("rejects NaN and positive infinity but accepts uniform negative infinity", () => {
    expect(() =>
      rankSelection(config, { score: () => NaN, details: {} }),
    ).toThrow();
    expect(() =>
      rankSelection(config, { score: () => Infinity, details: {} }),
    ).toThrow();
    expect(
      rankSelection(config, { score: () => -Infinity, details: {} }).diagnostics
        .actualCount,
    ).toBe(100000);
  });
});
