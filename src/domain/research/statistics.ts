import { differenceSignature } from "./difference";
import type { HistoryRecord } from "../pick5";
import type { ResearchConfig, ResearchStats } from "./types";
export function researchHistory(
  config: ResearchConfig,
  history?: HistoryRecord[],
): HistoryRecord[] {
  if (!Array.isArray(history) || !history.length)
    throw new Error("研究方法需要历史数据");
  const issues = new Set<string>(),
    dates = new Set<string>();
  for (const row of history) {
    if (
      !row ||
      typeof row.issue !== "string" ||
      !row.issue.trim() ||
      typeof row.number !== "string" ||
      !/^\d{5}$/.test(row.number) ||
      typeof row.date !== "string" ||
      !/^\d{4}-\d{2}-\d{2}$/.test(row.date) ||
      !Number.isFinite(Date.parse(row.date)) ||
      new Date(row.date).toISOString().slice(0, 10) !== row.date ||
      issues.has(row.issue) ||
      dates.has(row.date)
    )
      throw new Error("历史数据格式、期号或日期重复错误");
    issues.add(row.issue);
    dates.add(row.date);
  }
  let rows = [...history].sort(
    (a, b) => a.date.localeCompare(b.date) || a.issue.localeCompare(b.issue),
  );
  if (config.referenceIssue) {
    const index = rows.findIndex((row) => row.issue === config.referenceIssue);
    if (index < 0) throw new Error("参考期不存在");
    rows = rows.slice(0, index + 1);
  }
  if (
    !Number.isInteger(config.window) ||
    config.window < 1 ||
    rows.length < config.window
  )
    throw new Error("历史不足指定研究窗口");
  return rows.slice(-config.window);
}
export function feature(method: string, d: number[]): string {
  switch (method) {
    case "difference":
      return differenceSignature(d.join(""));
    case "oddFrequency":
      return String(d.filter((x) => x % 2).length);
    case "bigFrequency":
      return String(d.filter((x) => x >= 5).length);
    case "primeFrequency":
      return String(d.filter((x) => [1, 2, 3, 5, 7].includes(x)).length);
    case "distinctFrequency":
      return String(new Set(d).size);
    case "consecutiveFrequency": {
      const sorted = [...d].sort((a, b) => a - b);
      return String(
        sorted.slice(1).filter((x, i) => x - sorted[i] === 1).length,
      );
    }
    case "routeFrequency":
      return String(
        d.filter((x) => x % 3 === 0).length * 36 +
          d.filter((x) => x % 3 === 1).length * 6 +
          d.filter((x) => x % 3 === 2).length,
      );
    case "tailFrequency":
      return String(d.reduce((a, b) => a + b, 0) % 10);
    default:
      throw new Error("未知历史形态");
  }
}
export function buildStats(rows: HistoryRecord[]): ResearchStats {
  if (!rows.length) throw new Error("历史不能为空");
  const digits = rows.map((r) => [...r.number].map(Number)),
    n = rows.length,
    counts = Array.from({ length: 5 }, () => Array(10).fill(0) as number[]),
    omissions = Array.from({ length: 5 }, () => Array(10).fill(-1) as number[]),
    transitions = Array.from({ length: 5 }, () =>
      Array.from({ length: 10 }, () => Array(10).fill(0) as number[]),
    );
  const frequencies: ResearchStats["frequencies"] = {},
    multisets = new Map<string, number>();
  const methods = [
    "difference",
    "oddFrequency",
    "bigFrequency",
    "primeFrequency",
    "distinctFrequency",
    "consecutiveFrequency",
    "routeFrequency",
    "tailFrequency",
  ];
  for (const method of methods) frequencies[method] = new Map();
  for (let i = 0; i < n; i++) {
    const d = digits[i];
    for (let p = 0; p < 5; p++) {
      counts[p][d[p]]++;
      omissions[p][d[p]] = n - 1 - i;
      if (i) transitions[p][digits[i - 1][p]][d[p]]++;
    }
    for (const method of methods) {
      const key = feature(method, d),
        map = frequencies[method];
      map.set(key, (map.get(key) ?? 0) + 1);
    }
    const key = [...d].sort((a, b) => a - b).join("");
    multisets.set(key, (multisets.get(key) ?? 0) + 1);
  }
  const sums = digits.map((d) => d.reduce((a, b) => a + b, 0)),
    spans = digits.map((d) => Math.max(...d) - Math.min(...d)),
    mean = sums.reduce((a, b) => a + b, 0) / n,
    sd = Math.sqrt(sums.reduce((a, b) => a + (b - mean) ** 2, 0) / n);
  return {
    rows: [...rows],
    digits,
    n,
    counts,
    omissions,
    transitions,
    last: digits[n - 1],
    sums: sums.sort((a, b) => a - b),
    spans: spans.sort((a, b) => a - b),
    mean,
    sd,
    frequencies,
    multisets,
  };
}
