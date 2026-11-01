import { expect, it } from "vitest";
import {
  defaultRelation,
  prepareRelation,
  inspectRelations,
  type RelationConfig,
} from "../src/domain/relations";
import { filter, defaultPositions, type Rule } from "../src/domain/pick5";
import { backtest } from "../src/domain/backtest";
import { encodePlan, decodePlans } from "../src/lib/plans";
const rows = [
  "10000",
  "20000",
  "10000",
  "20000",
  "10000",
  "20000",
  "10000",
  "20000",
].map((number, i) => ({
  issue: String(i + 1),
  date: `2026-01-0${i + 1}`,
  number,
}));
const c = (p: Partial<RelationConfig> = {}) => ({ ...defaultRelation, ...p });
it("scores lagged repeat, non-wrapping neighbors, both mirrors and cross-position transfers", () => {
  expect(prepareRelation(c({ lag: 2 }), rows).score("10000")).toBe(1);
  expect(prepareRelation(c({ lag: 2 }), rows).score("20000")).toBe(0);
  expect(prepareRelation(c({ method: "neighbor" }), rows).score("30000")).toBe(
    1,
  );
  expect(prepareRelation(c({ method: "neighbor" }), rows).score("20000")).toBe(
    0,
  );
  const zero = [{ issue: "0", date: "2026-01-01", number: "00000" }];
  expect(prepareRelation(c({ method: "neighbor" }), zero).score("90000")).toBe(
    0,
  );
  expect(
    prepareRelation(c({ method: "mirror", mirror: "nine" }), rows).score(
      "70000",
    ),
  ).toBe(1);
  expect(
    prepareRelation(c({ method: "mirror", mirror: "five" }), rows).score(
      "70000",
    ),
  ).toBe(1);
  expect(
    prepareRelation(c({ method: "repeat", previousPosition: 1 }), rows).score(
      "00000",
    ),
  ).toBe(1);
});
it("counts inheritance over multiple periods and directional indicator differences", () => {
  expect(
    prepareRelation(c({ method: "inherit", depth: 4 }), rows).score("10000"),
  ).toBe(2);
  expect(
    prepareRelation(
      c({ method: "inherit", scope: "positions", depth: 4 }),
      rows,
    ).score("30000"),
  ).toBe(4);
  expect(
    prepareRelation(
      c({ method: "delta", metric: "sum", min: -45, max: 45 }),
      rows,
    ).score("00000"),
  ).toBe(-2);
});
it("learns only observed historical scores and respects the cutoff", () => {
  const config = c({
    strategy: "historical",
    window: 4,
    lag: 2,
    minSupport: 1,
    referenceIssue: "6",
  });
  const fitted = prepareRelation(config, rows);
  expect(fitted.test("10000")).toBe(true);
  expect(fitted.test("20000")).toBe(false);
  const changed = [
    ...rows.slice(0, 6),
    { ...rows[6], number: "99999" },
    { ...rows[7], number: "99999" },
  ];
  expect(prepareRelation(config, changed).diagnostics).toEqual(
    fitted.diagnostics,
  );
  expect(() =>
    prepareRelation({ ...config, referenceIssue: "4" }, rows),
  ).toThrow(/不足/);
});
it("shows repeat intervals and streaks using full cutoff history rather than the display window", () => {
  const report = inspectRelations(rows, c({ window: 3 }), 3);
  expect(report.rows.map((r) => r.value)).toEqual([2, 1, 2]);
  expect(report.rows.at(-1)?.repeatGap).toBe(2);
  expect(report.rows.at(-1)?.streak).toBe(1);
  const lag2 = report.lags.find((r) => r.lag === 2)!;
  expect(lag2.repeat).toBe(lag2.samples);
});
it("integrates filtering, exclude, snapshots and rolling replay", () => {
  const rule: Rule = {
    id: "r",
    kind: "relation",
    values: [],
    enabled: true,
    mode: "include",
    relation: c({ lag: 2 }),
  };
  const input = {
    positions: defaultPositions(),
    candidates: ["10000", "20000"],
    rules: [rule],
    history: rows,
  };
  expect(filter(input).numbers).toEqual(["10000"]);
  expect(
    filter({ ...input, rules: [{ ...rule, mode: "exclude" }] }).numbers,
  ).toEqual(["20000"]);
  const plan = encodePlan("周期", input);
  expect(
    decodePlans(JSON.stringify({ schemaVersion: 1, plans: [plan] }))[0].input,
  ).toEqual(input);
  expect(
    backtest(
      {
        ...input,
        candidates: undefined,
        rules: [{ ...rule, relation: c({ lag: 2, referenceIssue: "8" }) }],
      },
      8,
    ).map((r) => r.status),
  ).toEqual(["insufficient", "insufficient", ...Array(6).fill("retained")]);
});
it("distinguishes mirror definitions, observed zero-support states, and malformed plans", () => {
  const one = [{ issue: "1", date: "2026-01-01", number: "10000" }];
  expect(
    prepareRelation(c({ method: "mirror", mirror: "nine" }), one).score(
      "80000",
    ),
  ).toBe(1);
  expect(
    prepareRelation(c({ method: "mirror", mirror: "five" }), one).score(
      "80000",
    ),
  ).toBe(0);
  expect(
    prepareRelation(c({ method: "mirror", mirror: "five" }), one).score(
      "60000",
    ),
  ).toBe(1);
  const fitted = prepareRelation(
    c({ strategy: "historical", window: 4, lag: 2, minSupport: 0 }),
    rows,
  );
  expect(fitted.test("20000")).toBe(false);
  expect(() => prepareRelation(c({ lag: 0 }), rows)).toThrow();
  expect(() =>
    prepareRelation(c({ method: "mirror", metric: "sum" }), rows),
  ).toThrow();
  const rule: Rule = {
    id: "r",
    kind: "relation",
    values: [],
    enabled: true,
    mode: "include",
    relation: c(),
  };
  const plan = encodePlan("边界", {
    positions: defaultPositions(),
    rules: [rule],
    history: rows,
  });
  plan.input.rules[0].relation!.minSupport = NaN;
  expect(() =>
    decodePlans(JSON.stringify({ schemaVersion: 1, plans: [plan] })),
  ).toThrow();
});
it("honors tolerant groups and preserves the leading zero in cross-position inheritance", () => {
  const rule: Rule = {
    id: "r",
    kind: "relation",
    values: [],
    enabled: true,
    mode: "include",
    group: "repeat",
    relation: c({ lag: 2 }),
  };
  const neighbor: Rule = {
    ...rule,
    id: "n",
    group: "neighbor",
    relation: c({ method: "neighbor" }),
  };
  const input = {
    positions: defaultPositions(),
    candidates: ["00000", "10000", "30000"],
    rules: [rule, neighbor],
    history: rows,
    combination: { mode: "atLeast" as const, minimum: 1 },
  };
  expect(filter(input).numbers).toEqual(["10000", "30000"]);
  expect(
    prepareRelation(
      c({ method: "inherit", depth: 4, previousPosition: 1 }),
      rows,
    ).score("00000"),
  ).toBe(4);
});
