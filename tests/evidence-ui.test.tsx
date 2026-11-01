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
import EvidenceLab from "../src/components/EvidenceLab";
import { defaultEvidence } from "../src/domain/evidence/config";
import { analyzeEvidence } from "../src/domain/evidence/engine";
import { defaultPositions, type FilterInput } from "../src/domain/pick5";
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
    candidates: ["00000", "00001", "11111"],
    history: Array.from({ length: 180 }, (_, i) => ({
      issue: String(i + 1),
      date: new Date(Date.UTC(2025, 0, i + 1)).toISOString().slice(0, 10),
      number: "00000",
    })),
    evidence: {
      ...defaultEvidence,
      window: 40,
      monitor: 40,
      checks: 1,
      resamples: 99,
      tune: 20,
      calibration: 20,
      test: 60,
      budget: 2,
    },
  });
  return (
    <>
      <EvidenceLab input={input} onChange={setInput} />
      <output data-testid="input">{JSON.stringify(input)}</output>
    </>
  );
}
it("shows real-engine quality/checks/calibration/disagreement and loads only eligible numbers", () => {
  vi.stubGlobal("Worker", FakeWorker);
  render(<Harness />);
  fireEvent.click(
    screen.getByRole("button", { name: "运行随机性与稳健性体检" }),
  );
  const w = FakeWorker.all[0],
    r = analyzeEvidence(w.request.input, w.request.config);
  act(() => w.onmessage!({ data: { id: w.request.id, result: r } }));
  expect(w.terminated).toBe(true);
  expect(screen.getByRole("table", { name: "随机性检验表" })).toBeTruthy();
  expect(
    screen.getByRole("img", { name: "时间外顶标签可靠性图" }),
  ).toBeTruthy();
  expect(screen.getByText("均匀评分回退")).toBeTruthy();
  expect(screen.getByRole("table", { name: "模型分歧候选" })).toBeTruthy();
  fireEvent.click(
    screen.getByRole("button", { name: "载入审查组合并停用原条件" }),
  );
  expect(
    JSON.parse(screen.getByTestId("input").textContent!).candidates,
  ).toEqual(r.portfolio?.numbers);
  expect(screen.queryByLabelText("证据体检结果")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "撤销审查载入" }));
  expect(
    JSON.parse(screen.getByTestId("input").textContent!).candidates,
  ).toEqual(["00000", "00001", "11111"]);
});
it("cancels and rejects stale replies after cancellation or changed parameters", () => {
  vi.stubGlobal("Worker", FakeWorker);
  render(<Harness />);
  fireEvent.click(
    screen.getByRole("button", { name: "运行随机性与稳健性体检" }),
  );
  const w = FakeWorker.all[0];
  fireEvent.click(screen.getByRole("button", { name: "取消证据体检" }));
  expect(w.terminated).toBe(true);
  act(() => w.onmessage!({ data: { id: w.request.id, result: {} } }));
  expect(screen.queryByLabelText("证据体检结果")).toBeNull();
  fireEvent.click(
    screen.getByRole("button", { name: "运行随机性与稳健性体检" }),
  );
  const second = FakeWorker.all[1];
  fireEvent.change(screen.getByLabelText("证据显著性水平"), {
    target: { value: "0.01" },
  });
  expect(second.terminated).toBe(true);
});
it("shows quality errors without exposing a portfolio on blocked data", () => {
  vi.stubGlobal("Worker", FakeWorker);
  render(<Harness />);
  fireEvent.click(
    screen.getByRole("button", { name: "运行随机性与稳健性体检" }),
  );
  const w = FakeWorker.all[0],
    r = analyzeEvidence(
      {
        ...w.request.input,
        history: [w.request.input.history[0], w.request.input.history[0]],
      },
      w.request.config,
    );
  act(() => w.onmessage!({ data: { id: w.request.id, result: r } }));
  expect(screen.getByText(/数据质量未通过/)).toBeTruthy();
  expect(
    screen.queryByRole("button", { name: "载入审查组合并停用原条件" }),
  ).toBeNull();
});
