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
import SequenceResearchLab from "../src/components/SequenceResearchLab";
import { analyzeLab } from "../src/domain/lab/engine";
import { defaultLab } from "../src/domain/lab/config";
import { defaultPositions, type FilterInput } from "../src/domain/pick5";
class W {
  static all: W[] = [];
  request: any;
  terminated = false;
  onmessage: ((e: any) => void) | null = null;
  constructor() {
    W.all.push(this);
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
  W.all = [];
  localStorage.clear();
});
function Harness() {
  const [input, setInput] = useState<FilterInput>({
    positions: defaultPositions(),
    rules: [],
    history: Array.from({ length: 100 }, (_, i) => ({
      issue: String(i + 1),
      date: new Date(Date.UTC(2025, 0, i + 1)).toISOString().slice(0, 10),
      number: "00000",
    })),
    lab: {
      ...defaultLab,
      candidatesText: "00000 11111",
      targetsText: "00000",
      cover: { ...defaultLab.cover, radius: 0, budget: 1 },
    },
  });
  return (
    <>
      <SequenceResearchLab input={input} onChange={setInput} />
      <output data-testid="input">{JSON.stringify(input)}</output>
    </>
  );
}
function run(task: "posterior" | "cover") {
  fireEvent.click(
    screen.getByRole("button", {
      name: task === "posterior" ? "同步增量后验与区间" : "求解有限整数覆盖",
    }),
  );
  const w = W.all.at(-1)!,
    r = analyzeLab(w.request.input, w.request.config, task, w.request.previous);
  act(() => w.onmessage!({ data: { id: w.request.id, result: r } }));
  return r;
}
it("renders real posterior, reuses persisted state and exposes capabilities", () => {
  vi.stubGlobal("Worker", W);
  render(<Harness />);
  run("posterior");
  expect(screen.getByRole("table", { name: "增量后验可信区间" })).toBeTruthy();
  run("posterior");
  expect(screen.getByText(/unchanged/)).toBeTruthy();
  fireEvent.click(screen.getByText("方法能力与执行管道", { exact: true }));
  expect(screen.getByRole("table", { name: "方法能力目录" })).toBeTruthy();
});
it("loads an independently certified cover and supports undo with changed input protection", () => {
  vi.stubGlobal("Worker", W);
  render(<Harness />);
  const r = run("cover");
  expect(screen.getByText("OPTIMAL", { exact: true })).toBeTruthy();
  fireEvent.click(
    screen.getByRole("button", { name: "载入有限覆盖组合并停用原条件" }),
  );
  expect(
    JSON.parse(screen.getByTestId("input").textContent!).candidates,
  ).toEqual(r.cover!.numbers);
  fireEvent.click(screen.getByRole("button", { name: "撤销有限覆盖载入" }));
  expect(
    JSON.parse(screen.getByTestId("input").textContent!).candidates,
  ).toBeUndefined();
});
it("cancels and discards stale replies after parameter changes", () => {
  vi.stubGlobal("Worker", W);
  render(<Harness />);
  fireEvent.click(screen.getByRole("button", { name: "求解有限整数覆盖" }));
  const w = W.all[0];
  fireEvent.click(screen.getByRole("button", { name: "取消研究计算" }));
  act(() => w.onmessage!({ data: { id: w.request.id, result: {} } }));
  expect(screen.queryByLabelText("有限覆盖结果")).toBeNull();
  run("cover");
  fireEvent.change(screen.getByLabelText("有限覆盖预算"), {
    target: { value: "2" },
  });
  expect(screen.queryByLabelText("有限覆盖结果")).toBeNull();
});
