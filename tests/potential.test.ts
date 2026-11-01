import { expect, it } from "vitest";
import {
  fitPotential,
  defaultPotential,
} from "../src/domain/research/potential";
import { defaultResearch } from "../src/domain/research/types";
import {
  prepareResearch,
  validateResearchConfig,
} from "../src/domain/research";
import { defaultPositions, filter } from "../src/domain/pick5";
const history = (digits: string[]) =>
  digits.map((number, i) => ({
    issue: String(i + 1),
    date: new Date(Date.UTC(2026, 0, i + 1)).toISOString().slice(0, 10),
    number,
  }));
const config = { ...defaultPotential, short: 2, blocks: 3, sensitivity: 0.1 };
const rows = history([
  "00000",
  "11111",
  "00000",
  "00000",
  "11111",
  "11111",
  "00000",
  "00000",
]);
it("detects warming/cooling crossings and alternating block states without treating neutral as alternating", () => {
  const m = fitPotential(rows, config);
  const zero = m.signals[0][0],
    one = m.signals[0][1];
  expect(zero.states).toEqual(["热", "冷", "热"]);
  expect(zero.crossing).toBe("升温越界");
  expect(one.crossing).toBe("降温越界");
  expect(zero.alternation).toBe(1);
  expect(zero.momentum).toBeGreaterThan(0);
  expect(m.signals[0][9].alternation).toBe(0);
  expect(
    fitPotential(rows, { ...config, mode: "warming" }).score("00000"),
  ).toBeGreaterThan(
    fitPotential(rows, { ...config, mode: "warming" }).score("11111"),
  );
  expect(
    fitPotential(rows, { ...config, mode: "cooling" }).score("11111"),
  ).toBeGreaterThan(
    fitPotential(rows, { ...config, mode: "cooling" }).score("00000"),
  );
});
it("scores spatial state clustering independently of digit repetition", () => {
  const base = fitPotential(rows, { ...config, clusterWeight: 0 }),
    weighted = fitPotential(rows, { ...config, clusterWeight: 2 });
  expect(weighted.score("00000") - base.score("00000")).toBe(2);
  expect(weighted.score("01010") - base.score("01010")).toBe(0);
});
it("bounds history and configuration rather than silently shortening windows", () => {
  expect(() => fitPotential(rows.slice(1), config)).toThrow("历史不足");
  for (const potential of [
    { ...config, short: 0 },
    { ...config, blocks: 2 },
    { ...config, sensitivity: NaN },
    { ...config, mode: "bad" },
    { ...config, clusterWeight: -1 },
  ])
    expect(() =>
      validateResearchConfig({
        ...defaultResearch,
        window: 8,
        method: "potential",
        potential,
      }),
    ).toThrow();
});
it("uses a frozen cutoff and dynamic full-universe rank threshold with stable seeded ties", () => {
  const c = {
    ...defaultResearch,
    method: "potential" as const,
    window: 8,
    referenceIssue: "8",
    potential: config,
    retain: 0.01,
    ties: "seeded" as const,
  };
  const a = prepareResearch(c, rows),
    b = prepareResearch(c, [
      ...rows,
      ...history(["99999"]).map((r) => ({
        ...r,
        issue: "9",
        date: "2026-01-09",
      })),
    ]);
  expect(a.diagnostics).toEqual(b.diagnostics);
  expect(a.diagnostics).toMatchObject({
    actualCount: 1000,
    universe: 100000,
    lastIssue: "8",
  });
  expect(a.test("00000")).toBe(b.test("00000"));
  const input = {
    positions: defaultPositions(),
    history: rows,
    rules: [
      {
        id: "p",
        kind: "research" as const,
        enabled: true,
        mode: "include" as const,
        values: [],
        research: c,
      },
    ],
  };
  expect(filter(input).numbers).toHaveLength(1000);
  const next = prepareResearch(
    { ...c, referenceIssue: undefined },
    history([
      "00000",
      "11111",
      "00000",
      "00000",
      "11111",
      "11111",
      "00000",
      "00000",
      "99999",
    ]),
  );
  expect(next.diagnostics.boundaryScore).not.toBe(a.diagnostics.boundaryScore);
});
it("does not label a movement inside the neutral band as a boundary crossing", () => {
  expect(
    fitPotential(rows, { ...config, sensitivity: 5 }).signals[0][0].crossing,
  ).toBe("未越界");
});
it("replays a target using the preceding cutoff, and rejects a model with no parameters", async () => {
  const { backtest } = await import("../src/domain/backtest");
  const c = {
    ...defaultResearch,
    method: "potential" as const,
    window: 8,
    potential: config,
    retain: 0.01,
    ties: "seeded" as const,
  };
  const all = history([
    "00000",
    "11111",
    "00000",
    "00000",
    "11111",
    "11111",
    "00000",
    "00000",
    "99999",
  ]);
  const input = {
    positions: defaultPositions(),
    history: all,
    rules: [
      {
        id: "p",
        kind: "research" as const,
        enabled: true,
        mode: "include" as const,
        values: [],
        research: c,
      },
    ],
  };
  const replay = backtest(input, 9);
  expect(replay.slice(0, 8).every((r) => r.status === "insufficient")).toBe(
    true,
  );
  expect(replay[8].referenceIssue).toBe("8");
  expect(replay[8].status).toBe(
    prepareResearch({ ...c, referenceIssue: "8" }, all).test("99999")
      ? "retained"
      : "removed",
  );
  expect(() =>
    validateResearchConfig({ ...c, potential: undefined }),
  ).toThrow();
});
