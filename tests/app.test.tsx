// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, afterEach, beforeEach, vi } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import App from "../src/App";
beforeEach(() => {
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
});
afterEach(() => {
  cleanup();
  localStorage.clear();
  history.replaceState({}, "", "/workbench");
});
describe("workbench and routes", () => {
  it("navigates to independent history and preserves selected positions", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "万位号码0" }));
    expect(
      screen
        .getByRole("button", { name: "万位号码0" })
        .getAttribute("aria-pressed"),
    ).toBe("false");
    fireEvent.click(screen.getByRole("link", { name: "历史走势" }));
    expect(location.pathname).toBe("/history");
    fireEvent.click(screen.getByRole("link", { name: "缩水工作台" }));
    expect(
      screen
        .getByRole("button", { name: "万位号码0" })
        .getAttribute("aria-pressed"),
    ).toBe("false");
  });
  it("saves a plan that can be restored from a fresh render", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "保存方案" }));
    fireEvent.change(screen.getByLabelText("方案名称"), {
      target: { value: "前导零组合" },
    });
    fireEvent.click(screen.getByRole("button", { name: "确认保存" }));
    cleanup();
    render(<App />);
    fireEvent.click(screen.getByRole("link", { name: "我的方案" }));
    expect(screen.getByText("前导零组合")).toBeTruthy();
  });
});

describe("review regressions", () => {
  it("restores every imported AND rule even if their kinds repeat", () => {
    localStorage.setItem(
      "pl5.plans.v1",
      JSON.stringify({
        schemaVersion: 1,
        plans: [
          {
            id: "multi",
            name: "双和值",
            createdAt: "2026-10-18T12:00:00Z",
            input: {
              positions: Array.from({ length: 5 }, () => [0, 1]),
              rules: [
                {
                  id: "a",
                  kind: "sum",
                  enabled: true,
                  mode: "include",
                  values: [1, 2],
                },
                {
                  id: "b",
                  kind: "sum",
                  enabled: true,
                  mode: "exclude",
                  values: [2],
                },
              ],
            },
          },
        ],
      }),
    );
    render(<App />);
    fireEvent.click(screen.getByRole("link", { name: "我的方案" }));
    fireEvent.click(screen.getByRole("button", { name: "使用方案" }));
    expect(screen.getAllByRole("checkbox", { name: "和值" })).toHaveLength(2);
  });
  it("keeps history view settings when navigating away and back", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("link", { name: "历史走势" }));
    fireEvent.change(screen.getByLabelText("观察范围"), {
      target: { value: "30" },
    });
    fireEvent.click(screen.getByRole("link", { name: "缩水工作台" }));
    fireEvent.click(screen.getByRole("link", { name: "历史走势" }));
    expect((screen.getByLabelText("观察范围") as HTMLSelectElement).value).toBe(
      "30",
    );
  });
  it("adds history conditions without overwriting an existing rule", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "和值 45" }));
    fireEvent.click(screen.getByRole("link", { name: "历史走势" }));
    fireEvent.click(screen.getByRole("button", { name: "预览条件 ↗" }));
    fireEvent.click(screen.getByRole("button", { name: "确认添加到工作台" }));
    expect(screen.getAllByRole("checkbox", { name: "和值" })).toHaveLength(2);
  });
});
it("restores arbitrary imported IDs without colliding with default rule IDs", () => {
  localStorage.setItem(
    "pl5.plans.v1",
    JSON.stringify({
      schemaVersion: 1,
      plans: [
        {
          id: "collision",
          name: "标识冲突",
          createdAt: "2026-10-18T12:00:00Z",
          input: {
            positions: Array.from({ length: 5 }, () => [0, 1]),
            rules: [
              {
                id: "tail",
                kind: "sum",
                enabled: false,
                mode: "include",
                values: [],
              },
            ],
          },
        },
      ],
    }),
  );
  render(<App />);
  fireEvent.click(screen.getByRole("link", { name: "我的方案" }));
  fireEvent.click(screen.getByRole("button", { name: "使用方案" }));
  fireEvent.click(screen.getByRole("button", { name: "保存方案" }));
  fireEvent.click(screen.getByRole("button", { name: "确认保存" }));
  expect(screen.queryByRole("dialog")).toBeNull();
});
it("keeps keyboard focus inside the save dialog and restores the trigger focus", () => {
  render(<App />);
  const trigger = screen.getByRole("button", { name: "保存方案" });
  trigger.focus();
  fireEvent.click(trigger);
  const close = screen.getByRole("button", { name: "关闭保存窗口" });
  close.focus();
  fireEvent.keyDown(close, { key: "Tab", shiftKey: true });
  expect(document.activeElement).toBe(
    screen.getByRole("button", { name: "确认保存" }),
  );
  fireEvent.keyDown(document.activeElement!, { key: "Escape" });
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(document.activeElement).toBe(trigger);
});
