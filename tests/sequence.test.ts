import { it, expect } from "vitest";
import {
  initialSequence,
  sequenceLoss,
  sequencePredict,
  fitSequence,
} from "../src/domain/selection/sequence";
for (const kind of ["lstm", "transformer"] as const) {
  it(
    kind +
      " differentiates every parameter against independent finite differences",
    () => {
      const w = initialSequence(kind, 7),
        x = [1, 2, 3, 1],
        r = sequenceLoss(kind, w, x, 4);
      expect(r.probabilities.reduce((a, b) => a + b, 0)).toBeCloseTo(1, 12);
      for (let i = 0; i < w.length; i++) {
        const d = 1e-5,
          a = w.slice(),
          b = w.slice();
        a[i] += d;
        b[i] -= d;
        const numeric =
          (sequenceLoss(kind, a, x, 4).loss -
            sequenceLoss(kind, b, x, 4).loss) /
          (2 * d);
        expect(r.gradient[i]).toBeCloseTo(numeric, 4);
      }
    },
  );
  it(
    kind +
      " trains all layers on a controlled sequence with deterministic replay",
    () => {
      const rows = Array.from({ length: 80 }, (_, i) => ({
        issue: String(i + 1),
        date: new Date(Date.UTC(2025, 0, i + 1)).toISOString().slice(0, 10),
        number: "22222",
      }));
      const a = fitSequence(rows, kind, 10, { context: 4, epochs: 2 }),
        b = fitSequence(rows, kind, 10, { context: 4, epochs: 2 });
      expect(a.probabilities).toEqual(b.probabilities);
      expect(a.probabilities.every((p) => p[2] > 0.1)).toBe(true);
      expect(a.diagnostics.bestEpoch).toBeGreaterThan(0);
      expect(
        a.diagnostics.mixture.comparisons.find((x) => x.weight === 0)?.loss,
      ).toBeCloseTo(Math.log(10), 10);
      expect(
        a.diagnostics.mixture.comparisons.find((x) => x.weight === 0.5)?.loss,
      ).toBeGreaterThan(0);
      expect(a.diagnostics.changed.embedding).toBeGreaterThan(0);
      expect(a.diagnostics.changed.body).toBeGreaterThan(0);
      expect(a.diagnostics.changed.head).toBeGreaterThan(0);
      const changed = rows.map((r, i) =>
          i >= 64 ? { ...r, number: "99999" } : r,
        ),
        c = fitSequence(changed, kind, 10, { context: 4, epochs: 2 });
      expect(a.diagnostics.bestEpoch).toBe(c.diagnostics.bestEpoch);
      expect(a.diagnostics.validationLoss).toBe(c.diagnostics.validationLoss);
    },
  );
}
it("attention never reads later tokens when computing an earlier token", () => {
  const w = initialSequence("transformer", 3);
  const a = sequencePredict("transformer", w, [1, 2, 3, 4]),
    b = sequencePredict("transformer", w, [1, 2, 9, 9]);
  expect(a.tokenStates.slice(0, 2)).toEqual(b.tokenStates.slice(0, 2));
  expect(a.attention[0].slice(1)).toEqual([0, 0, 0]);
});
