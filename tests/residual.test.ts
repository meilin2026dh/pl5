import { it, expect } from "vitest";
import {
  residualLoss,
  initialResidual,
  fitResidual,
} from "../src/domain/selection/residual";
it("backpropagates through causal convolutions and the residual skip", () => {
  const w = initialResidual(42),
    context = [0, 1, 2, 3, 4, 5, 6, 7],
    a = residualLoss(w, context, 8);
  for (const i of [0, 40, 44, 92, 96, 144, 148, 188]) {
    const eps = 1e-5,
      p = new Float64Array(w),
      m = new Float64Array(w);
    p[i] += eps;
    m[i] -= eps;
    const numerical =
      (residualLoss(p, context, 8).loss - residualLoss(m, context, 8).loss) /
      (2 * eps);
    expect(a.gradient[i]).toBeCloseTo(numerical, 5);
  }
});
it("trains a reproducible tiny residual model and reports held-out next-digit loss", () => {
  const rows = Array.from({ length: 40 }, (_, i) => ({
    issue: String(i + 1),
    date: new Date(Date.UTC(2026, 0, i + 1)).toISOString().slice(0, 10),
    number: i % 2 ? "11111" : "00000",
  }));
  const a = fitResidual(rows, 42),
    b = fitResidual(rows, 42);
  expect(a.probabilities).toEqual(b.probabilities);
  for (const p of a.probabilities)
    expect(p.reduce((s, n) => s + n, 0)).toBeCloseTo(1, 10);
  expect(a.diagnostics).toMatchObject({
    parameters: 990,
    context: 8,
    trainingEnd: "40",
    validationStart: "34",
    validationEnd: "40",
  });
});
