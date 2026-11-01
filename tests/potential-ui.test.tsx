// @vitest-environment jsdom
import React, { useState } from "react";
import { it, expect, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import ResearchRules from "../src/components/ResearchRules";
import { defaultPositions, type FilterInput } from "../src/domain/pick5";
import { prepareResearch } from "../src/domain/research";
import { decodePlans, encodePlan } from "../src/lib/plans";
afterEach(cleanup);
const history = [
  "00000",
  "11111",
  "00000",
  "00000",
  "11111",
  "11111",
  "00000",
  "00000",
].map((number, i) => ({
  issue: String(i + 1),
  date: `2026-01-0${i + 1}`,
  number,
}));
function Harness() {
  const [input, setInput] = useState<FilterInput>({
    positions: defaultPositions(),
    history,
    historySource: "固定周期算例",
    rules: [],
  });
  return (
    <>
      <ResearchRules input={input} onChange={setInput} />
      <output data-testid="saved">{JSON.stringify(input.rules)}</output>
      <button
        onClick={() => {
          const p = encodePlan("势能", input);
          setInput(
            decodePlans(JSON.stringify({ schemaVersion: 1, plans: [p] }))[0]
              .input,
          );
        }}
      >
        测试方案恢复
      </button>
    </>
  );
}
function setup() {
  fireEvent.click(screen.getByRole("button", { name: "添加实验方法" }));
  fireEvent.change(screen.getByRole("combobox", { name: "实验方法" }), {
    target: { value: "potential" },
  });
  fireEvent.change(screen.getByLabelText("历史窗口（期）"), {
    target: { value: "8" },
  });
  fireEvent.change(screen.getByLabelText("势能短窗"), {
    target: { value: "2" },
  });
  fireEvent.change(screen.getByLabelText("势能分窗数"), {
    target: { value: "3" },
  });
  fireEvent.change(screen.getByLabelText("势能灵敏带"), {
    target: { value: "0.1" },
  });
}
it("shows known alternating states and saves, restores, edits, disables and deletes the real model", () => {
  render(<Harness />);
  setup();
  expect(
    screen.getByRole("table", { name: "冷热势能观察" }).textContent,
  ).toContain("热→冷→热");
  expect(
    screen.getByRole("table", { name: "冷热势能观察" }).textContent,
  ).toContain("升温越界");
  fireEvent.change(screen.getByLabelText("势能侧重"), {
    target: { value: "warming" },
  });
  fireEvent.change(screen.getByLabelText("并列策略"), {
    target: { value: "seeded" },
  });
  fireEvent.change(screen.getByLabelText("保留比例（%）"), {
    target: { value: "1" },
  });
  fireEvent.click(screen.getByRole("button", { name: "保存实验条件" }));
  const saved = JSON.parse(screen.getByTestId("saved").textContent!)[0];
  expect(prepareResearch(saved.research, history).diagnostics.actualCount).toBe(
    1000,
  );
  fireEvent.click(screen.getByRole("button", { name: "测试方案恢复" }));
  fireEvent.click(
    screen.getByRole("button", { name: "编辑 冷热势能动态评分" }),
  );
  expect((screen.getByLabelText("势能侧重") as HTMLSelectElement).value).toBe(
    "warming",
  );
  fireEvent.change(screen.getByLabelText("规则模式"), {
    target: { value: "exclude" },
  });
  fireEvent.click(screen.getByRole("button", { name: "保存实验条件" }));
  expect(JSON.parse(screen.getByTestId("saved").textContent!)[0].mode).toBe(
    "exclude",
  );
  fireEvent.click(screen.getByRole("checkbox", { name: "冷热势能动态评分" }));
  expect(JSON.parse(screen.getByTestId("saved").textContent!)[0].enabled).toBe(
    false,
  );
  fireEvent.click(
    screen.getByRole("button", { name: "删除 冷热势能动态评分" }),
  );
  expect(screen.getByTestId("saved").textContent).toBe("[]");
});
it("rejects insufficient history in the editor instead of saving a shortened model", () => {
  render(<Harness />);
  setup();
  fireEvent.change(screen.getByLabelText("势能分窗数"), {
    target: { value: "4" },
  });
  fireEvent.click(screen.getByRole("button", { name: "保存实验条件" }));
  expect(screen.getByRole("alert").textContent).toContain("历史不足");
  expect(screen.getByTestId("saved").textContent).toBe("[]");
});
