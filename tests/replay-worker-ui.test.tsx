// @vitest-environment jsdom
import React from "react";
import { it, expect, vi, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  act,
  cleanup,
} from "@testing-library/react";
import Backtest from "../src/components/Backtest";
import { defaultPositions, type FilterInput } from "../src/domain/pick5";
class Port {
  static all: Port[] = [];
  onmessage: ((e: any) => void) | null = null;
  onerror: (() => void) | null = null;
  message: any;
  terminate = vi.fn();
  constructor() {
    Port.all.push(this);
  }
  postMessage(m: any) {
    this.message = m;
  }
  reply() {
    this.onmessage?.({
      data: {
        requestId: this.message.requestId,
        rows: [
          {
            issue: "1",
            date: "2026-01-01",
            number: "00000",
            referenceIssue: "无",
            status: "retained",
          },
        ],
      },
    });
  }
}
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  Port.all = [];
});
it("runs replay off the UI thread and cancels obsolete replies", () => {
  vi.stubGlobal("Worker", Port);
  const input: FilterInput = {
    positions: defaultPositions(),
    rules: [],
    history: [],
  };
  const { rerender } = render(<Backtest input={input} />);
  fireEvent.click(screen.getByText("运行历史回放"));
  expect(Port.all[0].message.operation).toBe("backtest");
  fireEvent.click(screen.getByText("取消回放"));
  expect(Port.all[0].terminate).toHaveBeenCalledOnce();
  act(() => Port.all[0].reply());
  expect(screen.queryByText("00000")).toBeNull();
  fireEvent.click(screen.getByText("运行历史回放"));
  const second = Port.all[1];
  rerender(<Backtest input={{ ...input, historySource: "changed" }} />);
  expect(second.terminate).toHaveBeenCalledOnce();
  act(() => second.reply());
  expect(screen.queryByText("00000")).toBeNull();
});

it("shows completed rows, releases worker and handles calculation errors", () => {
  vi.stubGlobal("Worker", Port);
  render(<Backtest input={{ positions: defaultPositions(), rules: [] }} />);
  fireEvent.click(screen.getByText("运行历史回放"));
  act(() => Port.all[0].reply());
  expect(screen.getByText("00000")).toBeTruthy();
  expect(Port.all[0].terminate).toHaveBeenCalledOnce();
  fireEvent.click(screen.getByText("运行历史回放"));
  const p = Port.all[1];
  act(() =>
    p.onmessage?.({
      data: { requestId: p.message.requestId, error: "历史不足" },
    }),
  );
  expect(screen.getByRole("alert").textContent).toBe("历史不足");
  expect(p.terminate).toHaveBeenCalledOnce();
  expect(screen.getByText("运行历史回放")).toBeTruthy();
});
