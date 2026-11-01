// @vitest-environment jsdom
import React, { useState } from "react";
import { it, expect, vi, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  act,
  cleanup,
} from "@testing-library/react";
import ProbabilityLab from "../src/components/ProbabilityLab";
import { analyzeProbability } from "../src/domain/probability/engine";
import { defaultProbability } from "../src/domain/probability/config";
import { defaultPositions, type FilterInput } from "../src/domain/pick5";
class WorkerDouble {
  static all: WorkerDouble[] = [];
  request: any;
  terminated = false;
  onmessage: ((e: any) => void) | null = null;
  constructor() {
    WorkerDouble.all.push(this);
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
  WorkerDouble.all = [];
  localStorage.clear();
});
function Harness({ defaults = false }: { defaults?: boolean }) {
  const [input, setInput] = useState<FilterInput>({
    positions: defaultPositions(),
    rules: [],
    candidates: ["00000", "00123"],
    history: Array.from({ length: defaults ? 800 : 180 }, (_, i) => ({
      issue: String(i + 1),
      date: new Date(Date.UTC(2025, 0, i + 1)).toISOString().slice(0, 10),
      number: String((i * 571) % 100000).padStart(5, "0"),
    })),
    probability: defaults
      ? undefined
      : {
          ...defaultProbability,
          train: 100,
          calibration: 20,
          test: 30,
          budget: 1,
        },
  });
  return (
    <>
      <ProbabilityLab input={input} onChange={setInput} />
      <output data-testid="input">{JSON.stringify(input)}</output>
    </>
  );
}
function run() {
  fireEvent.click(screen.getByRole("button", { name: "运行自适应概率实验" }));
  const w = WorkerDouble.all.at(-1)!,
    r = analyzeProbability(w.request.input, w.request.config);
  act(() => w.onmessage!({ data: { id: w.request.id, result: r } }));
  return { w, r };
}
it("shows real model/coverage/transport/online results and loads with undo", () => {
  vi.stubGlobal("Worker", WorkerDouble);
  render(<Harness />);
  const { r } = run();
  expect(screen.getByRole("table", { name: "贝叶斯证据与MDL" })).toBeTruthy();
  expect(screen.getByText(/预算结果不继承校准覆盖/)).toBeTruthy();
  expect(
    screen.getByRole("table", { name: "Wasserstein压力情景" }),
  ).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "查看完整校准集合" }));
  expect(screen.getByLabelText("校准集合分页")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("概率审计号码"), {
    target: { value: "00123" },
  });
  fireEvent.click(screen.getByRole("button", { name: "查询概率决策" }));
  expect(screen.getByLabelText("号码概率决策").textContent).toContain("00123");
  fireEvent.click(
    screen.getByRole("button", { name: "载入概率预算组合并停用原条件" }),
  );
  expect(
    JSON.parse(screen.getByTestId("input").textContent!).candidates,
  ).toEqual(r.portfolio.numbers);
  fireEvent.click(screen.getByRole("button", { name: "撤销概率载入" }));
  expect(
    JSON.parse(screen.getByTestId("input").textContent!).candidates,
  ).toEqual(["00000", "00123"]);
});
it("cancels tasks, rejects stale replies, invalidates changed configuration", () => {
  vi.stubGlobal("Worker", WorkerDouble);
  render(<Harness />);
  fireEvent.click(screen.getByRole("button", { name: "运行自适应概率实验" }));
  const w = WorkerDouble.all[0];
  fireEvent.click(screen.getByRole("button", { name: "取消概率实验" }));
  act(() => w.onmessage!({ data: { id: w.request.id, result: {} } }));
  expect(screen.queryByLabelText("自适应概率结果")).toBeNull();
  run();
  fireEvent.change(screen.getByLabelText("概率预算注数"), {
    target: { value: "2" },
  });
  expect(screen.queryByLabelText("自适应概率结果")).toBeNull();
});
it("persists prior exposure across parameter changes and page remount", () => {
  vi.stubGlobal("Worker", WorkerDouble);
  const view = render(<Harness />);
  run();
  view.unmount();
  render(<Harness />);
  run();
  expect(screen.getByText(/本测试区间此前已查看/)).toBeTruthy();
});

it("runs from absent config without self-cancelling and protects undo after edits", () => {
  vi.stubGlobal("Worker", WorkerDouble);
  render(<Harness defaults />);
  fireEvent.click(screen.getByRole("button", { name: "运行自适应概率实验" }));
  const w = WorkerDouble.all.at(-1)!;
  expect(w.terminated).toBe(false);
  const r = analyzeProbability(w.request.input, w.request.config);
  act(() => w.onmessage!({ data: { id: w.request.id, result: r } }));
  expect(screen.getByLabelText("自适应概率结果")).toBeTruthy();
  fireEvent.click(
    screen.getByRole("button", { name: "载入概率预算组合并停用原条件" }),
  );
  fireEvent.change(screen.getByLabelText("概率预算注数"), {
    target: { value: "2" },
  });
  expect(
    (screen.getByRole("button", { name: "撤销概率载入" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
});
