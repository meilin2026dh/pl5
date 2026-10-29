// @vitest-environment jsdom
import React from "react";
import { afterEach, beforeEach, describe, it, expect, vi } from "vitest";
import {
  render,
  screen,
  fireEvent,
  act,
  cleanup,
} from "@testing-library/react";
import Workbench from "../src/pages/Workbench";
import {
  filter,
  defaultPositions,
  defaultRules,
  type FilterInput,
} from "../src/domain/pick5";
class WorkerPort {
  static instances: WorkerPort[] = [];
  onmessage: ((event: { data: unknown }) => void) | null = null;
  onerror: (() => void) | null = null;
  requestId = 0;
  input: FilterInput | undefined;
  constructor() {
    WorkerPort.instances.push(this);
  }
  postMessage(message: { requestId: number; input: FilterInput }) {
    this.input = message.input;
    this.requestId = message.requestId;
  }
  terminate() {}
  reply() {
    this.onmessage?.({
      data: {
        requestId: this.requestId,
        result: filter(this.input!),
      },
    });
  }
}
function Harness() {
  const [input, setInput] = React.useState<FilterInput>({
    positions: defaultPositions(),
    rules: defaultRules().map((r) =>
      r.kind === "sum" ? { ...r, enabled: true, values: [0] } : r,
    ),
  });
  return (
    <Workbench
      input={input}
      setInput={setInput}
      onSave={() => {}}
      notify={() => {}}
    />
  );
}
beforeEach(() => {
  WorkerPort.instances = [];
  vi.stubGlobal("Worker", WorkerPort);
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
describe("calculation lifecycle", () => {
  it("displays a completed result and invalidates exports after input changes", () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole("button", { name: "开始缩水" }));
    expect(
      WorkerPort.instances[0].input?.rules.find((r) => r.kind === "sum")
        ?.values,
    ).toEqual([0]);
    act(() => WorkerPort.instances[0].reply());
    expect(screen.getByLabelText("过滤结果").textContent).toContain("00000");
    expect(
      (screen.getByRole("button", { name: "导出 TXT" }) as HTMLButtonElement)
        .disabled,
    ).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "万位号码0" }));
    expect(
      (screen.getByRole("button", { name: "导出 TXT" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
  });
  it("ignores replies from cancelled and obsolete tasks", () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole("button", { name: "开始缩水" }));
    const old = WorkerPort.instances[0];
    fireEvent.click(screen.getByRole("button", { name: "取消计算" }));
    act(() => old.reply());
    expect(screen.getByText("留一点空间，给好思路")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "开始缩水" }));
    const second = WorkerPort.instances[1];
    fireEvent.click(screen.getByRole("button", { name: "万位号码0" }));
    act(() => second.reply());
    expect(screen.getByText("留一点空间，给好思路")).toBeTruthy();
  });
});
