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
import ConditionLab from "../src/components/ConditionLab";
import { analyzeConditions } from "../src/domain/audit/engine";
import { defaultAudit } from "../src/domain/audit/config";
import { defaultPositions, type FilterInput } from "../src/domain/pick5";
class WorkerStub {
  static all: WorkerStub[] = [];
  request: any;
  terminated = false;
  onmessage: ((e: any) => void) | null = null;
  constructor() {
    WorkerStub.all.push(this);
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
  WorkerStub.all = [];
});
function Harness() {
  const [input, setInput] = useState<FilterInput>({
    positions: defaultPositions(),
    rules: [
      { id: "sum", kind: "sum", enabled: true, mode: "include", values: [15] },
    ],
    history: Array.from({ length: 60 }, (_, i) => ({
      issue: String(i + 1),
      date: new Date(Date.UTC(2026, 0, i + 1)).toISOString().slice(0, 10),
      number: "12345",
    })),
    audit: { ...defaultAudit, pool: "current", training: 40, target: 10000 },
  });
  return (
    <>
      <ConditionLab input={input} onChange={setInput} />
      <output data-testid="config">{JSON.stringify(input)}</output>
    </>
  );
}
it("runs the real condition engine through worker contract and applies its rules", () => {
  vi.stubGlobal("Worker", WorkerStub);
  render(<Harness />);
  fireEvent.click(screen.getByRole("button", { name: "分析相关性与预算" }));
  const w = WorkerStub.all[0],
    r = analyzeConditions(w.request.input, w.request.config, w.request.walk);
  act(() => w.onmessage!({ data: { id: w.request.id, result: r } }));
  expect(w.terminated).toBe(true);
  fireEvent.click(
    screen.getByRole("button", { name: "应用选中条件（其余停用）" }),
  );
  const applied = JSON.parse(screen.getByTestId("config").textContent!);
  expect(applied.combination.mode).toBe("strict");
  expect(applied.rules.filter((r: any) => r.enabled)).toEqual(
    r.analysis.selectedRules,
  );
  expect(
    screen.queryByRole("button", { name: "应用选中条件（其余停用）" }),
  ).toBeNull();
});
it("cancels workers and ignores replies after cancellation or config edits", () => {
  vi.stubGlobal("Worker", WorkerStub);
  render(<Harness />);
  fireEvent.click(screen.getByRole("button", { name: "运行Walk-forward体检" }));
  const w = WorkerStub.all[0];
  fireEvent.click(screen.getByRole("button", { name: "取消条件体检" }));
  expect(w.terminated).toBe(true);
  act(() =>
    w.onmessage!({ data: { id: w.request.id, result: { analysis: {} } } }),
  );
  expect(
    screen.queryByRole("button", { name: "应用选中条件（其余停用）" }),
  ).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "分析相关性与预算" }));
  const second = WorkerStub.all[1];
  fireEvent.change(screen.getByLabelText("体检目标注数"), {
    target: { value: "1000" },
  });
  expect(second.terminated).toBe(true);
});
