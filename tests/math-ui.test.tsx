// @vitest-environment jsdom
import React, { useState } from "react";
import { it, expect, afterEach } from "vitest";
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
    candidates: ["12345", "54321", "00000", "02468", "89000"],
    rules: [],
  });
  return (
    <>
      <AdvancedRules input={input} onChange={setInput} historySource="测试" />
      <output data-testid="numbers">{filter(input).numbers.join(",")}</output>
    </>
  );
}
function open(kind: string) {
  fireEvent.click(
    screen.getByRole("button", { name: /^添加条件$/ }),
  );
  fireEvent.change(screen.getByLabelText("高级过滤规则"), {
    target: { value: kind },
  });
}
it("adds inverse-number filters, edits to exclude, disables and deletes", () => {
  render(<Harness />);
  open("inversions");
  fireEvent.change(screen.getByLabelText("数学预览号码"), {
    target: { value: "54321" },
  });
  expect(screen.getByLabelText("数学特征预览").textContent).toContain(
    "逆序数 10",
  );
  fireEvent.change(screen.getByLabelText("高级规则允许值"), {
    target: { value: "10" },
  });
  expect(screen.getByText("预览通过当前草稿")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "应用高级条件" }));
  expect(screen.getByTestId("numbers").textContent).toBe("54321");
  fireEvent.click(screen.getByRole("button", { name: "编辑排列逆序数" }));
  fireEvent.change(screen.getByLabelText("筛选模式"), {
    target: { value: "exclude" },
  });
  fireEvent.click(screen.getByRole("button", { name: "应用高级条件" }));
  expect(screen.getByTestId("numbers").textContent).not.toContain("54321");
  fireEvent.click(screen.getByRole("checkbox", { name: "排列逆序数" }));
  expect(screen.getByTestId("numbers").textContent).toContain("54321");
  fireEvent.click(screen.getByRole("button", { name: "删除排列逆序数" }));
  expect(screen.queryByRole("button", { name: "编辑排列逆序数" })).toBeNull();
});
it("supports custom sum modulus and validates values against it", () => {
  render(<Harness />);
  open("sumModulo");
  fireEvent.change(screen.getByLabelText("和值取模模数"), {
    target: { value: "7" },
  });
  fireEvent.change(screen.getByLabelText("高级规则允许值"), {
    target: { value: "1" },
  });
  fireEvent.click(screen.getByRole("button", { name: "应用高级条件" }));
  expect(screen.getByTestId("numbers").textContent).toBe("12345,54321");
  fireEvent.click(screen.getByRole("button", { name: "编辑和值取模" }));
  fireEvent.change(screen.getByLabelText("高级规则允许值"), {
    target: { value: "7" },
  });
  fireEvent.click(screen.getByRole("button", { name: "应用高级条件" }));
  expect(screen.getByRole("alert").textContent).toContain("范围");
});
it("adds mathematical patterns and position-pair lcm with live preview", () => {
  render(<Harness />);
  open("mathPrimePattern");
  fireEvent.change(screen.getByLabelText("高级规则允许值"), {
    target: { value: "NNCCC" },
  });
  fireEvent.change(screen.getByLabelText("数学预览号码"), {
    target: { value: "02468" },
  });
  expect(screen.getByLabelText("数学特征预览").textContent).toContain("PCCC");
  fireEvent.change(screen.getByLabelText("高级规则允许值"), {
    target: { value: "NPCCC" },
  });
  fireEvent.click(screen.getByRole("button", { name: "应用高级条件" }));
  expect(screen.getByTestId("numbers").textContent).toBe("02468");
  fireEvent.click(screen.getByRole("button", { name: "删除数学质合形态" }));
  open("pairLcm");
  fireEvent.change(screen.getByLabelText("位置组合"), {
    target: { value: "0,1" },
  });
  fireEvent.change(screen.getByLabelText("高级规则允许值"), {
    target: { value: "72" },
  });
  fireEvent.click(screen.getByRole("button", { name: "应用高级条件" }));
  expect(screen.getByTestId("numbers").textContent).toBe("89000");
});
