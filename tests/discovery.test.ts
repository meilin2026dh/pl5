import { describe, it, expect } from "vitest";
import {
  fitTensor,
  fitRatio,
  auc,
  diversify,
} from "../src/domain/discovery/models";
import { analyzeDiscovery } from "../src/domain/discovery/engine";
import { defaultDiscovery } from "../src/domain/discovery/config";
import { defaultPositions, validateInput } from "../src/domain/pick5";
const initialInput = { positions: defaultPositions(), rules: [] };
describe("discovery models", () => {
  it("has normalized positive TT and learns correlated digits", () => {
    const model = fitTensor(
      Array.from({ length: 120 }, (_, i) => (i % 2 ? "11111" : "00000")),
      2,
      7,
    );
    let sum = 0;
    for (let i = 0; i < 100000; i++)
      sum += model.prob(String(i).padStart(5, "0"));
    expect(sum).toBeCloseTo(1, 9);
    expect(model.prob("00000")).toBeGreaterThan(model.prob("01010") * 10);
    expect(model.trace.every(Number.isFinite)).toBe(true);
  });
  it("uses seeded pure noise and produces finite ratio scores", () => {
    const a = fitRatio(Array(80).fill("12345"), 11),
      b = fitRatio(Array(80).fill("12345"), 11);
    expect(a.score("12345")).toBe(b.score("12345"));
    expect(a.score("12345")).toBeGreaterThan(a.score("99999"));
    expect(auc([0.5, 0.5], [1, 0])).toBe(0.5);
    expect(auc([1, 0], [1, 0])).toBe(1);
  });
  it("greedy DPP spreads equal-quality candidates and rejects invalid limits", () => {
    const r = diversify(["00000", "00001", "99999"], [0, 0, 0], 2, 1);
    expect(r.numbers).toEqual(["00000", "99999"]);
    expect(new Set(r.numbers).size).toBe(2);
    expect(() => diversify(["00000"], [0], 2, 1)).toThrow();
  });
  it("separates all time segments and does not fit final answers", () => {
    const history = Array.from({ length: 150 }, (_, i) => ({
      issue: String(i + 1),
      date: new Date(Date.UTC(2025, 0, i + 1)).toISOString().slice(0, 10),
      number: String(i % 10).repeat(5),
    }));
    const c = {
      ...defaultDiscovery,
      train: 80,
      validation: 20,
      calibration: 20,
      test: 10,
      pool: 16,
      budget: 3,
      model: "tensor" as const,
    };
    const input = { ...initialInput, history, historySource: "test" };
    const a = analyzeDiscovery(input, c);
    const b = analyzeDiscovery(
      {
        ...input,
        history: history.map((r, i) =>
          i >= 140 ? { ...r, number: "98765" } : r,
        ),
      },
      c,
    );
    expect(a.modelDigest).toBe(b.modelDigest);
    expect(a.numbers).toEqual(b.numbers);
    expect(a.ranges.train.end).toBe("100");
    expect(a.ranges.test.start).toBe("141");
    expect(a.numbers.length).toBe(3);
    expect(a.subsetGuarantee).toBe(false);
    expect(() => analyzeDiscovery(input, { ...c, budget: 17 })).toThrow();
  });
});

it("keeps uniform-score ties and records all rolling folds", async () => {
  const { walkDiscovery } = await import("../src/domain/discovery/engine");
  const history = Array.from({ length: 150 }, (_, i) => ({
    issue: String(i + 1),
    date: new Date(Date.UTC(2025, 0, i + 1)).toISOString().slice(0, 10),
    number: String((i * 7919) % 100000).padStart(5, "0"),
  }));
  const c = {
    ...defaultDiscovery,
    train: 80,
    validation: 20,
    calibration: 20,
    test: 10,
    pool: 16,
    budget: 3,
  };
  const r = walkDiscovery({ ...initialInput, history }, c);
  expect(r.walkForward.map((r) => r.start)).toEqual(["121", "131", "141"]);
  expect(
    r.walkForward.every(
      (r) => r.numbers.length === 3 && r.ranges.train.count === 80,
    ),
  ).toBe(true);
  expect(r.calibration.size).toBeGreaterThanOrEqual(r.pool.length);
});
it("matches DPP Cholesky gains to independent 2x2 determinant", () => {
  const r = diversify(["00000", "00001", "99999"], [0, 0, 0], 2, 1);
  expect(Math.exp(r.gains.reduce((a, b) => a + b, 0))).toBeCloseTo(
    1 - Math.exp(-10),
    12,
  );
});
it("validates persisted discovery configuration and fixed cutoff", () => {
  expect(() =>
    validateInput({
      ...initialInput,
      discovery: { ...defaultDiscovery, sigma: NaN },
    }),
  ).toThrow();
  expect(() =>
    validateInput({
      ...initialInput,
      discovery: { ...defaultDiscovery, budget: 65 },
    }),
  ).toThrow();
});
it("registers new model and selector capability without conferring subset guarantees", async () => {
  const { methods } = await import("../src/domain/lab/registry");
  expect(methods.find((m) => m.id === "tensor-tt")?.type).toBe("distribution");
  expect(methods.find((m) => m.id === "dpp-map")?.conformal).toBe(false);
  expect(methods.find((m) => m.id === "ratio-mlp")).toBeTruthy();
});
