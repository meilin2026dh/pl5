import { it, expect } from "vitest";
import {
  inspectQuality,
  monteCarloP,
  holm,
  changeStatistic,
  uniformMartingale,
  randomizationP,
  frequencyStatistic,
  serialStatistic,
} from "../src/domain/evidence/statistics";
import { analyzeEvidence } from "../src/domain/evidence/engine";
import { defaultEvidence } from "../src/domain/evidence/config";
import { defaultPositions } from "../src/domain/pick5";
const rows = Array.from({ length: 180 }, (_, i) => ({
  issue: String(i + 1),
  date: new Date(Date.UTC(2025, 0, i + 1)).toISOString().slice(0, 10),
  number: "00000",
}));
it("blocks invalid dates/duplicates and does not equate gaps with missing draws", () => {
  expect(inspectQuality([rows[0], rows[0]]).errors).toHaveLength(2);
  expect(
    inspectQuality([{ ...rows[0], date: "2026-02-30" }]).errors.length,
  ).toBeGreaterThan(0);
  expect(inspectQuality([rows[0], rows[2]])).toMatchObject({
    gaps: 1,
    errors: [],
  });
});
it("uses nonzero randomization p values and Holm family adjustment", () => {
  expect(monteCarloP(2, [0, 1])).toBeCloseTo(1 / 3);
  expect(holm([0.01, 0.04, 0.03])).toEqual([0.03, 0.06, 0.06]);
});
it("finds a distribution break and keeps constant sequence permutation p=1", () => {
  expect(
    changeStatistic(
      Array.from({ length: 80 }, (_, i) => Array(5).fill(i < 40 ? 0 : 9)),
    ).cut,
  ).toBe(40);
  expect(
    randomizationP(
      Array.from({ length: 40 }, () => [0, 0, 0, 0, 0]),
      serialStatistic,
      99,
      1,
    ).p,
  ).toBe(1);
  expect(
    randomizationP(
      Array.from({ length: 40 }, () => [0, 0, 0, 0, 0]),
      frequencyStatistic,
      99,
      1,
      true,
    ).p,
  ).toBe(0.01);
});
it("betting evidence is prequential and stable under prefix extension", () => {
  const a = uniformMartingale(rows.slice(0, 40)),
    b = uniformMartingale(rows);
  expect(b.trace.slice(0, 40)).toEqual(a.trace);
  expect(a.anytimeP).toBeLessThan(0.001);
});
it("keeps tuning, calibration and test disjoint and respects cutoff", () => {
  const c = {
    ...defaultEvidence,
    window: 40,
    monitor: 40,
    tune: 20,
    calibration: 20,
    test: 60,
    checks: 1,
    resamples: 99,
    budget: 3,
    referenceIssue: "160",
  };
  const input = { positions: defaultPositions(), rules: [], history: rows };
  const r = analyzeEvidence(input, c);
  expect(r.validation?.ranges).toMatchObject({
    tune: ["61", "80"],
    calibration: ["81", "100"],
    test: ["101", "160"],
  });
  const { quality: _quality, ...frozen } = r;
  const { quality: _other, ...prefix } = analyzeEvidence(
    { ...input, history: rows.slice(0, 160) },
    c,
  );
  expect(frozen).toEqual(prefix);
  expect(r.portfolio?.exactProbability).toBe(
    (r.portfolio?.numbers.length ?? 0) / 100000,
  );
});
it("rejects poor data before any scoring and produces finite model probabilities", async () => {
  const { probabilities, scoreProbabilities } =
    await import("../src/domain/evidence/models");
  const r = analyzeEvidence(
    { positions: defaultPositions(), rules: [], history: [rows[0], rows[0]] },
    defaultEvidence,
  );
  expect(r.blocked).toBe(true);
  for (const kind of ["uniform", "iid", "markov"] as const) {
    for (const p of probabilities(rows.slice(0, 40), {
      kind,
      window: 40,
      alpha: 1,
    })) {
      expect(p.reduce((a, b) => a + b, 0)).toBeCloseTo(1, 12);
      expect(p.every((v) => v > 0)).toBe(true);
    }
  }
  expect(
    scoreProbabilities(
      Array.from({ length: 5 }, () => Array(10).fill(0.1)),
      "01234",
    ).logLoss,
  ).toBeCloseTo(Math.log(10), 12);
  expect(
    scoreProbabilities(
      Array.from({ length: 5 }, () => Array(10).fill(0.1)),
      "01234",
    ).brier,
  ).toBeCloseTo(0.9);
});
it("can pass predeclared evidence gates on a clearly nonrandom controlled process", () => {
  const history = Array.from({ length: 700 }, (_, i) => ({
    issue: String(i + 1),
    date: new Date(Date.UTC(2023, 0, i + 1)).toISOString().slice(0, 10),
    number: i % 2 ? "11111" : "00000",
  }));
  const c = {
    ...defaultEvidence,
    window: 500,
    monitor: 100,
    tune: 20,
    calibration: 20,
    test: 60,
    checks: 1,
    resamples: 99,
    budget: 3,
  };
  const r = analyzeEvidence(
    { positions: defaultPositions(), rules: [], history },
    c,
  );
  expect(r.recommendation?.useBias).toBe(true);
  expect(r.validation?.model.kind).toBe("markov");
  expect(r.validation?.gain.low).toBeGreaterThan(0);
  expect(r.checks?.find((t) => t.label === "逐位均匀频率")?.p).toBe(0.01);
  expect(r.portfolio?.exactProbability).toBe(3 / 100000);
});
it("calibration and time-out answers cannot influence prior model selection", async () => {
  const { temporalValidation } = await import("../src/domain/evidence/engine");
  const c = {
    ...defaultEvidence,
    window: 40,
    tune: 20,
    calibration: 20,
    test: 60,
  };
  const a = temporalValidation(rows, c),
    edited = rows.map((r, i) => (i >= 120 ? { ...r, number: "99999" } : r)),
    b = temporalValidation(edited, c);
  expect(a.model).toEqual(b.model);
  expect(a.calibration).toEqual(b.calibration);
  expect(a.metrics).not.toEqual(b.metrics);
  expect(a.ranges.tune[1]).toBe("100");
  expect(a.ranges.calibration[1]).toBe("120");
});
it("has an exact zero uniform score advantage within numerical tolerance", async () => {
  const { evaluate, improvement } =
    await import("../src/domain/evidence/models");
  const r = improvement(
    evaluate(rows, 40, 100, { kind: "uniform", window: 40, alpha: 1 }),
  );
  expect(r).toEqual({
    mean: 0,
    low: 0,
    high: 0,
    maxSingleShare: 0,
    leaveOneWorst: 0,
  });
});
it("repeat-structure null probabilities match an independent full enumeration", async () => {
  const { repeatStatistic } = await import("../src/domain/evidence/statistics");
  const full = Array.from({ length: 100000 }, (_, i) =>
    [...String(i).padStart(5, "0")].map(Number),
  );
  expect(repeatStatistic(full)).toBeCloseTo(0, 12);
});
