import { metrics, type HistoryRecord } from "./pick5";
import { researchHistory } from "./research/statistics";
import { defaultResearch } from "./research/types";
export const relationLabels = {
  repeat: "重号周期",
  neighbor: "邻号传递",
  mirror: "隔期镜像",
  inherit: "数字遗传延续",
  delta: "指标变化差值",
} as const;
export const relationMetricLabels = {
  position: "指定位置数字",
  sum: "和值",
  span: "跨度",
  tail: "和尾",
  odd: "奇数个数",
  big: "大数个数",
  prime: "质类个数",
  distinct: "不同数字个数",
} as const;
export type RelationConfig = {
  method: keyof typeof relationLabels;
  metric: keyof typeof relationMetricLabels;
  scope: "indicator" | "positions";
  position: number;
  previousPosition: number;
  lag: number;
  depth: number;
  window: number;
  referenceIssue?: string;
  strategy: "range" | "historical";
  min: number;
  max: number;
  minSupport: number;
  mirror: "nine" | "five";
};
export const defaultRelation: RelationConfig = {
  method: "repeat",
  metric: "position",
  scope: "indicator",
  position: 0,
  previousPosition: 0,
  lag: 1,
  depth: 5,
  window: 100,
  strategy: "range",
  min: 1,
  max: 1,
  minSupport: 0.05,
  mirror: "nine",
};
const integer = (n: unknown, a: number, b: number) =>
  typeof n === "number" && Number.isInteger(n) && n >= a && n <= b;
export function validateRelation(
  value: unknown,
): asserts value is RelationConfig {
  if (!value || typeof value !== "object" || Array.isArray(value))
    throw new Error("跨期关联参数格式错误");
  const c = value as RelationConfig;
  const max =
    c.method === "inherit" && c.scope === "indicator"
      ? c.depth
      : c.scope === "positions"
        ? 5
        : 1;
  if (
    !Object.hasOwn(relationLabels, c.method) ||
    !Object.hasOwn(relationMetricLabels, c.metric) ||
    !["indicator", "positions"].includes(c.scope) ||
    !integer(c.position, 0, 4) ||
    !integer(c.previousPosition, 0, 4) ||
    !integer(c.lag, 1, 60) ||
    !integer(c.depth, 1, 60) ||
    !integer(c.window, 3, 1000) ||
    !["range", "historical"].includes(c.strategy) ||
    !["nine", "five"].includes(c.mirror) ||
    !integer(
      c.min,
      c.method === "delta" ? -45 : 0,
      c.method === "delta" ? 45 : max,
    ) ||
    !integer(c.max, c.min, c.method === "delta" ? 45 : max) ||
    typeof c.minSupport !== "number" ||
    !Number.isFinite(c.minSupport) ||
    c.minSupport < 0 ||
    c.minSupport > 1 ||
    (c.referenceIssue !== undefined &&
      (typeof c.referenceIssue !== "string" || !c.referenceIssue.trim()))
  )
    throw new Error("跨期关联方法、窗口、位置或取值范围不合法");
  if (
    c.scope === "positions" &&
    (c.metric !== "position" || c.method === "delta")
  )
    throw new Error("逐位模式仅支持数字关联，不支持指标差值");
  if (c.method === "mirror" && c.metric !== "position")
    throw new Error("镜像映射仅用于数字，请选择位置数字");
}
export function relationHistory(
  c: RelationConfig,
  history?: HistoryRecord[],
): HistoryRecord[] {
  const last = researchHistory(
    { ...defaultResearch, window: 1, referenceIssue: c.referenceIssue },
    history,
  )[0];
  return history!
    .filter((r) => r.date <= last.date)
    .sort((a, b) => a.date.localeCompare(b.date));
}
export const relationValue = (
  number: string,
  c: RelationConfig,
  previous = false,
): number =>
  c.metric === "position"
    ? Number(number[previous ? c.previousPosition : c.position])
    : metrics(number)[c.metric];
const mirrored = (n: number, c: RelationConfig) =>
  c.mirror === "nine" ? 9 - n : (n + 5) % 10;
const related = (a: number, b: number, c: RelationConfig) =>
  c.method === "neighbor"
    ? Math.abs(a - b) === 1
    : c.method === "mirror"
      ? a === mirrored(b, c)
      : a === b;
