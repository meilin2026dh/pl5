import { it, expect } from "vitest";
import {
  analyzeProbability,
  inspectNumber,
} from "../src/domain/probability/engine";
import { defaultProbability } from "../src/domain/probability/config";
import { defaultPositions, validateInput } from "../src/domain/pick5";
const rows = Array.from({ length: 240 }, (_, i) => ({
  issue: String(i + 1),
  date: new Date(Date.UTC(2024, 0, i + 1)).toISOString().slice(0, 10),
  number: String((i * 7919) % 100000).padStart(5, "0"),
}));
const c = {
  ...defaultProbability,
  train: 100,
  calibration: 20,
  test: 30,
  budget: 10,
  referenceIssue: "200",
};
const input = {
  positions: defaultPositions(),
  rules: [],
  history: rows,
  historySource: "fixture",
};
it("separates selection/gate/calibration/test and refuses budget coverage promises", () => {
  const r = analyzeProbability(input, c);
  expect(r.ranges).toEqual({
    fit: ["51", "90"],
    gate: ["91", "150"],
    train: ["51", "150"],
    calibration: ["151", "170"],
    test: ["171", "200"],
  });
  expect(r.gate.useBias).toBe(false);
  expect(r.conformal.indices).toHaveLength(100000);
  expect(r.portfolio.numbers).toHaveLength(10);
  expect(r.portfolio.exactProbability).toBe(0.0001);
  expect(r.portfolio.inheritsCoverage).toBe(false);
  expect(r.conflict).toBe(true);
  expect(inspectNumber(r, "00000").probabilities).toHaveLength(4);
  expect(inspectNumber(r, r.portfolio.numbers[0]).rank).toBe(1);
  expect(inspectNumber(r, r.portfolio.numbers[0]).stage).toBe("uniform");
  expect(() => inspectNumber(r, "123")).toThrow();
});
it("does not let final answers or appended future change earlier decisions or portfolio", () => {
  const a = analyzeProbability(input, c),
    changed = rows.map((r, i) => (i >= 170 ? { ...r, number: "99999" } : r)),
    b = analyzeProbability({ ...input, history: changed }, c);
  expect(a.gate).toEqual(b.gate);
  expect(a.conformal).toEqual(b.conformal);
  expect(a.portfolio).toEqual(b.portfolio);
  const prefix = analyzeProbability(
    { ...input, history: rows.slice(0, 200) },
    c,
  );
  expect(a).toEqual(prefix);
});
it("blocks bad quality, insufficient data and invalid backup configuration", () => {
  expect(() =>
    analyzeProbability({ ...input, history: [rows[0], rows[0]] }, c),
  ).toThrow();
  expect(() =>
    analyzeProbability(
      { ...input, history: rows.slice(0, 100) },
      { ...c, referenceIssue: undefined },
    ),
  ).toThrow();
  expect(() =>
    validateInput({ ...input, probability: { ...c, target: 1 } }),
  ).toThrow();
  expect(() => validateInput({ ...input, probability: c })).not.toThrow();
});
it("keeps original source but does not silently intersect the conformal set with old rules", () => {
  const r = analyzeProbability({ ...input, candidates: ["00000", "00123"] }, c);
  expect(r.conformal.indices).toHaveLength(100000);
  expect(r.portfolio.numbers.sort()).toEqual(["00000", "00123"]);
  expect(r.sourceRestricted).toBe(true);
});
it("recognizes strong controlled joint dependence and reports it as a fixture only", () => {
  const history = Array.from({ length: 700 }, (_, i) => ({
    issue: String(i + 1),
    date: new Date(Date.UTC(2022, 0, i + 1)).toISOString().slice(0, 10),
    number: String(i % 10).repeat(5),
  }));
  const r = analyzeProbability(
    { ...input, history },
    { ...defaultProbability, budget: 20 },
  );
  expect(r.gate.useBias).toBe(true);
  const forced = analyzeProbability(
    { ...input, history },
    { ...defaultProbability, budget: 20, uniformOnly: true },
  );
  expect(forced.gate.kind).toBe("U");
  expect(forced.validation.budgetHits).toBeGreaterThanOrEqual(0);
  expect(forced.online.outputLoss).toBeCloseTo(200 * Math.log(100000), 8);
  expect(r.gate.kind).not.toBe("U");
  expect(r.conformal.indices.length).toBeLessThan(100000);
  expect(r.hypergraph.pairs.covered).toBeGreaterThan(0);
  expect(r.online.regret).toBeLessThanOrEqual(r.online.bound + 1e-8);
});
