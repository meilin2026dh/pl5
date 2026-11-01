// @vitest-environment jsdom
import React from "react";
import { it, expect, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  cleanup,
  within,
} from "@testing-library/react";
import MarkovPreview from "../src/components/MarkovPreview";
import { defaultResearch } from "../src/domain/research/types";
afterEach(cleanup);
it("shows observed transition counts and a uniform posterior for unseen rows", () => {
  const history = [
    { issue: "1", date: "2026-01-01", number: "01234" },
    { issue: "2", date: "2026-01-02", number: "12345" },
  ];
  render(
    <MarkovPreview
      config={{ ...defaultResearch, window: 2, method: "markovScore" }}
      history={history}
    />,
  );
  const table = screen.getByRole("table", { name: "马尔可夫转移矩阵" });
  expect(within(table).getAllByRole("row")).toHaveLength(11);
  const unobserved = within(table).getAllByRole("row")[2];
  expect(
    within(unobserved)
      .getAllByRole("cell")
      .slice(1)
      .map((c) => c.textContent),
  ).toEqual(Array(10).fill("10.0%"));
  fireEvent.change(screen.getByLabelText("转移矩阵显示"), {
    target: { value: "counts" },
  });
  expect(within(table).getAllByRole("row")[1].textContent).toBe("00100000000");
  fireEvent.change(screen.getByLabelText("转移观察位置"), {
    target: { value: "4" },
  });
  expect(screen.getByText(/当前来源数字/).textContent).toContain("5");
});
