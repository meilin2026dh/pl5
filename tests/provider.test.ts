import { describe, it, expect, vi } from "vitest";
import { parseOfficial, mergeDraws, officialHistory } from "../server/provider.ts";
describe("official history boundary", () => {
  it("preserves zeros and sorts official five-digit draws", () => {
    expect(
      parseOfficial({
        success: true,
        value: {
          list: [
            {
              lotteryGameNum: "350133",
              lotteryDrawNum: "26277",
              lotteryDrawTime: "2026-10-18",
              lotteryDrawResult: "0 0 1 2 7",
            },
          ],
        },
      }),
    ).toEqual([{ issue: "26277", date: "2026-10-18", number: "00127" }]);
  });
  it("rejects API failures, other games, invalid dates, and malformed digits", () => {
    expect(() => parseOfficial({ success: false })).toThrow();
    for (const change of [
      { lotteryGameNum: "35" },
      { lotteryDrawTime: "2026-02-30" },
      { lotteryDrawResult: "1 2 3" },
    ])
      expect(() =>
        parseOfficial({
          success: true,
          value: {
            list: [
              {
                lotteryGameNum: "350133",
                lotteryDrawNum: "26277",
                lotteryDrawTime: "2026-10-18",
                lotteryDrawResult: "0 0 1 2 7",
                ...change,
              },
            ],
          },
        }),
      ).toThrow();
  });
  it("deduplicates identical issues but refuses conflicting revisions", () => {
    const a = { issue: "26277", date: "2026-10-18", number: "00127" };
    expect(mergeDraws([a, a])).toEqual([a]);
    expect(() => mergeDraws([a, { ...a, number: "99999" }])).toThrow();
  });
});

it("queries the official service again so newly published draws are not hidden by a five-minute cache", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: true,
    text: async () => JSON.stringify({success: true, value: {list: [{lotteryGameNum: "350133", lotteryDrawNum: "26287", lotteryDrawTime: "2026-10-28", lotteryDrawResult: "15448"}]}}),
  } as Response);
  try {
    await officialHistory(1);
    await officialHistory(1);
    expect(fetcher).toHaveBeenCalledTimes(2);
  } finally { fetcher.mockRestore(); }
});
