import { describe, it, expect } from "vitest";
import { buildStats, researchHistory } from "../src/domain/research/statistics";
import {
  fitFilter,
  validateFilterParameter,
} from "../src/domain/research/filters";
import fixture from "./fixtures/research-reference.json";
import {
  defaultResearch,
  type FilterMethod,
} from "../src/domain/research/types";
const rows = fixture.numbers.map((number, i) => ({
  issue: String(i + 1),
  date: new Date(Date.UTC(2024, 0, i + 1)).toISOString().slice(0, 10),
  number,
}));
describe("research source formulas", () => {
  for (const entry of fixture.cases)
    it(entry.method, () => {
      const fitted = fitFilter(
        entry.method as FilterMethod,
        entry.parameter,
        buildStats(rows),
      );
      let count = 0;
      let hash = 2166136261;
      for (let i = 0; i < 100000; i++) {
        const keep = fitted.test(String(i).padStart(5, "0"));
        if (keep) count++;
        hash = Math.imul(hash ^ (keep ? 1 : 0), 16777619) >>> 0;
      }
      expect({ count, hash }).toEqual({ count: entry.count, hash: entry.hash });
    });
  it("validates the entire snapshot before cutoff and requires exact window", () => {
    expect(
      researchHistory(
        { ...defaultResearch, window: 2, referenceIssue: "3" },
        rows,
      ).map((x) => x.issue),
    ).toEqual(["2", "3"]);
    expect(() =>
      researchHistory({ ...defaultResearch, window: rows.length + 1 }, rows),
    ).toThrow();
    expect(() =>
      researchHistory({ ...defaultResearch, window: 1 }, [
        ...rows,
        { ...rows[0], number: "bad" },
      ]),
    ).toThrow();
    expect(() =>
      researchHistory(
        { ...defaultResearch, window: 1, referenceIssue: "missing" },
        rows,
      ),
    ).toThrow();
  });
  it("rejects unknown omission instead of inventing window length", () => {
    const stats = buildStats(rows.slice(0, 1));
    expect(stats.omissions[0][9]).toBe(-1);
    expect(fitFilter("omission", 100, stats).test("99999")).toBe(false);
  });
  it("uses mathematical zero variance and source frequency fallback", () => {
    const stats = buildStats([
      { issue: "1", date: "2024-01-01", number: "00000" },
    ]);
    expect(stats.sd).toBe(0);
    expect(fitFilter("sumSigma", 2, stats).test("00001")).toBe(false);
    expect(fitFilter("oddFrequency", 1.0, stats).test("22222")).toBe(true);
  });
  it("frequency fallback chooses the first most frequent feature deterministically", () => {
    const stats = buildStats([
      { issue: "1", date: "2024-01-01", number: "00000" },
      { issue: "2", date: "2024-01-02", number: "11111" },
    ]);
    const fitted = fitFilter("oddFrequency", 1, stats);
    expect(fitted.diagnostics.fallback).toBe(true);
    expect(fitted.test("22222")).toBe(true);
    expect(fitted.test("11111")).toBe(false);
  });
  it("rejects duplicate dates, duplicate issues and impossible dates, including future rows", () => {
    for (const extra of [
      { ...rows[0], issue: "other" },
      { ...rows[0], date: "2025-01-01" },
      { issue: "future", date: "2025-02-30", number: "00000" },
    ])
      expect(() =>
        researchHistory(
          { ...defaultResearch, window: 1, referenceIssue: "1" },
          [...rows, extra],
        ),
      ).toThrow();
    const reverse = [...rows].reverse();
    expect(
      researchHistory({ ...defaultResearch, window: 2 }, reverse).map(
        (r) => r.issue,
      ),
    ).toEqual(["74", "75"]);
    expect(reverse[0].issue).toBe("75");
  });
  it("rejects invalid parameters", () => {
    for (const [method, value] of [
      ["hotcold", 1.5],
      ["bayes", NaN],
      ["samePosition", 6],
      ["sumSigma", -1],
    ] as const)
      expect(() => validateFilterParameter(method, value)).toThrow();
  });
});
