import { it, expect } from "vitest";
import { filter, defaultPositions, type Rule } from "../src/domain/pick5";
import { defaultResearch } from "../src/domain/research/types";
import { differenceSignature } from "../src/domain/research/difference";
import { phi, analyzeConditions } from "../src/domain/audit/engine";
import { defaultAudit } from "../src/domain/audit/config";
const rows = Array.from({ length: 60 }, (_, i) => ({
  issue: String(i + 1),
  date: new Date(Date.UTC(2026, 0, i + 1)).toISOString().slice(0, 10),
  number: i % 2 ? "23456" : "12345",
}));
const rule = (
  id: string,
  kind: Rule["kind"],
  values: Rule["values"],
): Rule => ({ id, kind, values, enabled: true, mode: "include" });
it("uses signed adjacent differences and only observed translation classes", () => {
  expect(differenceSignature("25973")).toBe("3,4,-2,-4");
  expect(differenceSignature("12345")).toBe(differenceSignature("23456"));
  expect(differenceSignature("67890")).not.toBe(differenceSignature("12345"));
  const r: Rule = {
    ...rule("d", "research", []),
    research: {
      ...defaultResearch,
      method: "difference",
      window: 40,
      parameter: 1,
    },
  };
  expect(
    filter({
      positions: defaultPositions(),
      candidates: ["12345", "23456", "67890"],
      history: rows,
      rules: [r],
    }).numbers,
  ).toEqual(["12345", "23456"]);
});
it("allows a per-rule violation budget independent of group labels", () => {
  const rules = [
    { ...rule("s", "sum", [15]), group: "same" },
    { ...rule("m", "max", [4]), group: "same" },
    rule("o", "odd", [3]),
  ];
  expect(
    filter({
      positions: defaultPositions(),
      candidates: ["12345"],
      rules,
      combination: { mode: "violations", minimum: 0, maxViolations: 1 },
    }).numbers,
  ).toEqual(["12345"]);
  expect(
    filter({
      positions: defaultPositions(),
      candidates: ["12345"],
      rules,
      combination: { mode: "violations", minimum: 0, maxViolations: 0 },
    }).numbers,
  ).toEqual([]);
});
it("computes binary phi without claiming constants have defined correlation", () => {
  expect(
    phi(Uint8Array.from([1, 1, 0, 0]), Uint8Array.from([1, 1, 0, 0])),
  ).toBe(1);
  expect(
    phi(Uint8Array.from([1, 1, 0, 0]), Uint8Array.from([0, 0, 1, 1])),
  ).toBe(-1);
  expect(phi(Uint8Array.from([1, 1]), Uint8Array.from([0, 1]))).toBeNull();
});
it("deduplicates equivalent masks and plans to an explicit number ceiling", () => {
  const input = {
    positions: defaultPositions(),
    history: rows,
    rules: [
      rule("a", "sum", [15]),
      rule("b", "sum", [15]),
      rule("c", "odd", [3]),
    ],
  };
  const r = analyzeConditions(
    input,
    { ...defaultAudit, pool: "current", training: 40, target: 10000 },
    false,
  );
  expect(r.analysis.redundant.some((v) => v.id === "b")).toBe(true);
  expect(r.analysis.remaining).toBeLessThanOrEqual(10000);
  expect(r.analysis.remaining).toBeGreaterThan(0);
});
it("freezes each forward fold and reports the actual training and validation periods", () => {
  const r = analyzeConditions(
    {
      positions: defaultPositions(),
      history: rows,
      rules: [rule("a", "sum", [15])],
    },
    {
      ...defaultAudit,
      pool: "current",
      training: 40,
      folds: 2,
      validation: 10,
      target: 10000,
    },
    true,
  );
  expect(r.folds).toHaveLength(2);
  expect(r.folds![0]).toMatchObject({
    trainingEnd: "40",
    validationStart: "41",
    validationEnd: "50",
  });
  expect(r.folds![1]).toMatchObject({
    trainingEnd: "50",
    validationStart: "51",
    validationEnd: "60",
  });
});
it("has exactly 40951 signed difference classes over the full space", () => {
  const signatures = new Set(
    Array.from({ length: 100000 }, (_, i) =>
      differenceSignature(String(i).padStart(5, "0")),
    ),
  );
  expect(signatures.size).toBe(40951);
});
it("does not select a condition that empties the source pool", () => {
  const r = analyzeConditions(
    {
      positions: defaultPositions(),
      history: rows,
      candidates: ["12345"],
      rules: [rule("empty", "sum", [0])],
    },
    { ...defaultAudit, pool: "current", training: 40, target: 1 },
    false,
  );
  expect(r.analysis.remaining).toBe(1);
  expect(r.analysis.selectedRules).toEqual([]);
});
it("rejects an empty source instead of reporting NaN compression or a successful empty plan", () => {
  expect(() =>
    analyzeConditions(
      {
        positions: defaultPositions(),
        history: rows,
        candidates: [],
        rules: [rule("a", "sum", [15])],
      },
      {
        ...defaultAudit,
        pool: "current",
        training: 40,
        validation: 10,
        folds: 2,
      },
      true,
    ),
  ).toThrow(/外部号码/);
});

it("applies historical conditions with the identical bounded training snapshot", () => {
  const history = rows.map((r, i) => ({
    ...r,
    number: String(i).padStart(5, "0"),
  }));
  const input = {
    positions: defaultPositions(),
    history,
    rules: [rule("history", "historyExclude", [])],
  };
  const result = analyzeConditions(
    input,
    { ...defaultAudit, pool: "current", training: 40, target: 99960 },
    false,
  );
  expect(result.analysis.remaining).toBe(99960);
  expect(
    filter({ ...input, rules: result.analysis.selectedRules }).numbers,
  ).toHaveLength(result.analysis.remaining);
});
