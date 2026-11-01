import { it, expect } from "vitest";
import {
  hamming,
  neighbors,
  exactCoverage,
  freeEnergy,
  runInnovation,
} from "../src/domain/innovation/engine";
import { defaultInnovation } from "../src/domain/innovation/config";
import { defaultPositions } from "../src/domain/pick5";
it("full Hamming graph is regular, preserves leading zeroes", () => {
  expect(neighbors("00000")).toHaveLength(45);
  expect(new Set(neighbors("99999")).size).toBe(45);
  expect(hamming("00001", "10001")).toBe(1);
});
it("distinguishes geometric coverage from exact-match probability", () => {
  expect(exactCoverage(["00000"], ["00000", "00001"], 4).covered).toBe(2);
  expect(exactCoverage(["00000"], ["00000", "00001"], 5)).toMatchObject({
    covered: 1,
    total: 2,
    witness: "00001",
  });
});
it("entropy objective has correct analytic gradient", () => {
  const links = [
      [0, 1],
      [1, 2],
    ],
    p = [0.2, 0.3, 0.4],
    r = freeEnergy(p, links, 1, 0.1);
  for (let i = 0; i < 3; i++) {
    const a = [...p],
      b = [...p];
    a[i] += 1e-6;
    b[i] -= 1e-6;
    expect(r.gradient[i]).toBeCloseTo(
      (freeEnergy(a, links, 1, 0.1).loss - freeEnergy(b, links, 1, 0.1).loss) /
        2e-6,
      5,
    );
  }
});
const history = Array.from({ length: 40 }, (_, i) => ({
  issue: String(i + 1),
  date: new Date(Date.UTC(2026, 0, i + 1)).toISOString().slice(0, 10),
  number: String(i * 17).padStart(5, "0"),
}));
it("runs deterministically under hard guards and fixed budget", () => {
  const input = {
    positions: defaultPositions(),
    rules: [],
    history,
    candidates: ["00000", "00001", "11111", "22222"],
  };
  const c = {
    ...defaultInnovation,
    window: 40,
    budget: 2,
    simulations: 100,
    digits: "01",
    matches: 5,
  };
  const a = runInnovation(input, c);
  expect(a).toEqual(runInnovation(input, c));
  expect(a.numbers.length).toBeLessThanOrEqual(2);
  expect(a.risk.exactHit).toBe(a.numbers.length / 100000);
  expect(a.audit.guard.ok).toBe(true);
  expect(a.coverage.guaranteed).toBe(false);
});
it("GP posterior uncertainty shrinks at observed strategy", async () => {
  const { posterior, optimizeWeights } =
    await import("../src/domain/innovation/bo");
  const p = posterior([[1, 0, 0, 0]], [0.8], [1, 0, 0, 0]);
  expect(p.mean).toBeCloseTo(0.8, 4);
  expect(p.sd).toBeLessThan(0.002);
  const r = optimizeWeights([1, 1, 1, 1], 42, (w) => w[0]);
  expect(r.trials).toHaveLength(12);
  expect(r.weights[0]).toBe(1);
});
it("soft rules preserve disagreement; hard rules cannot be rescued", () => {
  const input = {
    positions: defaultPositions(),
    rules: [
      {
        id: "s",
        kind: "sum" as const,
        enabled: true,
        mode: "include" as const,
        values: [0],
      },
    ],
    history,
    candidates: ["00000", "11111"],
  };
  const c = {
    ...defaultInnovation,
    window: 40,
    budget: 2,
    simulations: 100,
    solver: "rank" as const,
    digits: "01",
  };
  const hard = runInnovation(input, c),
    soft = runInnovation(input, { ...c, rules: "soft" });
  expect(hard.numbers).toEqual(["00000"]);
  expect(soft.numbers).toHaveLength(2);
  expect(soft.audit.guard.ok).toBe(true);
});
it("all solvers certify their geometric result and preserve fixed cutoff", () => {
  const input = {
    positions: defaultPositions(),
    rules: [],
    history,
    candidates: ["00000", "00001", "11111", "22222"],
  };
  for (const solver of ["cover", "entropy", "rank", "sample"] as const) {
    const c = {
      ...defaultInnovation,
      solver,
      window: 40,
      referenceIssue: "40",
      budget: 2,
      simulations: 100,
      digits: "01",
      matches: 4,
    };
    const r = runInnovation(input, c);
    expect(r.coverage).toEqual(
      exactCoverage(
        r.numbers,
        Array.from({ length: 32 }, (_, i) => i.toString(2).padStart(5, "0")),
        4,
      ),
    );
    expect(r.numbers.length).toBeLessThanOrEqual(2);
    const extra = { issue: "41", date: "2026-02-10", number: "99999" };
    expect(
      runInnovation({ ...input, history: [...history, extra] }, c),
    ).toEqual(r);
  }
});
it("validates imported configuration and persists scheme options", async () => {
  const { validateInnovation } =
    await import("../src/domain/innovation/config");
  const { encodePlan, decodePlans } = await import("../src/lib/plans");
  expect(() =>
    validateInnovation({ ...defaultInnovation, weights: [0, 0, 0, 0] }),
  ).toThrow();
  expect(() =>
    validateInnovation({ ...defaultInnovation, digits: "001" }),
  ).toThrow();
  expect(() =>
    validateInnovation({ ...defaultInnovation, budget: 100, shortlist: 16 }),
  ).toThrow();
  const input = {
    positions: defaultPositions(),
    rules: [],
    history,
    innovation: { ...defaultInnovation, solver: "entropy" as const },
  };
  const p = encodePlan("覆盖", input);
  expect(
    decodePlans(JSON.stringify({ schemaVersion: 1, plans: [p] }))[0].input
      .innovation,
  ).toEqual(input.innovation);
});
it("hard policy does not inherit an original violation allowance", () => {
  const r = runInnovation(
    {
      positions: defaultPositions(),
      history,
      candidates: ["00000", "11111"],
      rules: [
        { id: "s", kind: "sum", enabled: true, mode: "include", values: [0] },
      ],
      combination: { mode: "violations", minimum: 0, maxViolations: 1 },
    },
    {
      ...defaultInnovation,
      solver: "rank",
      budget: 2,
      window: 40,
      simulations: 100,
    },
  );
  expect(r.numbers).toEqual(["00000"]);
});
it("rank and GP evaluate the same full eligible top-K policy", () => {
  const input = {
    positions: defaultPositions(),
    rules: [],
    history,
    candidates: Array.from({ length: 100 }, (_, i) =>
      String(i).padStart(5, "0"),
    ),
  };
  const c = {
    ...defaultInnovation,
    solver: "rank" as const,
    budget: 16,
    shortlist: 16,
    window: 40,
    simulations: 100,
    rescue: false,
  };
  const r = runInnovation(input, c);
  const expected = [...input.candidates]
    .sort(
      (a, b) =>
        r.trace.scores[Number(b)] - r.trace.scores[Number(a)] ||
        a.localeCompare(b),
    )
    .slice(0, 16);
  expect(r.numbers).toEqual(expected);
});
it("same-budget rescue has a positive independently recounted geometry gain only", () => {
  const input = {
    positions: defaultPositions(),
    rules: [],
    history,
    candidates: Array.from({ length: 32 }, (_, i) =>
      String(i).padStart(5, "0"),
    ),
  };
  const c = {
    ...defaultInnovation,
    solver: "rank" as const,
    window: 40,
    budget: 20,
    weights: [1, 0, 0, 0],
    simulations: 100,
  };
  const before = runInnovation(input, { ...c, rescue: false }),
    after = runInnovation(input, c);
  expect(after.numbers).toHaveLength(before.numbers.length);
  expect(after.risk.exactHit).toBe(before.risk.exactHit);
  expect(after.audit.rescues).toHaveLength(1);
  expect(after.coverage.covered - before.coverage.covered).toBe(
    after.audit.rescues[0].gain,
  );
  expect(after.audit.rescues[0].gain).toBeGreaterThan(0);
});
