// @vitest-environment jsdom
import React, { useState } from "react";
import { afterEach, it, expect } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import AdvancedRules from "../src/components/AdvancedRules";
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
    candidates: ["00000", "01269", "12345"],
  });
  return (
    <>
      <AdvancedRules input={input} onChange={setInput} historySource="测试" />
      <output data-testid="numbers">{filter(input).numbers.join(",")}</output>
    </>
  );
}
it("adds AC and sorted-gap rules with correct preview and negative AC support", () => {
  render(<Harness />);
  fireEvent.click(screen.getByRole("button", { name: "添加条件" }));
  fireEvent.change(screen.getByLabelText("高级过滤规则"), {
    target: { value: "ac" },
  });
  fireEvent.change(screen.getByLabelText("高级规则允许值"), {
    target: { value: "-4" },
  });
  fireEvent.change(screen.getByLabelText("数学预览号码"), {
    target: { value: "00000" },
  });
  expect(screen.getByText("预览通过当前草稿")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "应用高级条件" }));
  expect(screen.getByTestId("numbers").textContent).toBe("00000");
  fireEvent.click(screen.getByRole("button", { name: "删除AC差值复杂度" }));
  fireEvent.click(screen.getByRole("button", { name: "添加条件" }));
  fireEvent.change(screen.getByLabelText("高级过滤规则"), {
    target: { value: "gapPattern" },
  });
  fireEvent.change(screen.getByLabelText("大间距下限"), {
    target: { value: "3" },
  });
  fireEvent.click(screen.getByRole("button", { name: "应用高级条件" }));
  expect(screen.getByTestId("numbers").textContent).toBe("01269");
});
