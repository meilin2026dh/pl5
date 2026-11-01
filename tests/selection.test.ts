import { it, expect } from "vitest";
import { structure, selectPortfolio } from "../src/domain/selection/engine";
import { defaultSelection } from "../src/domain/selection/config";
import { defaultPositions } from "../src/domain/pick5";
const history = Array.from({ length: 60 }, (_, i) => ({
  issue: String(i + 1),
  date: new Date(Date.UTC(2026, 0, i + 1)).toISOString().slice(0, 10),
  number: String((i * 7919) % 100000).padStart(5, "0"),
}));
const input = { positions: defaultPositions(), rules: [], history };
it("computes positive-difference AC and sorted gaps including zeroes", () => {
  expect(structure("00000", 3)).toEqual({
    ac: -4,
    gaps: [0, 0, 0, 0],
    large: 0,
  });
  expect(structure("01269", 3)).toEqual({
    ac: 5,
    gaps: [1, 1, 4, 3],
    large: 2,
  });
});
it("runs exact, MC/GA and annealing with reproducibility, hard constraints and diverse output", () => {
  for (const method of ["exact", "mcga", "anneal"] as const) {
    const c = {
      ...defaultSelection,
      method,
      window: 40,
      samples: 100,
      population: 20,
      generations: 4,
      budget: 5,
      recent: 0,
      acMin: -4,
      acMax: 5,
      minLarge: 0,
      maxLarge: 4,
      maxSame: 3,
    };
    const a = selectPortfolio(input, c),
      b = selectPortfolio(input, c);
    expect(a).toEqual(b);
    expect(a.numbers.length).toBeGreaterThan(0);
    for (let i = 0; i < a.numbers.length; i++)
      for (const n of a.numbers.slice(i + 1))
        expect(
          [...n].filter((d, p) => d === a.numbers[i][p]).length,
        ).toBeLessThanOrEqual(3);
    expect(a.diagnostics.bestGap).toBeGreaterThanOrEqual(0);
    if (method === "exact") expect(a.diagnostics.bestGap).toBe(0);
  }
});
it("preserves existing constraints and never silently fills infeasible pools", () => {
  const c = {
    ...defaultSelection,
    window: 40,
    recent: 0,
    acMin: -4,
    acMax: 5,
    minLarge: 0,
    maxLarge: 4,
  };
  expect(
    selectPortfolio(
      {
        ...input,
        candidates: ["12345"],
        rules: [
          {
            id: "k",
            kind: "kill" as const,
            enabled: true,
            mode: "include" as const,
            values: [1],
          },
        ],
      },
      c,
    ).numbers,
  ).toEqual([]);
});
it("freezes historical cutoff despite extra future rows", () => {
  const c = {
    ...defaultSelection,
    window: 40,
    referenceIssue: "40",
    recent: 5,
    budget: 3,
  };
  expect(selectPortfolio(input, c)).toEqual(
    selectPortfolio({ ...input, history: history.slice(0, 40) }, c),
  );
});
it("audits AC distribution and integrates scalar/pattern gap filters", async () => {
  const { filter } = await import("../src/domain/pick5");
  const counts = new Map<number, number>();
  for (let i = 0; i < 100000; i++) {
    const a = structure(String(i).padStart(5, "0"), 3).ac;
    counts.set(a, (counts.get(a) || 0) + 1);
  }
  expect(counts.get(5)).toBe(480);
  expect(Math.max(...counts.keys())).toBe(5);
  expect(counts.get(-4)).toBe(10);
  const r = (
    kind: "ac" | "largeGaps" | "gapPattern",
    values: (string | number)[],
    params?: { gapThreshold: number },
  ) => ({
    id: kind,
    kind,
    values,
    params,
    enabled: true,
    mode: "include" as const,
  });
  expect(
    filter({
      ...input,
      candidates: ["01269", "12345", "00000"],
      rules: [r("ac", [5])],
    }).numbers,
  ).toEqual(["01269"]);
  expect(
    filter({
      ...input,
      candidates: ["01269", "12345"],
      rules: [r("gapPattern", ["SSLL"], { gapThreshold: 3 })],
    }).numbers,
  ).toEqual(["01269"]);
  expect(
    filter({
      ...input,
      candidates: ["01269", "12345"],
      rules: [r("largeGaps", [2], { gapThreshold: 3 })],
    }).numbers,
  ).toEqual(["01269"]);
});
it("uses set Jaccard separately from positional overlap and exposes exact seeding fallback", async () => {
  const { jaccard } = await import("../src/domain/selection/engine");
  expect(jaccard("12345", "54321")).toBe(1);
  expect(jaccard("00000", "00111")).toBe(0.5);
  const c = {
    ...defaultSelection,
    method: "mcga" as const,
    window: 40,
    recent: 0,
    acMin: -4,
    acMax: 5,
    minLarge: 0,
    maxLarge: 4,
    samples: 100,
    population: 10,
    generations: 1,
    budget: 3,
  };
  const a = selectPortfolio({ ...input, candidates: ["12345"] }, c);
  expect(a.numbers).toEqual(["12345"]);
  expect(a.diagnostics.exactSeedFallback).toBe(true);
  expect(a.diagnostics.shortfall).toBe(true);
  const b = selectPortfolio(
    { ...input, candidates: [history.at(-1)!.number] },
    { ...c, method: "exact", recent: 1, historySame: 5, jaccard: 0.99 },
  );
  expect(b.numbers).toEqual([]);
});
it("fits a deterministic temporal-feature shallow network and reports honest validation", async () => {
  const { learnScorer } = await import("../src/domain/selection/learning");
  const a = learnScorer(history.slice(0, 40), "neural", true, 42),
    b = learnScorer(history.slice(0, 40), "neural", true, 42);
  expect(a.score("00000")).toBe(b.score("00000"));
  expect(a.score("00000")).toBeGreaterThan(0);
  expect(a.score("00000")).toBeLessThan(1);
  expect(a.diagnostics).toMatchObject({
    features: 35,
    trainingEnd: "40",
    validationStart: "37",
    validationEnd: "40",
    trainingTargets: 20,
  });
  expect(a.diagnostics).toEqual(b.diagnostics);
});
it("persists selection settings and rejects malformed configurations", async () => {
  const { encodePlan, decodePlans } = await import("../src/lib/plans");
  const { validateSelection } = await import("../src/domain/selection/config");
  const plan = encodePlan("精选", { ...input, selection: defaultSelection });
  expect(
    decodePlans(JSON.stringify({ schemaVersion: 1, plans: [plan] }))[0].input
      .selection,
  ).toEqual(defaultSelection);
  for (const change of [
    { acMin: 6 },
    { acMin: 5, acMax: 0 },
    { gapThreshold: 0 },
    { budget: 201 },
    { population: 0 },
    { jaccard: NaN },
    { scorer: "xgboost" },
  ])
    expect(() =>
      validateSelection({
        ...defaultSelection,
        ...change,
      } as typeof defaultSelection),
    ).toThrow();
});
it("keeps neural training and selection identical under a fixed cutoff", () => {
  const c = {
    ...defaultSelection,
    scorer: "neural" as const,
    window: 40,
    referenceIssue: "40",
    recent: 0,
    budget: 2,
    acMin: -4,
    minLarge: 0,
    maxLarge: 4,
  };
  const limited = { ...input, candidates: ["12345", "54321", "01269"] };
  expect(selectPortfolio(limited, c)).toEqual(
    selectPortfolio({ ...limited, history: history.slice(0, 40) }, c),
  );
});
it("replays full portfolios with strictly prior training and rolls rule cutoffs", async () => {
  const { replaySelection } = await import("../src/domain/selection/engine");
  const rows = Array.from({ length: 42 }, (_, i) => ({
    issue: String(i + 1),
    date: new Date(Date.UTC(2026, 0, i + 1)).toISOString().slice(0, 10),
    number: "12345",
  }));
  const c = {
    ...defaultSelection,
    window: 40,
    recent: 0,
    acMin: -4,
    minLarge: 0,
    maxLarge: 4,
    budget: 1,
  };
  const source = {
    positions: defaultPositions(),
    history: rows,
    candidates: ["12345"],
    rules: [
      {
        id: "h",
        kind: "samePosition" as const,
        enabled: true,
        mode: "include" as const,
        values: [5],
        params: { referenceIssue: "42" },
      },
    ],
  };
  const replay = replaySelection(source, c);
  expect(replay).toHaveLength(10);
  expect(replay.slice(0, 8).every((r) => r.status === "insufficient")).toBe(
    true,
  );
  expect(replay.at(-1)).toMatchObject({
    issue: "42",
    referenceIssue: "41",
    status: "retained",
    selected: 1,
  });
  expect(
    replaySelection({ ...source, candidates: ["00000"] }, c).every(
      (r) => r.status === "outside",
    ),
  ).toBe(true);
});
it("enforces set Jaccard independently of positional overlap", () => {
  const c = {
    ...defaultSelection,
    window: 40,
    recent: 0,
    acMin: -4,
    minLarge: 0,
    maxLarge: 4,
    outputJaccard: 0.6,
    budget: 10,
  };
  const r = selectPortfolio(
    { ...input, candidates: ["12345", "54321", "67890"] },
    c,
  );
  expect(r.numbers).toHaveLength(2);
  for (let i = 0; i < r.numbers.length; i++)
    for (const b of r.numbers.slice(i + 1)) {
      const a = new Set(r.numbers[i]),
        other = new Set(b);
      const intersection = [...a].filter((d) => other.has(d)).length;
      expect(intersection / new Set([...a, ...other]).size).toBeLessThanOrEqual(
        0.6,
      );
    }
});
it("residual scoring excludes rows after the selected cutoff", () => {
  const c = {
    ...defaultSelection,
    scorer: "resnet" as const,
    window: 40,
    referenceIssue: "40",
    recent: 0,
    acMin: -4,
    minLarge: 0,
    maxLarge: 4,
    budget: 3,
  };
  const candidates = ["12345", "54321", "67890"];
  expect(selectPortfolio({ ...input, candidates }, c)).toEqual(
    selectPortfolio({ ...input, candidates, history: history.slice(0, 40) }, c),
  );
});
