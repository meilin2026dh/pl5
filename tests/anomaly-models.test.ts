import { it, expect } from "vitest";
import {
  fitIsolation,
  pathCorrection,
} from "../src/domain/discovery/isolation";
import {
  aeInitial,
  aeLoss,
  fitAutoencoder,
} from "../src/domain/discovery/autoencoder";
import { fitMaxent } from "../src/domain/discovery/maxent";
import { haarPacket, fitWavelet } from "../src/domain/discovery/wavelet";
import {
  fitCopula,
  normalCDF,
  normalQuantile,
} from "../src/domain/discovery/copula";
it("isolation handles leaves, constant data and seeded forest", () => {
  expect(pathCorrection(2)).toBe(1);
  expect(pathCorrection(1)).toBe(0);
  const rows = [
    ...Array.from({ length: 63 }, (_, i) => String(i % 3).repeat(5)),
    "99999",
  ];
  const m = fitIsolation(rows, 7);
  expect(m.anomaly("99999")).toBeGreaterThan(m.anomaly("11111"));
  expect(m.score("12345")).toBe(fitIsolation(rows, 7).score("12345"));
  expect(fitIsolation(Array(80).fill("00000"), 1).anomaly("99999")).toBeCloseTo(
    0.5,
    10,
  );
});
it("autoencoder full gradients and actual reconstruction learning", () => {
  const w = aeInitial(2),
    a = aeLoss(w, "12345", 2);
  for (let i = 0; i < w.length; i++) {
    const x = w.slice(),
      e = 1e-5;
    x[i] += e;
    const u = aeLoss(x, "12345", 2).loss;
    x[i] -= 2 * e;
    expect(a.gradient[i]).toBeCloseTo(
      (u - aeLoss(x, "12345", 2).loss) / (2 * e),
      5,
    );
  }
  const m = fitAutoencoder(Array(80).fill("12345"), 2);
  expect(m.score("12345")).toBeGreaterThan(m.score("99999"));
  expect(m.parameterChanges.encoder).toBeGreaterThan(0);
  expect(m.parameterChanges.decoder).toBeGreaterThan(0);
});
it("maxent normalizes and learns sufficient statistics with exact partition", () => {
  const m = fitMaxent(Array(80).fill("12345"));
  let sum = 0;
  for (let i = 0; i < 100000; i++) sum += m.prob(String(i).padStart(5, "0"));
  expect(sum).toBeCloseTo(1, 9);
  expect(m.prob("12345")).toBeGreaterThan(m.prob("99999"));
  expect(m.trace.at(-1)!).toBeLessThan(m.trace[0]);
});
it("wavelet packet conserves energy and freezes history context", () => {
  const x = Array.from({ length: 16 }, (_, i) => i - 7);
  expect(
    haarPacket(x).reduce((s, r) => s + r.reduce((a, v) => a + v * v, 0), 0),
  ).toBeCloseTo(
    x.reduce((s, v) => s + v * v, 0),
    10,
  );
  const m = fitWavelet(
    Array.from({ length: 80 }, (_, i) => String(i % 10).repeat(5)),
  );
  expect(Number.isFinite(m.score("12345"))).toBe(true);
  expect(m.context).toHaveLength(15);
  expect(m.penalties).toHaveLength(5);
});
it("copula gives a seeded positive discrete mass and shrunk covariance", () => {
  expect(normalCDF(0)).toBeCloseTo(0.5, 6);
  expect(normalQuantile(0.975)).toBeCloseTo(1.95996, 4);
  const m = fitCopula(
    Array.from({ length: 80 }, (_, i) => String(i % 10).repeat(5)),
    7,
  );
  let sum = 0;
  for (let i = 0; i < 100000; i++) sum += m.prob(String(i).padStart(5, "0"));
  expect(sum).toBeCloseTo(1, 9);
  expect(m.correlation[0][1]).toBeCloseTo(0.5, 10);
  expect(m.histogram.reduce((a, b) => a + b, 0)).toBe(250000);
  expect(m.prob("00000")).toBeGreaterThan(0);
  expect(
    fitCopula(
      Array.from({ length: 80 }, (_, i) => String(i % 10).repeat(5)),
      7,
    ).histogram,
  ).toEqual(m.histogram);
});
it("integrates all five modes with chronological fitting and budget guards", async () => {
  const { analyzeDiscovery } = await import("../src/domain/discovery/engine");
  const { defaultDiscovery, validateDiscovery } =
    await import("../src/domain/discovery/config");
  const { defaultPositions } = await import("../src/domain/pick5");
  const history = Array.from({ length: 130 }, (_, i) => ({
    issue: String(i + 1),
    date: new Date(Date.UTC(2025, 0, i + 1)).toISOString().slice(0, 10),
    number: String((i * 7919) % 100000).padStart(5, "0"),
  }));
  for (const model of [
    "isolation",
    "autoencoder",
    "maxent",
    "wavelet",
    "copula",
  ] as const) {
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
    expect(r.numbers).toHaveLength(3);
    expect(r.ranges.train.end).toBe("80");
    expect(r.subsetGuarantee).toBe(false);
    const altered = analyzeDiscovery(
      {
        positions: defaultPositions(),
        rules: [],
        history: history.map((r, i) =>
          i >= 120 ? { ...r, number: "99999" } : r,
        ),
      },
      c,
    );
    expect(altered.modelDigest).toBe(r.modelDigest);
    expect(altered.numbers).toEqual(r.numbers);
  }
  expect(() =>
    validateDiscovery({
      ...defaultDiscovery,
      model: "autoencoder",
      train: 201,
    }),
  ).toThrow();
}, 20000);
