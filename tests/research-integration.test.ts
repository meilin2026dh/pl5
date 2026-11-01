import { it, expect } from "vitest";
import {
  filter,
  defaultPositions,
  type FilterInput,
  type Rule,
} from "../src/domain/pick5";
import { defaultResearch } from "../src/domain/research/types";
import { backtest } from "../src/domain/backtest";
import { encodePlan, decodePlans } from "../src/lib/plans";
const history = Array.from({ length: 20 }, (_, i) => ({
  issue: String(i + 1),
  date: new Date(Date.UTC(2026, 0, i + 1)).toISOString().slice(0, 10),
  number: String(i % 10).repeat(5),
}));
const rule: Rule = {
  id: "r",
  kind: "research",
  enabled: true,
  mode: "include",
  values: [],
  research: { ...defaultResearch, window: 10, method: "hotcold", parameter: 1 },
};
const input: FilterInput = {
  positions: defaultPositions(),
  rules: [rule],
  history,
  candidates: ["00000", "11111"],
};
it("integrates experiment predicates and serializable diagnostics", () => {
  const r = filter(input);
  expect(r.numbers).toEqual(["00000"]);
  expect(r.research?.[0].diagnostics).toBeTruthy();
  expect(
    filter({ ...input, rules: [{ ...rule, mode: "exclude" }] }).numbers,
  ).toEqual(["11111"]);
});
it("keeps whole-universe ranking independent of external candidate count", () => {
  const r = {
    ...rule,
    research: {
      ...defaultResearch,
      window: 10,
      method: "heatScore" as const,
      retain: 0.01,
      ties: "inclusive" as const,
    },
  };
  const result = filter({ ...input, rules: [r] });
  expect(result.numbers).toEqual(["00000", "11111"]);
  expect(result.research?.[0].diagnostics.actualCount).toBe(100000);
});
it("roundtrips complete experiment settings", () => {
  const plan = encodePlan("实验", {
    ...input,
    rules: [
      { ...rule, research: { ...rule.research!, seed: 42, ties: "seeded" } },
    ],
  });
  expect(
    decodePlans(JSON.stringify({ schemaVersion: 1, plans: [plan] }))[0].input,
  ).toEqual(plan.input);
});
it("overrides frozen references with strictly preceding records in replay", () => {
  const result = backtest(
    {
      ...input,
      candidates: undefined,
      rules: [
        {
          ...rule,
          research: { ...rule.research!, referenceIssue: "20", window: 2 },
        },
      ],
    },
    3,
  );
  expect(result.map((r) => r.referenceIssue)).toEqual(["17", "18", "19"]);
  expect(result.some((r) => r.status === "error")).toBe(false);
});
it("replays non-uniform seeded rankings against all 100000 numbers without future training", () => {
  const rows = history
    .slice(0, 7)
    .map((r, i) => ({ ...r, number: i < 4 ? "00000" : "99999" }));
  const r: Rule = {
    ...rule,
    research: {
      ...defaultResearch,
      method: "heatScore",
      window: 3,
      referenceIssue: "7",
      retain: 0.00001,
      ties: "seeded",
      seed: 42,
    },
  };
  const i: FilterInput = {
    ...input,
    history: rows,
    candidates: ["99999"],
    rules: [r],
  };
  expect(filter(i).numbers).toEqual(["99999"]);
  const replay = backtest(i, 3);
  expect(replay[0]).toMatchObject({
    issue: "5",
    referenceIssue: "4",
    status: "removed",
  });
  expect(replay[2]).toMatchObject({
    issue: "7",
    referenceIssue: "6",
    status: "retained",
  });
});
