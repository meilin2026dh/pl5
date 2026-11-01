import { it, expect } from "vitest";
import { analyzeLab } from "../src/domain/lab/engine";
import { defaultLab } from "../src/domain/lab/config";
import { methods } from "../src/domain/lab/registry";
import {
  selectPortfolio,
  replaySelection,
} from "../src/domain/selection/engine";
import { defaultSelection } from "../src/domain/selection/config";
import { defaultPositions, validateInput } from "../src/domain/pick5";
const history = Array.from({ length: 100 }, (_, i) => ({
  issue: String(i + 1),
  date: new Date(Date.UTC(2025, 0, i + 1)).toISOString().slice(0, 10),
  number: "22222",
}));
const input = {
  positions: defaultPositions(),
  rules: [],
  history,
  historySource: "fixture",
  candidates: ["00000", "22222"],
};
it("integrates real sequence scorers with selection and rejects excessive replay work", () => {
  for (const scorer of ["lstm", "transformer"] as const) {
    const c = {
      ...defaultSelection,
      scorer,
      window: 80,
      budget: 1,
      recent: 0,
      minLarge: 0,
      acMin: -4,
      sequence: { context: 4 as const, epochs: 1 },
    };
    const r = selectPortfolio(input, c);
    expect(r.numbers).toEqual(["22222"]);
    expect(r.diagnostics.scorer.parameters).toBeGreaterThan(1000);
    expect(() => replaySelection(input, { ...c, window: 300 })).toThrow(/回放/);
  }
});
it("respects cutoff, validates new configs and constrains explicit cover candidates to source", () => {
  const c = {
    ...defaultLab,
    window: 80,
    referenceIssue: "90",
    candidatesText: "00000 22222",
    targetsText: "00000 22222",
    cover: { ...defaultLab.cover, radius: 0, budget: 2 },
  };
  const a = analyzeLab(input, c, "posterior");
  expect(a.posterior?.used).toBe(90);
  const b = analyzeLab(
    { ...input, history: history.slice(0, 90) },
    c,
    "posterior",
  );
  expect(a.posterior).toEqual(b.posterior);
  const r = analyzeLab(input, c, "cover");
  expect(r.cover?.status).toBe("OPTIMAL");
  expect(r.cover?.numbers).toHaveLength(2);
  expect(() =>
    analyzeLab(input, { ...c, candidatesText: "99999" }, "cover"),
  ).toThrow(/来源/);
  expect(() =>
    validateInput({ ...input, lab: { ...c, shortlist: 33 } }),
  ).toThrow();
});
it("declares selectors separately from predictive distributions", () => {
  expect(new Set(methods.map((m) => m.id)).size).toBe(methods.length);
  expect(methods.find((m) => m.id === "mcga")?.type).toBe("selector");
  expect(methods.find((m) => m.id === "transformer")?.conformal).toBe(false);
});
