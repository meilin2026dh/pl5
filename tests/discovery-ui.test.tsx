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
import DiscoveryLab from "../src/components/DiscoveryLab";
import { defaultPositions, type FilterInput } from "../src/domain/pick5";
import { defaultDiscovery } from "../src/domain/discovery/config";
import { analyzeDiscovery } from "../src/domain/discovery/engine";
class W {
  static all: W[] = [];
  request: any;
  onmessage: any;
  onerror: any;
  dead = false;
  constructor() {
    W.all.push(this);
  }
  postMessage(r: any) {
    this.request = r;
  }
  terminate() {
    this.dead = true;
  }
}
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  W.all = [];
});
function H() {
  const [input, onChange] = useState<FilterInput>({
    positions: defaultPositions(),
    rules: [],
    history: Array.from({ length: 130 }, (_, i) => ({
      issue: String(i + 1),
      date: new Date(Date.UTC(2025, 0, i + 1)).toISOString().slice(0, 10),
      number: String(i % 10).repeat(5),
    })),
    discovery: {
      ...defaultDiscovery,
      train: 80,
      validation: 20,
      calibration: 20,
      test: 10,
      budget: 3,
      pool: 16,
    },
  });
  return (
    <>
      <DiscoveryLab input={input} onChange={onChange} />
      <output data-testid="input">{JSON.stringify(input)}</output>
    </>
  );
}
it("runs real engine, loads and undoes; cancels stale output", () => {
  vi.stubGlobal("Worker", W);
  render(<H />);
  fireEvent.click(screen.getByRole("button", { name: "运行评分与集合实验" }));
  let w = W.all.at(-1)!;
  const result = analyzeDiscovery(w.request.input, w.request.config);
  act(() => w.onmessage({ data: { id: w.request.id, result } }));
  expect(screen.getByText(/DPP后不继承/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "载入实验预算集合" }));
  expect(
    JSON.parse(screen.getByTestId("input").textContent!).candidates,
  ).toHaveLength(3);
  fireEvent.click(screen.getByRole("button", { name: "撤销实验载入" }));
  expect(
    JSON.parse(screen.getByTestId("input").textContent!).candidates,
  ).toBeUndefined();
  fireEvent.click(screen.getByRole("button", { name: "运行评分与集合实验" }));
  w = W.all.at(-1)!;
  fireEvent.click(screen.getByRole("button", { name: "取消集合实验" }));
  act(() => w.onmessage({ data: { id: w.request.id, result } }));
  expect(w.dead).toBe(true);
  expect(screen.queryByRole("button", { name: "载入实验预算集合" })).toBeNull();
});
it("exposes all four modes, uncertainty settings and three-state evidence", () => {
  vi.stubGlobal("Worker", W);
  render(<H />);
  for (const value of ["joint", "gnn", "contrast", "uncertainty"]) {
    fireEvent.change(screen.getByLabelText("实验评分模型"), {
      target: { value },
    });
    expect(
      JSON.parse(screen.getByTestId("input").textContent!).discovery.model,
    ).toBe(value);
  }
  fireEvent.change(screen.getByLabelText("实际偏差δ"), {
    target: { value: ".03" },
  });
  fireEvent.click(screen.getByRole("button", { name: "运行评分与集合实验" }));
  const w = W.all.at(-1)!,
    result = analyzeDiscovery(w.request.input, w.request.config);
  act(() => w.onmessage({ data: { id: w.request.id, result } }));
  fireEvent.click(
    screen.getByText("位置数字不确定性（50项）", { exact: true }),
  );
  expect(screen.getByRole("table", { name: "后验三态决策" })).toBeTruthy();
  expect(result.uncertainty.delta).toBe(0.03);
});