function lookback(c: RelationConfig) {
  return c.method === "inherit" ? c.depth : c.lag;
}
function scorerAt(
  rows: HistoryRecord[],
  end: number,
  c: RelationConfig,
): (number: string) => number {
  if (end < lookback(c)) throw new Error("历史不足：跨期关联缺少所需滞后记录");
  if (c.method === "inherit") {
    const prior = rows.slice(end - c.depth, end);
    if (c.scope === "positions") {
      const sets = Array.from(
        { length: 5 },
        (_, p) => new Set(prior.map((r) => r.number[p])),
      );
      return (number) => [...number].filter((d, p) => sets[p].has(d)).length;
    }
    const frequencies = new Map<number, number>();
    for (const r of prior) {
      const value = relationValue(r.number, c, true);
      frequencies.set(value, (frequencies.get(value) || 0) + 1);
    }
    return (number) => frequencies.get(relationValue(number, c)) || 0;
  }
  const previous = rows[end - c.lag].number;
  if (c.scope === "positions")
    return (number) =>
      [...number].filter((d, p) => related(Number(d), Number(previous[p]), c))
        .length;
  const b = relationValue(previous, c, true);
  return (number) => {
    const a = relationValue(number, c);
    return c.method === "delta" ? a - b : Number(related(a, b, c));
  };
}
export function prepareRelation(c: RelationConfig, history?: HistoryRecord[]) {
  validateRelation(c);
  const rows = relationHistory(c, history),
    needed = lookback(c) + (c.strategy === "historical" ? c.window : 0);
  if (rows.length < needed)
    throw new Error(
      `历史不足：需要至少${needed}期，截止参考期仅有${rows.length}期`,
    );
  const distribution = new Map<number, number>();
  if (c.strategy === "historical")
    for (let i = rows.length - c.window; i < rows.length; i++) {
      const score = scorerAt(rows, i, c)(rows[i].number);
      distribution.set(score, (distribution.get(score) || 0) + 1);
    }
  const allowed = [...distribution]
    .filter(([, n]) => n / c.window + 1e-12 >= c.minSupport)
    .map(([s]) => s)
    .sort((a, b) => a - b);
  const score = scorerAt(rows, rows.length, c);
  return {
    score,
    test: (number: string) => {
      const s = score(number);
      return c.strategy === "historical"
        ? allowed.includes(s)
        : s >= c.min && s <= c.max;
    },
    diagnostics: {
      method: relationLabels[c.method],
      metric: relationMetricLabels[c.metric],
      scope: c.scope,
      position: c.position,
      previousPosition: c.previousPosition,
      lag: c.lag,
      depth: c.depth,
      strategy: c.strategy,
      range: [c.min, c.max],
      window: c.strategy === "historical" ? c.window : lookback(c),
      minSupport: c.minSupport,
      mirror: c.method === "mirror" ? c.mirror : undefined,
      firstIssue:
        rows[
          c.strategy === "historical"
            ? rows.length - c.window
            : rows.length - lookback(c)
        ].issue,
      lastIssue: rows.at(-1)!.issue,
      referenceNumber: rows.at(-c.lag)?.number,
      trainingSamples: c.strategy === "historical" ? c.window : 0,
      allowedScores: allowed,
      distribution: [...distribution]
        .sort((a, b) => a[0] - b[0])
        .map(([value, count]) => ({ value, count, rate: count / c.window })),
    },
  };
}
export function inspectRelations(
  history: HistoryRecord[] | undefined,
  c: RelationConfig,
  maxLag = 12,
) {
  validateRelation(c);
  if (!integer(maxLag, 1, 60)) throw new Error("观察滞后范围为1至60");
  const all = relationHistory(c, history),
    start = Math.max(0, all.length - c.window),
    lastSeen = new Map<number, number>();
  let streak = 0,
    previous: number | undefined;
  const series = all.map((r, i) => {
    const value = relationValue(r.number, c),
      index = lastSeen.get(value);
    streak = previous === value ? streak + 1 : 1;
    const result = {
      ...r,
      value,
      delta: previous === undefined ? null : value - previous,
      repeatGap: index === undefined ? null : i - index,
      streak,
      score: i >= lookback(c) ? scorerAt(all, i, c)(r.number) : null,
    };
    lastSeen.set(value, i);
    previous = value;
    return result;
  });
  const lags = Array.from({ length: maxLag }, (_, i) => {
    const lag = i + 1;
    let samples = 0,
      repeat = 0,
      neighbor = 0,
      mirror = 0;
    for (let j = start; j < all.length; j++) {
      if (j < lag) continue;
      const a = relationValue(all[j].number, c),
        b = relationValue(all[j - lag].number, c, true);
      samples++;
      repeat += Number(a === b);
      neighbor += Number(Math.abs(a - b) === 1);
      if (c.metric === "position") mirror += Number(a === mirrored(b, c));
    }
    return {
      lag,
      samples,
      repeat,
      neighbor,
      mirror: c.metric === "position" ? mirror : null,
    };
  });
  return {
    rows: series.slice(start),
    lags,
    available: all.length,
    firstIssue: all[0].issue,
    lastIssue: all.at(-1)!.issue,
  };
}
