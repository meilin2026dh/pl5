// @vitest-environment jsdom
import React from "react";
import { afterEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  act,
} from "@testing-library/react";
import History from "../src/pages/History";
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
const fixture = {
  draws: [
    { issue: "26001", date: "2026-01-01", number: "00123" },
    { issue: "26002", date: "2026-01-02", number: "98765" },
  ],
  source: "中国体彩网",
  version: "official-fixture-v1",
  updatedAt: "2026-10-18T00:00:00Z",
  sourceUrl: "https://www.lottery.gov.cn",
};
it("loads the requested official range, displays known metrics and applies date range", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValue({ ok: true, json: async () => fixture });
  vi.stubGlobal("fetch", fetcher);
  const onDataChange = vi.fn();
  render(<History onApply={() => {}} onDataChange={onDataChange} />);
  fireEvent.change(screen.getByLabelText("真实开奖期数"), {
    target: { value: "1000" },
  });
  fireEvent.click(screen.getByRole("button", { name: "获取官方开奖" }));
  await screen.findByText("中国体彩网");
  expect(fetcher.mock.calls[0][0]).toBe("/api/history?pages=10");
  await waitFor(() =>
    expect(onDataChange).toHaveBeenLastCalledWith(
      fixture.draws,
      fixture.source,
    ),
  );
  fireEvent.click(screen.getByRole("tab", { name: "开奖明细" }));
  expect(screen.getByText("00123")).toBeTruthy();
  fireEvent.keyDown(screen.getByLabelText("查看 26001 期详情"), {
    key: "Enter",
  });
  expect(screen.getByLabelText("开奖详情").textContent).toContain(
    "和值 6 · 跨度 3 · 和尾 6",
  );
  fireEvent.change(screen.getByLabelText("开始日期"), {
    target: { value: "2026-01-02" },
  });
  fireEvent.click(screen.getByRole("button", { name: "应用范围" }));
  expect(screen.queryByText("00123")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "重置范围" }));
  expect(screen.getByText("00123")).toBeTruthy();
});
it("ignores a stale file read after restoring demo", async () => {
  render(<History onApply={() => {}} />);
  let resolve!: (value: string) => void;
  const text = new Promise<string>((r) => {
    resolve = r;
  });
  const file = new File([""], "late.csv", { type: "text/csv" });
  Object.defineProperty(file, "text", { value: () => text });
  fireEvent.change(document.querySelector('input[type="file"]')!, {
    target: { files: [file] },
  });
  fireEvent.click(screen.getByRole("button", { name: "恢复演示" }));
  await act(async () => {
    resolve("issue,date,number\n26001,2026-01-01,00123");
    await text;
  });
  expect(screen.getByText("演示数据 · 非真实开奖")).toBeTruthy();
  expect(screen.queryByText("导入文件：late.csv")).toBeNull();
});
it("retains the current data on failed remote loads", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("离线")));
  render(<History onApply={() => {}} />);
  fireEvent.click(screen.getByRole("button", { name: "获取官方开奖" }));
  await waitFor(() =>
    expect(screen.getByRole("alert").textContent).toBe("离线"),
  );
  expect(screen.getByText("演示数据 · 非真实开奖")).toBeTruthy();
});

it("ignores an official response that finishes after demo reset", async () => {
  let finish!: (value: unknown) => void;
  vi.stubGlobal(
    "fetch",
    vi.fn().mockReturnValue(
      new Promise((resolve) => {
        finish = resolve;
      }),
    ),
  );
  render(<History onApply={() => {}} />);
  fireEvent.click(screen.getByRole("button", { name: "获取官方开奖" }));
  fireEvent.click(screen.getByRole("button", { name: "恢复演示" }));
  await act(async () => {
    finish({ ok: true, json: async () => fixture });
  });
  expect(screen.getByText("演示数据 · 非真实开奖")).toBeTruthy();
  expect(screen.queryByText("中国体彩网")).toBeNull();
});

it("shows the empty range state without invalid statistics", () => {
  render(<History onApply={() => {}} />);
  fireEvent.change(screen.getByLabelText("开始日期"), {
    target: { value: "2030-01-01" },
  });
  fireEvent.click(screen.getByRole("button", { name: "应用范围" }));
  expect(screen.getByText("当前范围没有开奖记录，请调整范围。")).toBeTruthy();
  expect(document.body.textContent).not.toContain("NaN");
  expect(document.body.textContent).not.toContain("Infinity");
});
