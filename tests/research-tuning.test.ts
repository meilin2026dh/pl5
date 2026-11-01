import { it, expect } from "vitest";
import { pool, presets } from "../src/domain/research/presets";
import {
  validationFolds,
  chooseParameter,
} from "../src/domain/research/tuning";
import { defaultResearch } from "../src/domain/research/types";
const rows = Array.from({ length: 50 }, (_, i) => ({
  issue: String(i + 1),
  date: new Date(Date.UTC(2026, 0, i + 1)).toISOString().slice(0, 10),
  number: "00000",
}));
it("retains the 57 source pool entries and six packages", () => {
  expect(pool.length).toBe(57);
  expect(Object.keys(presets)).toHaveLength(6);
});
it("uses only records preceding each validation segment and counts duplicate outcomes", () => {
  const folds = validationFolds(
    { ...defaultResearch, folds: 3, validationSize: 10 },
    rows,
  );
  expect(folds.map((f) => f.training.length)).toEqual([20, 30, 40]);
  expect(folds.map((f) => f.validation.length)).toEqual([10, 10, 10]);
  expect(folds[0].training.at(-1)?.issue).toBe("20");
  expect(folds[0].validation[0].issue).toBe("21");
});
it("chooses each objective and makes fallback explicit", () => {
  const a = [
    { parameter: 1, coverage: 0.7, averageCount: 20000, allHit: false },
    { parameter: 2, coverage: 0.95, averageCount: 50000, allHit: false },
  ];
  expect(chooseParameter(a, "lift60").entry.parameter).toBe(1);
  expect(chooseParameter(a, "cov90").entry.parameter).toBe(2);
  expect(chooseParameter(a, "strict").fallback).toBe(true);
});
import { tuneResearch } from "../src/domain/research/tuning";
it("never trains a fold on its validation answers and counts all repeated periods", () => {
  const data = rows
    .slice(0, 30)
    .map((r, i) => ({ ...r, number: i < 20 ? "00000" : "99999" }));
  const result = tuneResearch(
    {
      ...defaultResearch,
      method: "auto",
      window: 30,
      folds: 1,
      validationSize: 10,
      family: "hotcold",
      selection: "strict",
    },
    data,
  );
  expect(result.diagnostics.validationCount).toBe(10);
  expect(result.diagnostics.validationCoverage).toBe(0);
  expect(result.diagnostics.fallback).toBe(true);
  expect(result.selected).toEqual([{ method: "hotcold", parameter: 4 }]);
});
it("selects a deterministic feasible greedy intersection on frozen folds", () => {
  const result = tuneResearch(
    {
      ...defaultResearch,
      method: "greedy",
      window: 30,
      folds: 1,
      validationSize: 10,
      targetCoverage: 1,
      maxSteps: 2,
    },
    rows.slice(0, 30),
  );
  expect(result.selected.length).toBeGreaterThan(0);
  expect(result.diagnostics.validationCount).toBe(10);
  expect(result.diagnostics.validationCoverage).toBe(1);
  expect(result.diagnostics.averageCount).toBe(1);
});
