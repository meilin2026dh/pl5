// @vitest-environment jsdom
import React from "react";
import { afterEach, it, expect } from "vitest";
import {
  render,
  screen,
  fireEvent,
  cleanup,
  act,
} from "@testing-library/react";
import CandidateSource from "../src/components/CandidateSource";
import { defaultPositions, type FilterInput } from "../src/domain/pick5";
afterEach(cleanup);
function Harness() {
  const [input, setInput] = React.useState<FilterInput>({
    positions: defaultPositions(),
    rules: [],
    candidates: ["00127"],
  });
  return <CandidateSource input={input} onChange={setInput} />;
}
it("invalidates a set preview after source A changes", () => {
  render(<Harness />);
  fireEvent.click(screen.getByText("集合运算：当前大底为A，另输入B"));
  fireEvent.change(screen.getByLabelText("集合B号码"), {
    target: { value: "00127" },
  });
  fireEvent.click(screen.getByRole("button", { name: "预览集合结果" }));
  expect(screen.getByText("结果共1组")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("大底号码"), {
    target: { value: "99999" },
  });
  fireEvent.click(screen.getByRole("button", { name: "载入大底" }));
  expect(screen.queryByText("结果共1组")).toBeNull();
});
