// @vitest-environment jsdom
import React, { useState } from "react";
import { it, expect, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import GeometryRules from "../src/components/GeometryRules";
import {
  defaultPositions,
  filter,
  type FilterInput,
} from "../src/domain/pick5";
afterEach(cleanup);
function Harness() {
  const [input, setInput] = useState<FilterInput>({
    positions: defaultPositions(),
    rules: [],
    candidates: ["95159", "13579", "15951"],
  });
  return (
    <>
      <GeometryRules input={input} onChange={setInput} />
      <button onClick={() => setInput({ ...input, rules: [] })}>
        清空全部测试条件
      </button>
      <div data-testid="result">
        {JSON.stringify(input.rules.length ? filter(input).numbers : [])}
      </div>
    </>
  );
}
it("adds an actual V filter, previews, edits, toggles and deletes it", () => {
  render(<Harness />);
  fireEvent.click(screen.getByRole("button", { name: "添加空间条件" }));
  fireEvent.change(screen.getByLabelText("空间方法"), {
    target: { value: "v" },
  });
  fireEvent.change(screen.getByLabelText("预览五位号码"), {
    target: { value: "95159" },
  });
  expect(screen.getByText("预览符合此条件")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "保存空间条件" }));
  expect(screen.getByTestId("result").textContent).toBe('["95159"]');
  fireEvent.click(screen.getByRole("button", { name: "编辑空间条件 V型" }));
  fireEvent.change(screen.getByLabelText("空间模式"), {
    target: { value: "exclude" },
  });
  fireEvent.click(screen.getByRole("button", { name: "保存空间条件" }));
  expect(screen.getByTestId("result").textContent).toBe('["13579","15951"]');
  fireEvent.click(screen.getByRole("checkbox", { name: "启用空间条件 V型" }));
  expect(screen.getByTestId("result").textContent).toBe(
    '["13579","15951","95159"]',
  );
  fireEvent.click(screen.getByRole("button", { name: "删除空间条件 V型" }));
  expect(screen.queryByRole("button", { name: "编辑空间条件 V型" })).toBeNull();
});
it("invalidates an open draft if its source rule is removed", () => {
  render(<Harness />);
  fireEvent.click(screen.getByRole("button", { name: "添加空间条件" }));
  fireEvent.click(screen.getByRole("button", { name: "保存空间条件" }));
  fireEvent.click(screen.getByRole("button", { name: "编辑空间条件 直线" }));
  fireEvent.click(screen.getByRole("button", { name: "清空全部测试条件" }));
  expect(screen.queryByRole("button", { name: "保存空间条件" })).toBeNull();
  expect(screen.getByRole("alert").textContent).toContain("改变或移除");
});
