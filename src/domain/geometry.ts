import type { HistoryRecord } from "./pick5";
import { researchHistory } from "./research/statistics";
import { defaultResearch } from "./research/types";
export const geometryLabels = {
  line: "直线",
  polyline: "折线",
  v: "V型（先降后升）",
  invertedV: "倒V型（先升后降）",
  arithmetic: "等差规律",
  geometric: "等比规律",
  fibonacci: "斐波那契规律",
  triangle: "三角形点集",
  trapezoid: "梯形点集",
  mirror: "镜像对称",
  central: "中心对称",
} as const;
export type GeometryMethod = keyof typeof geometryLabels;
export type GeometryLayout = "trend" | "phone" | "calculator";
export type GeometryConfig = {
  method: GeometryMethod;
  layout: GeometryLayout;
  source: "number" | "history";
  length: number;
  position: number;
  referenceIssue?: string;
  sequence: "digits" | "gaps";
  axis: "vertical" | "horizontal";
  tolerance: number;
};
export const defaultGeometry: GeometryConfig = {
  method: "line",
  layout: "trend",
  source: "number",
  length: 5,
  position: 0,
  sequence: "digits",
  axis: "vertical",
  tolerance: 0,
};
export type Point = [number, number];
const epsilon = 1e-9;
const distance = (a: Point, b: Point) => Math.hypot(a[0] - b[0], a[1] - b[1]);
const cross = (a: Point, b: Point, c: Point) =>
  (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
export function validateGeometry(
  value: unknown,
): asserts value is GeometryConfig {
  if (!value || typeof value !== "object" || Array.isArray(value))
    throw new Error("空间形态参数格式错误");
  const c = value as GeometryConfig;
  if (
    !Object.hasOwn(geometryLabels, c.method) ||
    !["trend", "phone", "calculator"].includes(c.layout) ||
    !["number", "history"].includes(c.source) ||
    !["digits", "gaps"].includes(c.sequence) ||
    !["vertical", "horizontal"].includes(c.axis) ||
    !Number.isInteger(c.position) ||
    c.position < 0 ||
    c.position > 4 ||
    !Number.isInteger(c.length) ||
    c.length < 3 ||
    c.length > 5 ||
    (c.source === "number" && c.position + c.length > 5) ||
    typeof c.tolerance !== "number" ||
    !Number.isFinite(c.tolerance) ||
    c.tolerance < 0 ||
    c.tolerance > 0.25 ||
    (c.referenceIssue !== undefined &&
      (typeof c.referenceIssue !== "string" || !c.referenceIssue.trim()))
  )
    throw new Error("空间形态方法、坐标或参数不合法（容差0—0.25，位置0—4）");
  if (
    ["arithmetic", "geometric", "fibonacci"].includes(c.method) &&
    c.sequence === "gaps" &&
    c.length < 4
  )
    throw new Error("间距规律至少需要4个路径点（3个间距）");
}
export function geometryPoints(
  digits: number[],
  layout: GeometryLayout,
): Point[] {
  return digits.map((d, i) => {
    if (layout === "trend") return [i, 9 - d];
    if (d === 0) return [1, 3];
    return [
      (d - 1) % 3,
      layout === "phone"
        ? Math.floor((d - 1) / 3)
        : 2 - Math.floor((d - 1) / 3),
    ];
  });
}
function hull(points: Point[]): Point[] {
  const sorted = [
    ...new Map(points.map((p) => [p.join(","), p])).values(),
  ].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  if (sorted.length < 3) return sorted;
  const half = (rows: Point[]) => {
    const result: Point[] = [];
    for (const p of rows) {
      while (
        result.length >= 2 &&
        cross(result.at(-2)!, result.at(-1)!, p) <= epsilon
      )
        result.pop();
      result.push(p);
    }
    return result.slice(0, -1);
  };
  return [...half(sorted), ...half([...sorted].reverse())];
}
function straight(points: Point[], tolerance: number): boolean {
  const a = points[0],
    b = points.find((p) => distance(a, p) > epsilon);
  return (
    !!b &&
    points.every(
      (p) => Math.abs(cross(a, b, p)) / distance(a, b) <= tolerance + epsilon,
    )
  );
}
function recurrence(values: number[], c: GeometryConfig): boolean {
  const t = c.tolerance + epsilon;
  if (values.length < 3) return false;
  if (c.method === "arithmetic") {
    const step = values[1] - values[0];
    return values
      .slice(2)
      .every((v, i) => Math.abs(v - values[i + 1] - step) <= t);
  }
  if (c.method === "geometric") {
    if (values.some((v) => v <= epsilon)) return false;
    const ratio = values[1] / values[0];
    return (
      Math.abs(ratio - 1) > epsilon &&
      values.slice(2).every((v, i) => Math.abs(v - values[i + 1] * ratio) <= t)
    );
  }
  return (
    values.some((v) => Math.abs(v) > epsilon) &&
    values
      .slice(2)
      .every((v, i) => Math.abs(v - values[i] - values[i + 1]) <= t)
  );
}
function symmetric(points: Point[], c: GeometryConfig): boolean {
  if (new Set(points.map((p) => p.join(","))).size < 3) return false;
  const center: Point = [
    (Math.min(...points.map((p) => p[0])) +
      Math.max(...points.map((p) => p[0]))) /
      2,
    (Math.min(...points.map((p) => p[1])) +
      Math.max(...points.map((p) => p[1]))) /
      2,
  ];
  const targets = points.map((p) =>
    c.method === "central"
      ? ([2 * center[0] - p[0], 2 * center[1] - p[1]] as Point)
      : c.axis === "vertical"
        ? ([2 * center[0] - p[0], p[1]] as Point)
        : ([p[0], 2 * center[1] - p[1]] as Point),
  );
  // With at most five points, backtracking guarantees a one-to-one match under tolerance.
  function match(i: number, used: number): boolean {
    if (i === targets.length) return true;
    return points.some(
      (p, j) =>
        !(used & (1 << j)) &&
        distance(p, targets[i]) <= c.tolerance + epsilon &&
        match(i + 1, used | (1 << j)),
    );
  }
  return match(0, 0);
}
function matches(digits: number[], c: GeometryConfig): boolean {
  const points = geometryPoints(digits, c.layout);
  if (["arithmetic", "geometric", "fibonacci"].includes(c.method))
    return recurrence(
      c.sequence === "digits"
        ? digits
        : points.slice(1).map((p, i) => distance(points[i], p)),
      c,
    );
  if (c.method === "line") return straight(points, c.tolerance);
  if (c.method === "polyline")
    return (
      new Set(points.map((p) => p.join(","))).size >= 3 &&
      !straight(points, c.tolerance)
    );
  if (c.method === "v" || c.method === "invertedV") {
    const dx = points.slice(1).map((p, i) => p[0] - points[i][0]),
      dy = points.slice(1).map((p, i) => p[1] - points[i][1]);
    if (!dx.every((v) => v > epsilon) && !dx.every((v) => v < -epsilon))
      return false;
    if (dy.some((v) => Math.abs(v) <= c.tolerance + epsilon)) return false;
    const signs = dy.map((v) => Math.sign(v) * (c.method === "v" ? 1 : -1));
    const turn = signs.findIndex((v) => v < 0);
    return (
      turn > 0 &&
      signs.slice(0, turn).every((v) => v > 0) &&
      signs.slice(turn).every((v) => v < 0)
    );
  }
  if (c.method === "mirror" || c.method === "central")
    return symmetric(points, c);
  const boundary = hull(points);
  if (c.method === "triangle") return boundary.length === 3;
  if (boundary.length !== 4) return false;
  const parallel = (a: Point, b: Point, c1: Point, d: Point) => {
    const u: Point = [b[0] - a[0], b[1] - a[1]],
      v: Point = [d[0] - c1[0], d[1] - c1[1]];
    return (
      Math.abs(u[0] * v[1] - u[1] * v[0]) /
        (Math.hypot(...u) * Math.hypot(...v)) <=
      c.tolerance + epsilon
    );
  };
  return (
    parallel(boundary[0], boundary[1], boundary[2], boundary[3]) ||
    parallel(boundary[1], boundary[2], boundary[3], boundary[0])
  );
}
export function matchesGeometry(
  digits: number[],
  config: GeometryConfig,
): boolean {
  validateGeometry(config);
  if (
    digits.length < 3 ||
    digits.some((d) => !Number.isInteger(d) || d < 0 || d > 9)
  )
    throw new Error("空间路径需要至少三个0—9数字");
  return matches(digits, config);
}
export function geometryHistory(
  config: GeometryConfig,
  history?: HistoryRecord[],
): HistoryRecord[] {
  if (config.source !== "history") return [];
  return researchHistory(
    {
      ...defaultResearch,
      window: config.length - 1,
      referenceIssue: config.referenceIssue,
    },
    history,
  );
}
export function prepareGeometry(
  config: GeometryConfig,
  history?: HistoryRecord[],
) {
  validateGeometry(config);
  const rows = geometryHistory(config, history),
    prefix = rows.map((r) => Number(r.number[config.position]));
  return {
    digits: (number: string) =>
      config.source === "history"
        ? [...prefix, Number(number[config.position])]
        : [...number]
            .slice(config.position, config.position + config.length)
            .map(Number),
    test: (number: string) =>
      matches(
        config.source === "history"
          ? [...prefix, Number(number[config.position])]
          : [...number]
              .slice(config.position, config.position + config.length)
              .map(Number),
        config,
      ),
    diagnostics: {
      method: geometryLabels[config.method],
      layout: config.layout,
      source: config.source,
      position: config.position,
      length: config.length,
      sequence: config.sequence,
      tolerance: config.tolerance,
      axis: config.axis,
      firstIssue: rows[0]?.issue,
      lastIssue: rows.at(-1)?.issue,
    },
  };
}
