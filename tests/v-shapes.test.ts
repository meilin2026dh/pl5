import { expect, it } from "vitest";
import {
  defaultGeometry,
  matchesGeometry,
  type GeometryLayout,
} from "../src/domain/geometry";
const shape = (
  digits: number[],
  method: "v" | "invertedV",
  layout: GeometryLayout = "trend",
) =>
  matchesGeometry(digits, {
    ...defaultGeometry,
    method,
    layout,
    length: digits.length,
  });
// An independent digit-sequence oracle, rather than reusing screen-coordinate turns.
function valley(d: number[]): boolean {
  return Array.from({ length: d.length - 2 }, (_, i) => i + 1).some(
    (p) =>
      d.slice(1, p + 1).every((v, i) => d[i] > v) &&
      d.slice(p + 1).every((v, i) => d[p + i] < v),
  );
}
it("agrees with independent valley/peak definitions for all 100000 ordered numbers", () => {
  let v = 0,
    peak = 0,
    overlap = 0;
  for (let n = 0; n < 100000; n++) {
    const d = [...String(n).padStart(5, "0")].map(Number);
    const a = shape(d, "v"),
      b = shape(d, "invertedV");
    if (a !== valley(d) || b !== valley(d.map((x) => 9 - x)))
      throw new Error(`shape mismatch ${n}`);
    v += Number(a);
    peak += Number(b);
    overlap += Number(a && b);
  }
  expect({ v, peak, overlap }).toEqual({ v: 6168, peak: 6168, overlap: 0 });
});
it("handles all turn positions, unequal arms, zeroes, flats and multiple turns", () => {
  for (const d of [
    [2, 1, 0, 1, 2],
    [9, 0, 1, 2, 3],
    [9, 8, 7, 0, 1],
    [9, 7, 0, 1, 8],
  ])
    expect(shape(d, "v")).toBe(true);
  for (const d of [
    [0, 1, 2, 3, 4],
    [4, 3, 2, 1, 0],
    [2, 1, 0, 0, 1],
    [2, 1, 2, 1, 2],
    [1, 1, 1, 1, 1],
  ])
    expect(shape(d, "v")).toBe(false);
});
it("recognizes a visible five-point keyboard V with vertical sections on its arms", () => {
  expect(shape([1, 4, 8, 6, 3], "v", "phone")).toBe(true);
  expect(shape([1, 4, 8, 6, 3], "invertedV", "phone")).toBe(false);
  expect(shape([7, 4, 2, 6, 9], "invertedV", "phone")).toBe(true);
  expect(shape([1, 4, 8, 6, 3], "invertedV", "calculator")).toBe(true);
  expect(shape([1, 4, 8, 6, 3], "v", "calculator")).toBe(false);
});
it("allows either traversal direction but rejects vertical folds, horizontal bottoms and lateral backtracking", () => {
  expect(shape([3, 6, 8, 4, 1], "v", "phone")).toBe(true);
  for (const d of [
    [1, 4, 7, 4, 1],
    [1, 7, 8, 9, 3],
    [1, 5, 7, 5, 3],
  ])
    expect(shape(d, "v", "phone")).toBe(false);
});
it("keeps V and inverted V disjoint for every keypad candidate and makes both selectable", () => {
  for (const layout of ["phone", "calculator"] as const) {
    let v = 0,
      p = 0,
      overlap = 0;
    for (let n = 0; n < 100000; n++) {
      const d = [...String(n).padStart(5, "0")].map(Number),
        a = shape(d, "v", layout),
        b = shape(d, "invertedV", layout);
      v += Number(a);
      p += Number(b);
      overlap += Number(a && b);
    }
    expect(v).toBeGreaterThan(0);
    expect(p).toBeGreaterThan(0);
    expect(overlap).toBe(0);
  }
});
it("supports three/four points and requires width on each individual arm", () => {
  for (const d of [
    [1, 8, 3],
    [1, 4, 8, 3],
    [1, 8, 6, 3],
  ])
    expect(shape(d, "v", "phone")).toBe(true);
  for (const d of [
    [1, 4, 7, 6],
    [1, 8, 5, 2],
  ])
    expect(shape(d, "v", "phone")).toBe(false);
});
