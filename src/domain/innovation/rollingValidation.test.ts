import { describe, expect, it } from "vitest";
import { rollingExclusion } from "./rollingValidation";
import { shiftOperators } from "./dualEngine";
const rows = Array.from({ length: 60 }, (_, i) => ({
  issue: String(i + 1).padStart(5, "0"),
  draw: String((i * 13) % 100000).padStart(5, "0"),
  externalDigit: (i * 7) % 10,
  availableBeforeDraw: true,
}));
describe("V3.5 rolling exclusion", () => {
  it("runs disjoint future windows with past-only fitting", () => {
    const r = rollingExclusion(rows, shiftOperators(), 20, 10);
    expect(r.windows).toHaveLength(4);
    expect(r.totalTestRows).toBe(40);
    expect(r.windows[0]!.trainEnd < r.windows[0]!.testStart).toBe(true);
    expect(r.eligibleForProduction).toBe(false);
  });
  it("rejects future features", () => {
    expect(() => rollingExclusion([{ ...rows[0]!, availableBeforeDraw: false }, ...rows.slice(1)], shiftOperators(), 20, 10)).toThrow();
  });
  it("rejects unordered issue identifiers", () => {
    expect(() => rollingExclusion([...rows].reverse(), shiftOperators(), 20, 10)).toThrow();
  });
});
