import { expect, it } from "vitest";
import { filter, defaultPositions, type Rule } from "../src/domain/pick5";
const check = (
  kind: Rule["kind"],
  values: Rule["values"],
  params?: Rule["params"],
) =>
  filter({
    positions: defaultPositions(),
    candidates: ["12345"],
    rules: [{ id: kind, kind, values, params, enabled: true, mode: "include" }],
  }).numbers;
it("advanced scalar, pattern and pair predicates", () => {
  expect(check("median", [3])).toEqual(["12345"]);
  expect(check("oddPattern", ["10101"])).toEqual(["12345"]);
  expect(check("pairProductTail", [2], { positions: [0, 1] })).toEqual([
    "12345",
  ]);
});
it("external candidates and tolerant groups", () => {
  expect(
    filter({
      positions: defaultPositions(),
      candidates: ["12345", "12345", "00000"],
      rules: [],
      combination: { mode: "atLeast", minimum: 0 },
    }).numbers,
  ).toEqual(["00000", "12345"]);
});
const cases: [Rule["kind"], Rule["values"], Rule["params"]?][] = [
  [
    "danGroups",
    [],
    {
      groups: [
        [1, 2],
        [4, 5],
      ],
      counts: [2, 2],
    },
  ],
  ["bigPattern", ["00001"]],
  ["primePattern", ["11101"]],
  ["routeCounts", ["1:2:2"]],
  ["routePattern", ["12012"]],
  ["positionDiff", [4], { positions: [0, 4] }],
  ["positionTrend", ["up"], { positions: [0, 1] }],
  ["max", [5]],
  ["min", [1]],
  ["mean", [3]],
  ["pairSum", [3], { positions: [0, 1] }],
  ["pairDiff", [1], { positions: [0, 1] }],
  ["pairTail", [3], { positions: [0, 1] }],
  ["classSum", [9], { class: "odd" }],
  ["remainderSum", [6], { modulus: 3 }],
  [
    "partition",
    [],
    {
      partitions: [
        [0, 1, 2, 3, 4],
        [5, 6, 7, 8, 9],
      ],
      counts: [4, 1],
    },
  ],
];
it.each(cases)("supports %s", (kind, values, params) =>
  expect(check(kind, values, params)).toEqual(["12345"]),
);
const history = [
  { issue: "001", date: "2026-01-01", number: "12345" },
  { issue: "002", date: "2026-01-02", number: "23456" },
  { issue: "003", date: "2026-01-03", number: "99999" },
];
function historyCheck(
  kind: Rule["kind"],
  values: Rule["values"],
  params: Rule["params"] = {},
  candidate = "12345",
) {
  return filter({
    positions: defaultPositions(),
    candidates: [candidate],
    history,
    rules: [
      {
        id: kind,
        kind,
        values,
        params: { referenceIssue: "002", ...params },
        enabled: true,
        mode: "include",
      },
    ],
  }).numbers;
}
it("history predicates use frozen reference, even when later data exists", () => {
  expect(historyCheck("historyExclude", [])).toEqual([]);
  expect(historyCheck("historyExclude", [], {}, "99999")).toEqual(["99999"]);
  expect(historyCheck("samePosition", [0])).toEqual(["12345"]);
  expect(historyCheck("historyOverlap", [4])).toEqual(["12345"]);
  expect(historyCheck("neighborCounts", ["4:1:0"])).toEqual(["12345"]);
  expect(historyCheck("historyDelta", [5])).toEqual(["12345"]);
  expect(historyCheck("historyDelta", [-5], { absolute: false })).toEqual([
    "12345",
  ]);
  expect(historyCheck("frequency", [1], { positions: [0], window: 2 })).toEqual(
    ["12345"],
  );
  expect(historyCheck("omission", [1], { positions: [0] })).toEqual(["12345"]);
  expect(() =>
    historyCheck("omission", [1], { positions: [0] }, "99999"),
  ).toThrow("历史不足");
});
it("group tolerance counts complete groups and includes inversion", () => {
  const rules: Rule[] = [
    {
      id: "a",
      kind: "sum",
      values: [15],
      enabled: true,
      mode: "include",
      group: "g",
    },
    {
      id: "b",
      kind: "max",
      values: [5],
      enabled: true,
      mode: "exclude",
      group: "g",
    },
    { id: "c", kind: "min", values: [1], enabled: true, mode: "include" },
  ];
  const input = { positions: defaultPositions(), candidates: ["12345"], rules };
  expect(
    filter({ ...input, combination: { mode: "atLeast", minimum: 1 } }).numbers,
  ).toEqual(["12345"]);
  expect(
    filter({ ...input, combination: { mode: "atLeast", minimum: 2 } }).numbers,
  ).toEqual([]);
  expect(() =>
    filter({ ...input, combination: { mode: "atLeast", minimum: 3 } }),
  ).toThrow();
});
it("rejects malformed imports, configurations and history", () => {
  expect(() =>
    filter({ positions: defaultPositions(), rules: [], candidates: ["1234"] }),
  ).toThrow();
  expect(() => check("routeCounts", ["4:4:4"])).toThrow();
  expect(() => check("positionDiff", [1], { positions: [0, 0] })).toThrow();
  expect(() =>
    check("partition", [], { partitions: [[0], [1]], counts: [2, 3] }),
  ).toThrow();
  expect(() =>
    historyCheck("frequency", [1], { window: 0, positions: [0] }),
  ).toThrow();
  expect(() =>
    filter({
      positions: defaultPositions(),
      candidates: ["12345"],
      history: [history[0]!, history[0]!],
      rules: [
        {
          id: "h",
          kind: "historyExclude",
          enabled: true,
          mode: "include",
          values: [],
        },
      ],
    }),
  ).toThrow("重复");
});
it("historical overlap counts distinct digits rather than repeated occurrences", () => {
  const result = filter({
    positions: defaultPositions(),
    candidates: ["00127"],
    history: [{ issue: "1", date: "2026-01-01", number: "00000" }],
    rules: [
      {
        id: "overlap",
        kind: "historyOverlap",
        enabled: true,
        mode: "include",
        values: [1],
      },
    ],
  });
  expect(result.numbers).toEqual(["00127"]);
});
