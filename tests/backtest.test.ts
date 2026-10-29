import { it, expect } from "vitest";
import { backtest } from "../src/domain/backtest";
import { defaultPositions, type FilterInput } from "../src/domain/pick5";
const rows = [
  { issue: "1", date: "2026-10-01", number: "00000" },
  { issue: "2", date: "2026-10-02", number: "00001" },
  { issue: "3", date: "2026-10-03", number: "00002" },
];
it("replays only using history before the evaluated draw and respects candidate base", () => {
  const input: FilterInput = {
    positions: defaultPositions(),
    rules: [
      {
        id: "h",
        kind: "historyExclude",
        enabled: true,
        mode: "include",
        values: [],
      },
    ],
    history: rows,
  };
  expect(backtest(input, 3).map((r) => r.status)).toEqual([
    "insufficient",
    "retained",
    "retained",
  ]);
  expect(
    backtest({ ...input, candidates: ["00000"] }, 3).map((r) => r.status),
  ).toEqual(["insufficient", "outside", "outside"]);
});
it("never treats insufficient frequency history as a successful filter", () => {
  const input: FilterInput = {
    positions: defaultPositions(),
    rules: [
      {
        id: "f",
        kind: "frequency",
        enabled: true,
        mode: "include",
        values: [0],
        params: { positions: [0], window: 10 },
      },
    ],
    history: rows,
  };
  expect(backtest(input, 3).every((r) => r.status === "insufficient")).toBe(
    true,
  );
});
