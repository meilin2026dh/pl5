import { describe, it, expect } from "vitest";
import { decodePlans, encodePlan, type Plan } from "../src/lib/plans";
const sample: Plan = {
  id: "a",
  name: "我的方案",
  createdAt: "2026-10-18T14:00:00Z",
  input: { positions: [[0], [0], [1], [2], [7]], rules: [] },
};
describe("saved plans boundary", () => {
  it("restores a five-digit input without losing zero positions", () => {
    expect(
      decodePlans(JSON.stringify({ schemaVersion: 1, plans: [sample] })),
    ).toEqual([sample]);
  });
  it("rejects incompatible or corrupted storage without hiding the error", () => {
    expect(() => decodePlans("{")).toThrow();
    expect(() => decodePlans('{"schemaVersion":99,"plans":[]}')).toThrow();
  });
  it("rejects malformed selections and rules before they reach worker", () => {
    expect(() =>
      decodePlans(
        JSON.stringify({
          schemaVersion: 1,
          plans: [{ ...sample, input: { positions: [[10]], rules: [] } }],
        }),
      ),
    ).toThrow();
  });
  it("encodes a detached snapshot instead of a mutable reference", () => {
    const p = encodePlan("清爽方案", sample.input);
    sample.input.positions[0].push(4);
    expect(p.input.positions[0]).toEqual([0]);
  });
});
