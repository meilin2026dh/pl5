import { defaultResearch } from "../src/domain/research/types";
// @vitest-environment jsdom
import React from "react";
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import ResearchRules, {
  ResearchDiagnosticsView,
} from "../src/components/ResearchRules";
import { defaultPositions, type FilterInput } from "../src/domain/pick5";
afterEach(cleanup);
const base: FilterInput = {
  positions: defaultPositions(),
  rules: [],
  historySource: "测试历史",
  history: Array.from({ length: 150 }, (_, i) => ({
    issue: String(i),
    date: new Date(Date.UTC(2026, 0, i + 1)).toISOString().slice(0, 10),
    number: "12345",
  })),
  candidates: ["12345"],
};
it("saves exact configured payload and restores seed, mode and full input when editing", () => {
  const onChange = vi.fn();
  const { rerender } = render(
    <ResearchRules input={base} onChange={onChange} />,
  );
  fireEvent.click(screen.getByRole("button", { name: "添加实验方法" }));
  fireEvent.change(screen.getByRole("combobox", { name: "实验方法" }), {
    target: { value: "bma" },
  });
  fireEvent.change(screen.getByLabelText("并列策略"), {
    target: { value: "seeded" },
  });
  fireEvent.change(screen.getByLabelText("随机种子"), {
    target: { value: "42" },
  });
  fireEvent.change(screen.getByLabelText("保留比例（%）"), {
    target: { value: "12" },
  });
  fireEvent.change(screen.getByLabelText("规则模式"), {
    target: { value: "exclude" },
  });
  fireEvent.click(screen.getByRole("button", { name: "保存实验条件" }));
  const next = onChange.mock.calls[0][0];
  expect(next.candidates).toEqual(["12345"]);
  expect(next.rules[0]).toMatchObject({
    kind: "research",
    enabled: true,
    mode: "exclude",
    research: { method: "bma", seed: 42, retain: 0.12, ties: "seeded" },
  });
  rerender(<ResearchRules input={next} onChange={onChange} />);
  fireEvent.click(screen.getByRole("button", { name: "编辑 BMA七模型平均" }));
  expect((screen.getByLabelText("随机种子") as HTMLInputElement).value).toBe(
    "42",
  );
  expect((screen.getByLabelText("规则模式") as HTMLSelectElement).value).toBe(
    "exclude",
  );
});
it("rejects invalid parameters before updating input", () => {
  const onChange = vi.fn();
  render(<ResearchRules input={base} onChange={onChange} />);
  fireEvent.click(screen.getByRole("button", { name: "添加实验方法" }));
  fireEvent.change(screen.getByLabelText("方法参数"), {
    target: { value: "11" },
  });
  fireEvent.click(screen.getByRole("button", { name: "保存实验条件" }));
  expect(screen.getByRole("alert").textContent).toContain("Top K");
  expect(onChange).not.toHaveBeenCalled();
});
it("renders bounded readable diagnostics", () => {
  render(
    <ResearchDiagnosticsView
      items={[
        {
          id: "x",
          label: "BMA",
          diagnostics: {
            weights: { uniform: 0.5 },
            selected: { parameter: 7 },
            folds: [{ coverage: 0.8 }],
          },
        },
      ]}
    />,
  );
  expect(screen.getByText("BMA")).toBeTruthy();
  expect(screen.getByText("uniform")).toBeTruthy();
});
it("preserves a checkbox change while editing and never resurrects a removed rule", () => {
  const rule: FilterInput["rules"][number] = {
    id: "existing",
    kind: "research",
    enabled: true,
    mode: "include",
    values: [],
    research: { ...defaultResearch },
  };
  const onChange = vi.fn();
  const { rerender } = render(
    <ResearchRules input={{ ...base, rules: [rule] }} onChange={onChange} />,
  );
  fireEvent.click(screen.getByRole("button", { name: "编辑 逐位冷热Top K" }));
  rerender(
    <ResearchRules
      input={{ ...base, rules: [{ ...rule, enabled: false }] }}
      onChange={onChange}
    />,
  );
  fireEvent.click(screen.getByText("保存实验条件"));
  expect(onChange.mock.calls[0][0].rules[0].enabled).toBe(false);
  rerender(
    <ResearchRules input={{ ...base, rules: [rule] }} onChange={onChange} />,
  );
  fireEvent.click(screen.getByRole("button", { name: "编辑 逐位冷热Top K" }));
  rerender(
    <ResearchRules input={{ ...base, rules: [] }} onChange={onChange} />,
  );
  const save = screen.queryByText("保存实验条件");
  if (save) fireEvent.click(save);
  expect(onChange).toHaveBeenCalledTimes(1);
});
