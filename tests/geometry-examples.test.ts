import { it, expect } from "vitest";
import {
  defaultGeometry,
  geometryLabels,
  prepareGeometry,
} from "../src/domain/geometry";
import { geometryExample } from "../src/domain/geometryExamples";
it("provides actual matching examples for all default methods in every layout", () => {
  for (const method of Object.keys(
    geometryLabels,
  ) as (keyof typeof geometryLabels)[]) {
    for (const layout of ["trend", "phone", "calculator"] as const) {
      const c = {
        ...defaultGeometry,
        method,
        layout,
        length: method === "geometric" ? 3 : 5,
      };
      const example = geometryExample(c);
      expect(example, `${method}/${layout}`).toMatch(/^\d{5}$/);
      expect(prepareGeometry(c).test(example!)).toBe(true);
    }
  }
});
it("does not invent a positive example for impossible or invalid parameters", () => {
  expect(
    geometryExample({ ...defaultGeometry, method: "trapezoid", length: 3 }),
  ).toBeNull();
  expect(
    geometryExample({ ...defaultGeometry, method: "geometric" }),
  ).toBeNull();
  expect(geometryExample({ ...defaultGeometry, tolerance: NaN })).toBeNull();
});
it("respects selected subpaths and only generates continuations of supplied history", () => {
  const c = {
    ...defaultGeometry,
    method: "v" as const,
    length: 3,
    position: 2,
  };
  const example = geometryExample(c);
  expect(example).toMatch(/^00\d{3}$/);
  expect(prepareGeometry(c).test(example!)).toBe(true);
  const history = [
    { issue: "1", date: "2026-01-01", number: "30000" },
    { issue: "2", date: "2026-01-02", number: "10000" },
  ];
  const h = {
    ...defaultGeometry,
    method: "v" as const,
    length: 3,
    source: "history" as const,
  };
  expect(geometryExample(h, history)).toBe("20000");
  expect(geometryExample(h, history.slice(0, 1))).toBeNull();
});
