// @vitest-environment jsdom
import React, { useState } from "react";
import { it, expect, vi, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  cleanup,
  act,
} from "@testing-library/react";
import SelectionLab from "../src/components/SelectionLab";
import { defaultSelection } from "../src/domain/selection/config";
import { selectPortfolio } from "../src/domain/selection/engine";
import { defaultPositions, type FilterInput } from "../src/domain/pick5";
class FakeWorker {
  static all: FakeWorker[] = [];
  onmessage: ((e: { data: any }) => void) | null = null;
  onerror: (() => void) | null = null;
  request: any;
  terminated = false;
  constructor() {
    FakeWorker.all.push(this);
  }
  postMessage(m: any) {
    this.request = m;
  }
  terminate() {
    this.terminated = true;
  }
}
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  FakeWorker.all = [];
});
function Harness({ extended = false }: { extended?: boolean }) {
  const [input, setInput] = useState<FilterInput>({
    positions: defaultPositions(),
    rules: [],
    historySource: "测试历史",
    history: Array.from({ length: extended ? 100 : 40 }, (_, i) => ({
      issue: String(i + 1),
      date: new Date(Date.UTC(2026, 0, i + 1)).toISOString().slice(0, 10),
      number: String((i * 7919) % 100000).padStart(5, "0"),
    })),
    candidates: ["12345", "54321", "01269", "89000", "00000"],
    selection: {
      ...defaultSelection,
      window: extended ? 80 : 40,
      scorer: extended ? "lstm" : "bayes",
      sequence: { context: 4, epochs: 1 },
      recent: 0,
      acMin: -4,
      minLarge: 0,
      maxLarge: 4,
      budget: 3,
    },
  });
  return (
    <>
      <SelectionLab input={input} onChange={setInput} />
      <output data-testid="input">{JSON.stringify(input)}</output>
    </>
  );
}
it("runs the real pipeline via worker contract, preserves configuration and loads diverse results", () => {
  vi.stubGlobal("Worker", FakeWorker);
  render(<Harness />);
  fireEvent.change(screen.getByLabelText("精选搜索器"), {
    target: { value: "mcga" },
  });
  fireEvent.change(screen.getByLabelText("蒙特卡洛采样次数"), {
    target: { value: "100" },
  });
  fireEvent.change(screen.getByLabelText("搜索迭代代数"), {
    target: { value: "2" },
  });
  fireEvent.click(screen.getByRole("button", { name: "运行多阶段精选" }));
  const w = FakeWorker.all[0],
    r = selectPortfolio(w.request.input, w.request.config);
  act(() => w.onmessage!({ data: { id: w.request.id, result: r } }));
  expect(screen.getByLabelText("精选号码").textContent).toBe(
    r.numbers.join("　"),
  );
  expect(w.terminated).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "将精选结果载入大底" }));
  const input = JSON.parse(screen.getByTestId("input").textContent!);
  expect(input.candidates).toEqual(r.numbers);
  expect(input.selection.method).toBe("mcga");
  expect(screen.queryByLabelText("精选结果")).toBeNull();
});
it("cancels and rejects obsolete replies after input changes", () => {
  vi.stubGlobal("Worker", FakeWorker);
  render(<Harness />);
  fireEvent.click(screen.getByRole("button", { name: "运行多阶段精选" }));
  const w = FakeWorker.all[0];
  fireEvent.click(screen.getByRole("button", { name: "取消精选" }));
  expect(w.terminated).toBe(true);
  act(() =>
    w.onmessage!({
      data: {
        id: w.request.id,
        result: selectPortfolio(w.request.input, w.request.config),
      },
    }),
  );
  expect(screen.queryByLabelText("精选结果")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "运行多阶段精选" }));
  const second = FakeWorker.all[1];
  fireEvent.change(screen.getByLabelText("精选目标注数"), {
    target: { value: "2" },
  });
  expect(second.terminated).toBe(true);
  expect(screen.queryByRole("button", { name: "取消精选" })).toBeNull();
});
it("persists untouched default settings on first run without cancelling its worker", () => {
  vi.stubGlobal("Worker", FakeWorker);
  function Bare() {
    const [input, setInput] = useState<FilterInput>({
      positions: defaultPositions(),
      rules: [],
      history: Array.from({ length: 100 }, (_, i) => ({
        issue: String(i + 1),
        date: new Date(Date.UTC(2026, 0, i + 1)).toISOString().slice(0, 10),
        number: "12345",
      })),
      candidates: ["01269"],
    });
    return (
      <>
        <SelectionLab input={input} onChange={setInput} />
        <output data-testid="bare">{JSON.stringify(input.selection)}</output>
      </>
    );
  }
  render(<Bare />);
  fireEvent.click(screen.getByRole("button", { name: "运行多阶段精选" }));
  const w = FakeWorker.all[0];
  expect(w.terminated).toBe(false);
  expect(JSON.parse(screen.getByTestId("bare").textContent!)).toEqual(
    defaultSelection,
  );
  act(() =>
    w.onmessage!({
      data: {
        id: w.request.id,
        result: selectPortfolio(w.request.input, w.request.config),
      },
    }),
  );
  expect(screen.getByLabelText("精选结果")).toBeTruthy();
});
it("uses the portfolio replay worker contract separately from scalar filtering", async () => {
  const { replaySelection } = await import("../src/domain/selection/engine");
  vi.stubGlobal("Worker", FakeWorker);
  render(<Harness />);
  fireEvent.click(screen.getByRole("button", { name: "回放最近10期精选" }));
  const w = FakeWorker.all[0];
  expect(w.request.task).toBe("replay");
  act(() =>
    w.onmessage!({
      data: {
        id: w.request.id,
        replay: replaySelection(w.request.input, w.request.config),
      },
    }),
  );
  expect(screen.getByLabelText("精选回放结果")).toBeTruthy();
  expect(screen.queryByLabelText("精选结果")).toBeNull();
});

it("exposes real sequence training diagnostics and a complete report action", () => {
  vi.stubGlobal("Worker", FakeWorker);
  render(<Harness extended />);
  fireEvent.click(screen.getByRole("button", { name: "运行多阶段精选" }));
  const w = FakeWorker.all[0],
    r = selectPortfolio(w.request.input, w.request.config);
  act(() => w.onmessage!({ data: { id: w.request.id, result: r } }));
  expect(screen.getByLabelText("时序模型训练诊断")).toBeTruthy();
  expect(screen.getByRole("button", { name: "复制时序训练报告" })).toBeTruthy();
});
