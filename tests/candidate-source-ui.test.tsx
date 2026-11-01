// @vitest-environment jsdom
import React, { useState } from "react";
import { afterEach, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import CandidateSource from "../src/components/CandidateSource";
import { defaultPositions, type FilterInput } from "../src/domain/pick5";
afterEach(cleanup);
function Harness() {
  const [input, setInput] = useState<FilterInput>({positions: defaultPositions(), rules: []});
  return <><CandidateSource input={input} onChange={setInput}/><div data-testid="loaded">{JSON.stringify(input.candidates ?? null)}</div></>;
}
it("opens and focuses the external candidate editor and reports empty input beside it", () => {
  render(<Harness/>);
  fireEvent.click(screen.getByRole("button", {name: "外部大底"}));
  const field = screen.getByLabelText("大底号码");
  expect(field.closest("details")?.open).toBe(true);
  expect(document.activeElement).toBe(field);
  fireEvent.click(screen.getByRole("button", {name: "载入大底"}));
  expect(screen.getByRole("alert").textContent).toContain("号码内容不能为空");
  expect(field.getAttribute("aria-invalid")).toBe("true");
});
it("restores the last loaded candidates after switching to positional mode", () => {
  render(<Harness/>);
  fireEvent.change(screen.getByLabelText("大底号码"), {target: {value: "00123 12345 00123"}});
  fireEvent.click(screen.getByRole("button", {name: "载入大底"}));
  expect(screen.getByRole("status").textContent).toContain("2组");
  fireEvent.click(screen.getByRole("button", {name: "定位复式"}));
  expect(screen.getByRole("status").textContent).toContain("定位复式");
  fireEvent.click(screen.getByRole("button", {name: "外部大底"}));
  expect(screen.getByRole("status").textContent).toContain("2组");
  expect(screen.getByRole("status").textContent).not.toContain("粘贴或导入");
  expect(screen.getByText('["00123","12345"]')).toBeTruthy();
});
