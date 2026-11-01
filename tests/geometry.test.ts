import { backtest } from "../src/domain/backtest";
import { describe, it, expect } from "vitest";
import {
  defaultGeometry,
  geometryPoints,
  matchesGeometry,
  prepareGeometry,
  validateGeometry,
} from "../src/domain/geometry";
import {
  defaultPositions,
  filter as runFilter,
  type Rule,
} from "../src/domain/pick5";
import { decodePlans, encodePlan } from "../src/lib/plans";
const config = (method: typeof defaultGeometry.method, extra = {}) => ({
  ...defaultGeometry,
  method,
  ...extra,
});
describe("deterministic spatial shapes", () => {
  it("preserves digit order and distinguishes phone/calculator layouts", () => {
    expect(geometryPoints([0, 1, 2], "phone")).toEqual([
      [1, 3],
      [0, 0],
      [1, 0],
    ]);
    expect(geometryPoints([0, 1, 2], "calculator")).toEqual([
      [1, 3],
      [0, 2],
      [1, 2],
    ]);
    expect(matchesGeometry([1, 2, 3, 4, 5], config("line"))).toBe(true);
    expect(
      matchesGeometry([1, 2, 3, 4, 5], config("line", { layout: "phone" })),
    ).toBe(false);
    expect(
      matchesGeometry([1, 1, 1, 1, 1], config("line", { layout: "phone" })),
    ).toBe(false);
  });
  it("distinguishes straight, bent, V and inverted V without flat turns", () => {
    expect(matchesGeometry([9, 5, 1, 5, 9], config("v"))).toBe(true);
    expect(matchesGeometry([1, 5, 9, 5, 1], config("invertedV"))).toBe(true);
    expect(matchesGeometry([9, 5, 1, 5, 9], config("invertedV"))).toBe(false);
    expect(matchesGeometry([9, 1, 1, 5, 9], config("v"))).toBe(false);
    expect(matchesGeometry([1, 2, 4, 8, 9], config("polyline"))).toBe(true);
    expect(matchesGeometry([1, 2, 3, 4, 5], config("polyline"))).toBe(false);
  });
  it("tests numeric recurrences and spatial gap recurrences separately", () => {
    expect(matchesGeometry([1, 3, 5, 7, 9], config("arithmetic"))).toBe(true);
    expect(matchesGeometry([0, 0, 1, 2, 4], config("geometric"))).toBe(false);
    expect(matchesGeometry([1, 1, 2, 3, 5], config("fibonacci"))).toBe(true);
    expect(matchesGeometry([0, 0, 0, 0, 0], config("fibonacci"))).toBe(false);
    expect(matchesGeometry([1, 2, 4, 8, 9], config("geometric"))).toBe(false);
    expect(
      matchesGeometry(
        [1, 2, 4, 8, 9],
        config("geometric", { tolerance: 0.25 }),
      ),
    ).toBe(false);
    // Four keypad edge lengths are 1,1,2,3 (not a Fibonacci sequence).
    expect(
      matchesGeometry(
        [1, 2, 3, 1, 0],
        config("fibonacci", { layout: "phone", sequence: "gaps" }),
      ),
    ).toBe(false);
  });
  it("recognizes convex hulls and refuses collapsed polygons", () => {
    expect(
      matchesGeometry([1, 3, 7, 1, 3], config("triangle", { layout: "phone" })),
    ).toBe(true);
    expect(
      matchesGeometry(
        [1, 3, 9, 7, 1],
        config("trapezoid", { layout: "phone" }),
      ),
    ).toBe(true);
    expect(
      matchesGeometry([1, 2, 3, 2, 1], config("triangle", { layout: "phone" })),
    ).toBe(false);
    expect(
      matchesGeometry(
        [1, 3, 7, 1, 3],
        config("trapezoid", { layout: "phone" }),
      ),
    ).toBe(false);
  });
  it("matches symmetric multisets one-to-one and excludes degenerate sets", () => {
    expect(
      matchesGeometry([1, 3, 5, 7, 9], config("mirror", { layout: "phone" })),
    ).toBe(true);
    expect(
      matchesGeometry([1, 3, 5, 7, 9], config("central", { layout: "phone" })),
    ).toBe(true);
    expect(
      matchesGeometry([1, 1, 3, 5, 8], config("mirror", { layout: "phone" })),
    ).toBe(false);
    expect(
      matchesGeometry([1, 1, 1, 1, 1], config("mirror", { layout: "phone" })),
    ).toBe(false);
  });
});
const history = Array.from({ length: 5 }, (_, i) => ({
  issue: String(i + 1),
  date: `2026-01-0${i + 1}`,
  number: `${i + 1}0000`,
}));
it("appends a candidate to past-only history and refuses insufficient or future references", () => {
  const c = config("arithmetic", { source: "history", referenceIssue: "4" });
  expect(prepareGeometry(c, history).test("50000")).toBe(true);
  expect(prepareGeometry(c, history).test("60000")).toBe(false);
  expect(() => prepareGeometry({ ...c, referenceIssue: "3" }, history)).toThrow(
    /不足/,
  );
  expect(() => prepareGeometry({ ...c, referenceIssue: "9" }, history)).toThrow(
    /参考期/,
  );
});
it("validates malformed imported configurations and integrates include/exclude and saved plans", () => {
  expect(() =>
    validateGeometry({ ...defaultGeometry, tolerance: NaN }),
  ).toThrow();
  expect(() => validateGeometry({ ...defaultGeometry, position: 5 })).toThrow();
  expect(() =>
    validateGeometry({ ...defaultGeometry, method: "unknown" }),
  ).toThrow();
  const rule: Rule = {
    id: "geo",
    kind: "geometry",
    values: [],
    enabled: true,
    mode: "include",
    geometry: config("arithmetic"),
  };
  const input = {
    positions: defaultPositions(),
    candidates: ["13579", "12345", "11235"],
    rules: [rule],
  };
  expect(runFilter(input).numbers).toEqual(["12345", "13579"]);
  expect(
    runFilter({ ...input, rules: [{ ...rule, mode: "exclude" }] }).numbers,
  ).toEqual(["11235"]);
  const plan = encodePlan("空间", input);
  expect(
    decodePlans(JSON.stringify({ schemaVersion: 1, plans: [plan] }))[0].input,
  ).toEqual(input);
});

