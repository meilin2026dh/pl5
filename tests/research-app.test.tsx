// @vitest-environment jsdom
import React from "react";
import { it, expect, vi, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  act,
  cleanup,
  within,
} from "@testing-library/react";
import App from "../src/App";
import { filter, type FilterInput } from "../src/domain/pick5";
class Port {
  static all: Port[] = [];
  onmessage: ((e: any) => void) | null = null;
  onerror: (() => void) | null = null;
  message: any;
  constructor() {
    Port.all.push(this);
  }
  terminate() {}
  postMessage(m: any) {
    this.message = m;
  }
  reply() {
    this.onmessage?.({
      data: {
        requestId: this.message.requestId,
        result: filter(this.message.input as FilterInput),
      },
    });
  }
}
afterEach(() => {
  cleanup();
  localStorage.clear();
  history.replaceState({}, "", "/workbench");
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  Port.all = [];
});
it("creates a seeded model, runs the real engine, saves and restores it, then invalidates diagnostics", () => {
  vi.stubGlobal("Worker", Port);
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  render(<App />);
  expect(
    screen.getByRole("link", { name: "实验方法" }).getAttribute("href"),
  ).toBe("#research-title");
  fireEvent.click(screen.getByRole("button", { name: "添加实验方法" }));
  fireEvent.change(screen.getByRole("combobox", { name: "实验方法" }), {
    target: { value: "bma" },
  });
  fireEvent.change(screen.getByLabelText("并列策略"), {
    target: { value: "seeded" },
  });
  fireEvent.change(screen.getByLabelText("保留比例（%）"), {
    target: { value: "10" },
  });
  fireEvent.change(screen.getByLabelText("随机种子"), {
    target: { value: "42" },
  });
  fireEvent.click(screen.getByText("保存实验条件"));
  fireEvent.click(screen.getByText("开始缩水"));
  expect(
    Port.all[0].message.input.rules.find((r: any) => r.kind === "research")
      .research.seed,
  ).toBe(42);
  act(() => Port.all[0].reply());
  expect(screen.getByText("实验计算说明")).toBeTruthy();
  expect(screen.getByText("共 10,000 组")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "保存方案" }));
  fireEvent.change(screen.getByLabelText("方案名称"), {
    target: { value: "研究BMA" },
  });
  fireEvent.click(screen.getByText("确认保存"));
  cleanup();
  render(<App />);
  fireEvent.click(screen.getByRole("link", { name: "我的方案" }));
  fireEvent.click(screen.getByRole("button", { name: "使用方案" }));
  fireEvent.click(screen.getByRole("button", { name: "编辑 BMA七模型平均" }));
  expect((screen.getByLabelText("随机种子") as HTMLInputElement).value).toBe(
    "42",
  );
  fireEvent.click(screen.getByText("取消"));
  fireEvent.click(screen.getByText("开始缩水"));
  act(() => Port.all.at(-1)!.reply());
  expect(screen.getByText("实验计算说明")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "万位号码0" }));
  expect(screen.queryByText("实验计算说明")).toBeNull();
  expect(
    (screen.getByRole("button", { name: "导出 TXT" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
});
