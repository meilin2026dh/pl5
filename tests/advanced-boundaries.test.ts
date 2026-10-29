import { describe, it, expect } from "vitest";
import { filter, defaultPositions, type Rule } from "../src/domain/pick5";
describe("advanced semantic boundaries", () => {
  it("classifies repeat neighbors by reference digit set instead of matching positions", () => {
    const rule: Rule = {
      id: "n",
      kind: "neighborCounts",
      enabled: true,
      mode: "include",
      values: ["5:0:0"],
    };
    expect(
      filter({
        positions: defaultPositions(),
        candidates: ["54321"],
        rules: [rule],
        history: [{ issue: "1", date: "2026-10-18", number: "12345" }],
      }).numbers,
    ).toEqual(["54321"]);
  });
  it("rejects an explicitly empty external candidate source", () => {
    expect(() =>
      filter({ positions: defaultPositions(), candidates: [], rules: [] }),
    ).toThrow();
  });
});
it("does not treat an unknown omission across a calendar gap as exact", () => {
  const rule: Rule = {
    id: "o",
    kind: "omission",
    enabled: true,
    mode: "include",
    values: [1],
    params: { positions: [0] },
  };
  expect(() =>
    filter({
      positions: defaultPositions(),
      candidates: ["00000"],
      rules: [rule],
      history: [
        { issue: "1", date: "2026-10-01", number: "00000" },
        { issue: "3", date: "2026-10-03", number: "11111" },
      ],
    }),
  ).toThrow();
});
it("rejects a frequency window longer than the available frozen history", () => {
  const rule: Rule = {
    id: "f",
    kind: "frequency",
    enabled: true,
    mode: "include",
    values: [1],
    params: { positions: [0], window: 30 },
  };
  expect(() =>
    filter({
      positions: defaultPositions(),
      candidates: ["00000"],
      rules: [rule],
      history: [{ issue: "1", date: "2026-10-01", number: "00000" }],
    }),
  ).toThrow();
});
it("supports distinct-digit hit ranges for a single dan set", () => {
  const rule: Rule = {
    id: "d",
    kind: "dan",
    enabled: true,
    mode: "include",
    values: [0, 1],
    params: { countMin: 2, countMax: 2 },
  };
  expect(
    filter({
      positions: defaultPositions(),
      candidates: ["00000", "00127", "22222"],
      rules: [rule],
    }).numbers,
  ).toEqual(["00127"]);
});
it("allows unrestricted positions inside categorical patterns", () => {
  const rule: Rule = {
    id: "p",
    kind: "oddPattern",
    enabled: true,
    mode: "include",
    values: ["1?0??"],
  };
  expect(
    filter({
      positions: defaultPositions(),
      candidates: ["12045", "12467", "22045"],
      rules: [rule],
    }).numbers,
  ).toEqual(["12045", "12467"]);
});

it("ignores stale tolerance minimum in strict mode", () => {
  expect(
    filter({
      positions: defaultPositions(),
      candidates: ["00000"],
      rules: [],
      combination: { mode: "strict", minimum: 2 },
    }).numbers,
  ).toEqual(["00000"]);
});