it("supports non-degenerate geometric subpaths and enforces enough distances", () => {
  expect(matchesGeometry([1, 2, 4], config("geometric", { length: 3 }))).toBe(
    true,
  );
  expect(
    matchesGeometry([8, 4, 2, 1], config("geometric", { length: 4 })),
  ).toBe(true);
  expect(() =>
    validateGeometry(config("arithmetic", { length: 3, sequence: "gaps" })),
  ).toThrow(/至少需要4/);
  expect(() =>
    validateGeometry(config("line", { length: 5, position: 1 })),
  ).toThrow();
  const c = config("geometric", { length: 3, position: 1 });
  expect(prepareGeometry(c).test("01249")).toBe(true);
  expect(prepareGeometry(c).test("01259")).toBe(false);
});
it("has exactly 26 five-digit arithmetic paths in the complete universe", () => {
  const r: Rule = {
    id: "a",
    kind: "geometry",
    enabled: true,
    mode: "include",
    values: [],
    geometry: config("arithmetic"),
  };
  expect(
    runFilter({ positions: defaultPositions(), rules: [r] }).numbers,
  ).toHaveLength(26);
});

it("replays spatial history with rolling past references rather than the saved future reference", () => {
  const r: Rule = {
    id: "geo",
    kind: "geometry",
    enabled: true,
    mode: "include",
    values: [],
    geometry: config("arithmetic", { source: "history", referenceIssue: "5" }),
  };
  const replay = backtest(
    { positions: defaultPositions(), rules: [r], history },
    5,
  );
  expect(replay.map((r) => r.status)).toEqual([
    "insufficient",
    "insufficient",
    "insufficient",
    "insufficient",
    "retained",
  ]);
  expect(replay.at(-1)?.referenceIssue).toBe("4");
});
it("applies exact tolerance boundaries without silently merging vertices", () => {
  expect(
    matchesGeometry([9, 5, 0], config("line", { length: 3, tolerance: 0.25 })),
  ).toBe(true);
  expect(
    matchesGeometry([9, 5, 0], config("line", { length: 3, tolerance: 0.24 })),
  ).toBe(false);
  expect(
    matchesGeometry(
      [1, 2, 4, 7, 8],
      config("mirror", { layout: "phone", axis: "horizontal" }),
    ),
  ).toBe(true);
  expect(
    matchesGeometry(
      [1, 2, 4, 7, 8],
      config("mirror", { layout: "phone", axis: "vertical" }),
    ),
  ).toBe(false);
});
it("supports grouped tolerant filtering and rejects corrupted spatial plan imports", () => {
  const a: Rule = {
    id: "a",
    kind: "geometry",
    enabled: true,
    mode: "include",
    values: [],
    group: "arithmetic",
    geometry: config("arithmetic"),
  };
  const b: Rule = { ...a, id: "b", group: "shape", geometry: config("v") };
  const input = {
    positions: defaultPositions(),
    rules: [a, b],
    candidates: ["13579", "95159", "11235"],
    combination: { mode: "atLeast" as const, minimum: 1 },
  };
  expect(runFilter(input).numbers).toEqual(["13579", "95159"]);
  expect(
    runFilter({ ...input, combination: { ...input.combination, minimum: 2 } })
      .numbers,
  ).toEqual([]);
  const plan = encodePlan("几何", input);
  plan.input.rules[0].geometry!.tolerance = NaN;
  expect(() =>
    decodePlans(JSON.stringify({ schemaVersion: 1, plans: [plan] })),
  ).toThrow(/空间/);
});
