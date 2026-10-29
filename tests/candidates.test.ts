import { it, expect } from "vitest";
import { parseCandidates, setOperation } from "../src/lib/candidates";
it("validates input and deduplicates while preserving zeroes", () => {
  expect(parseCandidates("00127, 99999\n00127")).toEqual(["00127", "99999"]);
  expect(() => parseCandidates("127")).toThrow();
  expect(() => parseCandidates("")).toThrow();
});
it("performs directional set operations on real five-digit values", () => {
  const a = ["00000", "00127"],
    b = ["00127", "99999"];
  expect(setOperation(a, b, "intersection")).toEqual(["00127"]);
  expect(setOperation(a, b, "union")).toEqual(["00000", "00127", "99999"]);
  expect(setOperation(a, b, "difference")).toEqual(["00000"]);
  expect(setOperation(a, b, "symmetric")).toEqual(["00000", "99999"]);
});
