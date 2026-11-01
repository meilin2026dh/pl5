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
import InnovationLab from "../src/components/InnovationLab";
import { defaultPositions, type FilterInput } from "../src/domain/pick5";
import { defaultInnovation } from "../src/domain/innovation/config";
import { runInnovation } from "../src/domain/innovation/engine";
class FakeWorker {
  static all: FakeWorker[] = [];
  request: any;
  terminated = false;
  onmessage: ((e: any) => void) | null = null;
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
function Harness() {
  const [input, setInput] = useState<FilterInput>({
    positions: defaultPositions(),
    rules: [],
    history: Array.from({ length: 40 }, (_, i) => ({
      issue: String(i + 1),
      date: new Date(Date.UTC(2026, 0, i + 1)).toISOString().slice(0, 10),
      number: "00000",
    })),
    candidates: ["00000", "00001", "11111"],
    innovation: {
      ...defaultInnovation,
      window: 40,
      budget: 2,
      simulations: 100,
    },
  });
  return (
    <>
      <InnovationLab input={input} onChange={setInput} />
      <output data-testid="input">{JSON.stringify(input)}</output>
    </>
  );
}
it("runs real engine, queries decisions and reversibly loads its portfolio", () => {
  vi.stubGlobal("Worker", FakeWorker);
  render(<Harness />);
  fireEvent.click(screen.getByRole("button", { name: "运行覆盖与审计" }));
  const w = FakeWorker.all[0],
    result = runInnovation(w.request.input, w.request.config);
  act(() => w.onmessage!({ data: { id: w.request.id, result } }));
  expect(screen.getByLabelText("覆盖审计结果")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("查询号码决策"), {
    target: { value: "99999" },
  });
  expect(screen.getByText(/99999：原始大底外/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "载入大底并停用原条件" }));
  expect(
    JSON.parse(screen.getByTestId("input").textContent!).candidates,
  ).toEqual(result.numbers);
  expect(screen.queryByLabelText("覆盖审计结果")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "撤销本次载入" }));
  expect(
    JSON.parse(screen.getByTestId("input").textContent!).candidates,
  ).toEqual(["00000", "00001", "11111"]);
});
it("cancels and invalidates work when parameters change", () => {
  vi.stubGlobal("Worker", FakeWorker);
  render(<Harness />);
  fireEvent.click(screen.getByRole("button", { name: "运行覆盖与审计" }));
  const w = FakeWorker.all[0];
  fireEvent.click(screen.getByRole("button", { name: "取消覆盖实验" }));
  expect(w.terminated).toBe(true);
  act(() => w.onmessage!({ data: { id: w.request.id, result: {} } }));
  expect(screen.queryByLabelText("覆盖审计结果")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "运行覆盖与审计" }));
  const second = FakeWorker.all[1];
  fireEvent.change(screen.getByLabelText("覆盖注数预算"), {
    target: { value: "3" },
  });
  expect(second.terminated).toBe(true);
});
it("discloses soft-policy override and rejects bad configuration before dispatch", () => {
  vi.stubGlobal("Worker", FakeWorker);
  render(<Harness />);
  fireEvent.change(screen.getByLabelText("覆盖条件策略"), {
    target: { value: "soft" },
  });
  expect(screen.getByText(/软支持模式：原条件失败/)).toBeTruthy();
  fireEvent.change(screen.getByLabelText("覆盖目标数字池"), {
    target: { value: "00" },
  });
  fireEvent.click(screen.getByRole("button", { name: "运行覆盖与审计" }));
  expect(FakeWorker.all).toHaveLength(0);
  expect(screen.getByText("覆盖实验配置错误；目标数字池须为1—8个不同数字")).toBeTruthy();
});
