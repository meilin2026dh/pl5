// @vitest-environment jsdom
import React, { useState } from "react";
import { it, expect, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  cleanup,
  within,
} from "@testing-library/react";
import PeriodRelations from "../src/components/PeriodRelations";
import {
  defaultPositions,
  filter,
  type FilterInput,
} from "../src/domain/pick5";
afterEach(cleanup);
const rows = Array.from({ length: 8 }, (_, i) => ({
  issue: String(i + 1),
  date: `2026-01-0${i + 1}`,
  number: i % 2 ? "20000" : "10000",
}));
function Harness() {
  const [input, setInput] = useState<FilterInput>({
    positions: defaultPositions(),
    rules: [],
    history: rows,
    historySource: "测试历史",
    candidates: ["10000", "20000"],
  });
  return (
    <>
      <PeriodRelations input={input} onChange={setInput} />
      <div data-testid="result">
        {JSON.stringify(input.rules.length ? filter(input).numbers : [])}
      </div>
      <button onClick={() => setInput({ ...input, rules: [] })}>
        清空测试条件
      </button>
    </>
  );
}
it("shows actual lag repeats and indicator history, then adds/edits/disables/deletes a real filter", () => {
  render(<Harness />);
  fireEvent.change(screen.getByLabelText("跨期窗口"), {
    target: { value: "4" },
  });
  const lag = screen.getByRole("table", { name: "跨期滞后对照" });
  expect(within(lag).getAllByText(/100.0%/).length).toBeGreaterThan(0);
  fireEvent.click(screen.getByRole("button", { name: "使用滞后2期" }));
  expect(
    (screen.getByLabelText("跨期滞后期数") as HTMLInputElement).value,
  ).toBe("2");
  fireEvent.click(screen.getByRole("button", { name: "添加关联条件" }));
  expect(screen.getByTestId("result").textContent).toBe('["10000"]');
  fireEvent.click(
    screen.getByRole("button", { name: "编辑跨期条件 重号周期" }),
  );
  fireEvent.change(screen.getByLabelText("跨期规则模式"), {
    target: { value: "exclude" },
  });
  fireEvent.click(screen.getByRole("button", { name: "保存关联条件" }));
  expect(screen.getByTestId("result").textContent).toBe('["20000"]');
  fireEvent.click(
    screen.getByRole("checkbox", { name: "启用跨期条件 重号周期" }),
  );
  expect(screen.getByTestId("result").textContent).toBe('["10000","20000"]');
  fireEvent.click(
    screen.getByRole("button", { name: "删除跨期条件 重号周期" }),
  );
  expect(
    screen.queryByRole("button", { name: "编辑跨期条件 重号周期" }),
  ).toBeNull();
});
it("changes metrics and learns an observed pattern with an explicit cutoff", () => {
  render(<Harness />);
  fireEvent.change(screen.getByLabelText("跨期窗口"), {
    target: { value: "4" },
  });
  fireEvent.change(screen.getByLabelText("跨期参考期"), {
    target: { value: "6" },
  });
  fireEvent.change(screen.getByLabelText("跨期滞后期数"), {
    target: { value: "2" },
  });
  fireEvent.change(screen.getByLabelText("跨期过滤依据"), {
    target: { value: "historical" },
  });
  fireEvent.change(screen.getByLabelText("跨期最低比例"), {
    target: { value: "100" },
  });
  expect(screen.getByText("保留分数：1")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "添加关联条件" }));
  expect(screen.getByTestId("result").textContent).toBe('["10000"]');
  fireEvent.change(screen.getByLabelText("跨期观察指标"), {
    target: { value: "sum" },
  });
  expect(screen.getByRole("img", { name: "跨期指标历史折线" })).toBeTruthy();
});
it("reports insufficient history and invalidates an edit after its rule is removed", () => {
  render(<Harness />);
  fireEvent.change(screen.getByLabelText("跨期滞后期数"), {
    target: { value: "20" },
  });
  fireEvent.click(screen.getByRole("button", { name: "添加关联条件" }));
  expect(screen.getByRole("alert").textContent).toContain("历史不足");
  fireEvent.change(screen.getByLabelText("跨期滞后期数"), {
    target: { value: "2" },
  });
  fireEvent.click(screen.getByRole("button", { name: "添加关联条件" }));
  fireEvent.click(
    screen.getByRole("button", { name: "编辑跨期条件 重号周期" }),
  );
  fireEvent.click(screen.getByRole("button", { name: "清空测试条件" }));
  expect(screen.getByRole("alert").textContent).toContain("改变或移除");
  expect(screen.queryByRole("button", { name: "保存关联条件" })).toBeNull();
});
