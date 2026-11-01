import { it, expect } from "vitest";
import {
  jointForward,
  jointLoss,
  initialJoint,
  fitJoint,
} from "../src/domain/discovery/joint";
import {
  fitGraph,
  graphLoss,
  graphInitial,
  buildGraph,
} from "../src/domain/discovery/graph";
import {
  fitContrast,
  contrastLoss,
  contrastInitial,
} from "../src/domain/discovery/contrast";
import { uncertainty } from "../src/domain/discovery/uncertainty";
it("joint gradients and strict prefix; probability sums to one", () => {
  const w = initialJoint(2),
    a = jointLoss(w, "123", 4);
  for (const i of Array.from({ length: 262 }, (_, i) => i)) {
    const x = w.slice(),
      e = 1e-5;
    x[i] += e;
    const u = jointLoss(x, "123", 4).loss;
    x[i] -= 2 * e;
    expect(a.gradient[i]).toBeCloseTo(
      (u - jointLoss(x, "123", 4).loss) / (2 * e),
      5,
    );
  }
  expect(jointForward(w, "12").probabilities).toHaveLength(10);
  const m = fitJoint(Array(80).fill("12345"), 2);
  let sum = 0;
  for (let i = 0; i < 100000; i++) sum += m.prob(String(i).padStart(5, "0"));
  expect(sum).toBeCloseTo(1, 8);
  expect(m.prob("12345")).toBeGreaterThan(m.prob("99999"));
  expect(m.changed).toBeGreaterThan(0);
});
it("graph trains message parameters and graph respects position identity", () => {
  const rows = Array(80).fill("12345"),
    g = buildGraph(rows),
    w = graphInitial(3),
    a = graphLoss(w, g, "12345", 1);
  for (const i of Array.from({ length: 241 }, (_, i) => i)) {
    const x = w.slice(),
      e = 1e-5;
    x[i] += e;
    const u = graphLoss(x, g, "12345", 1).loss;
    x[i] -= 2 * e;
    expect(a.gradient[i]).toBeCloseTo(
      (u - graphLoss(x, g, "12345", 1).loss) / (2 * e),
      5,
    );
  }
  const m = fitGraph(rows, 3);
  expect(m.score("12345")).not.toBe(m.score("54321"));
  expect(m.changed).toBeGreaterThan(0);
  expect(m.parameters).toBeTruthy();
  expect(
    graphLoss(Float64Array.from(m.parameters), g, "12345", 1).loss,
  ).toBeCloseTo(Math.log(1 + Math.exp(-m.score("12345"))), 12);
});
it("contrastive gradients and non-abnormal task labels", () => {
  const w = contrastInitial(2),
    a = contrastLoss(w, ["12345", "12?45", "67890", "77777"]);
  for (const i of Array.from({ length: 220 }, (_, i) => i)) {
    const x = w.slice(),
      e = 1e-5;
    x[i] += e;
    const u = contrastLoss(x, ["12345", "12?45", "67890", "77777"]).loss;
    x[i] -= 2 * e;
    expect(a.gradient[i]).toBeCloseTo(
      (u - contrastLoss(x, ["12345", "12?45", "67890", "77777"]).loss) /
        (2 * e),
      4,
    );
  }
  const m = fitContrast(
    Array.from({ length: 80 }, (_, i) => String(i % 10).repeat(5)),
    2,
  );
  expect(Number.isFinite(m.score("12345"))).toBe(true);
  expect(m.changed).toBeGreaterThan(0);
});
it("uncertainty abstains on balanced data, reports low with strong evidence", () => {
  const balanced = Array.from({ length: 100 }, (_, i) =>
      String(i % 10).repeat(5),
    ),
    a = uncertainty(balanced, 0.02, 0.05);
  expect(a.cells.every((c) => c.state === "insufficient")).toBe(true);
  expect(a.score("12345")).toBe(0);
  const b = uncertainty(Array(200).fill("00000"), 0.01, 0.05);
  expect(b.cells[0].state).toBe("high");
  expect(b.cells[1].state).toBe("low");
  expect(b.score("00000")).toBeGreaterThan(b.score("11111"));
});
it("integrates four modes with frozen diagnostics and old config compatibility", async () => {
  const { analyzeDiscovery } = await import("../src/domain/discovery/engine");
  const { defaultDiscovery, validateDiscovery } =
    await import("../src/domain/discovery/config");
  const { defaultPositions } = await import("../src/domain/pick5");
  const history = Array.from({ length: 130 }, (_, i) => ({
    issue: String(i + 1),
    date: new Date(Date.UTC(2025, 0, i + 1)).toISOString().slice(0, 10),
    number: String((i * 7919) % 100000).padStart(5, "0"),
  }));
  for (const model of ["joint", "gnn", "contrast", "uncertainty"] as const) {
    const c = {
      ...defaultDiscovery,
      model,
      train: 80,
      validation: 20,
      calibration: 20,
      test: 10,
      pool: 16,
      budget: 3,
    };
    const r = analyzeDiscovery(
      { positions: defaultPositions(), rules: [], history },
      c,
    );
    expect(r.extra).toBeTruthy();
    expect(r.uncertainty.cells).toHaveLength(50);
    expect(r.numbers).toHaveLength(3);
    expect(r.ranges.train.end).toBe("80");
  }
  expect(() =>
    validateDiscovery({ ...defaultDiscovery, model: "joint", train: 201 }),
  ).toThrow();
}, 20000);
it("reports training settings and actual message/encoder parameter updates", () => {
  const g = fitGraph(Array(80).fill("12345"), 1);
  expect(g.settings.epochs).toBe(3);
  expect(g.parameterChanges.message).toBeGreaterThan(0);
  const j = fitJoint(Array(80).fill("12345"), 1);
  expect(j.settings.rate).toBe(0.02);
  expect(j.parameterChanges.attention).toBeGreaterThan(0);
  const c = fitContrast(["12345", "67890", "23456"], 1);
  expect(c.settings.temperature).toBe(0.2);
  expect(c.parameterChanges.encoder).toBeGreaterThan(0);
});
