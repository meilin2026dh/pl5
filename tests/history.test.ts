import { describe, it, expect } from "vitest";
import { metrics } from "../src/domain/pick5";
import {
  filterHistory,
  officialHistoryUrl,
  validateSnapshot,
  parseHistoryCsv,
  omissions,
  makeDemo,
  historyCsv,
} from "../src/lib/history";
describe("history CSV", () => {
  it("round-trips demo export preserving numbers", () =>
    expect(parseHistoryCsv(historyCsv(makeDemo(3)))).toEqual(makeDemo(3)));
  it("uses the shared metric definitions", () =>
    expect(metrics("00123")).toMatchObject({
      sum: 6,
      tail: 6,
      span: 3,
      odd: 2,
    }));
  it("preserves zeroes and accepts quoted fields", () =>
    expect(
      parseHistoryCsv('issue,date,number\n2026001,2026-01-01,"00123"')[0]
        .number,
    ).toBe("00123"));
  it("rejects impossible dates, malformed numbers and issue conflicts", () => {
    expect(() =>
      parseHistoryCsv("issue,date,number\n1,2026-02-30,12345"),
    ).toThrow();
    expect(() =>
      parseHistoryCsv("issue,date,number\n1,2026-02-28,1234"),
    ).toThrow();
    expect(() =>
      parseHistoryCsv(
        "issue,date,number\n1,2026-02-28,12345\n1,2026-03-01,12346",
      ),
    ).toThrow();
  });
  it("does not silently drop malformed rows", () =>
    expect(() =>
      parseHistoryCsv("issue,date,number\n1,2026-02-28,12345\nbad"),
    ).toThrow());
  it("marks an unobserved omission as a lower bound", () =>
    expect(
      omissions([{ issue: "1", date: "2026-01-01", number: "12345" }], 0)[0][0],
    ).toEqual({ value: 1, lowerBound: true }));
  it("resets omission certainty after date gaps", () =>
    expect(
      omissions(
        [
          { issue: "1", date: "2026-01-01", number: "01234" },
          { issue: "2", date: "2026-01-03", number: "12345" },
        ],
        0,
      )[1][0],
    ).toEqual({ value: 1, lowerBound: true }));
  it("creates deterministic demo records", () =>
    expect(makeDemo(200)).toHaveLength(200));
});

describe("history query and ranges", () => {
  it("maps each supported count to the official API page count", () => {
    expect([200, 500, 1000, 2000].map(officialHistoryUrl)).toEqual([
      "/api/history?pages=2",
      "/api/history?pages=5",
      "/api/history?pages=10",
      "/api/history?pages=20",
    ]);
    expect(() => officialHistoryUrl(1000000)).toThrow();
  });
  it("applies date and numeric issue bounds together", () => {
    const draws = [
      { issue: "9", date: "2026-01-01", number: "00123" },
      { issue: "10", date: "2026-01-02", number: "12345" },
      { issue: "11", date: "2026-01-03", number: "23456" },
    ];
    expect(
      filterHistory(draws, {
        fromDate: "2026-01-02",
        toDate: "",
        fromIssue: "9",
        toIssue: "10",
      }),
    ).toEqual([draws[1]]);
    expect(
      filterHistory(draws, {
        fromDate: "2027-01-01",
        toDate: "",
        fromIssue: "",
        toIssue: "",
      }),
    ).toEqual([]);
  });
  it("validates remote snapshots using the strict CSV rules", () => {
    expect(
      validateSnapshot({
        draws: [{ issue: "26001", date: "2026-01-01", number: "00123" }],
        source: "中国体彩网",
        version: "official-v1",
      }).draws[0].number,
    ).toBe("00123");
    expect(() =>
      validateSnapshot({
        draws: [{ issue: "26001", date: "2026-01-01", number: "123" }],
        source: "bad",
      }),
    ).toThrow();
    expect(() => validateSnapshot({ draws: [], source: "empty" })).toThrow();
  });
});
