import type { HistoryRecord } from "../pick5";
import { inspectQuality } from "../evidence/statistics";
import { betaQuantile } from "./beta";
export type PosteriorConfig = {
  mode: "all" | "window";
  window: number;
  alpha: number;
};
export type PosteriorState = {
  version: "incremental-v1";
  source: string;
  config: PosteriorConfig;
  records: HistoryRecord[];
  counts: number[][];
};
const count = (rows: HistoryRecord[]) => {
  const c = Array.from({ length: 5 }, () => Array(10).fill(0) as number[]);
  for (const r of rows) [...r.number].forEach((d, p) => c[p][Number(d)]++);
  return c;
};
export function updatePosterior(
  rows: HistoryRecord[],
  config: PosteriorConfig,
  source: string,
  previous?: PosteriorState,
) {
  if (
    !["all", "window"].includes(config.mode) ||
    !Number.isInteger(config.window) ||
    config.window < 1 ||
    config.window > 10000 ||
    !Number.isFinite(config.alpha) ||
    config.alpha < 0.1 ||
    config.alpha > 100
  )
    throw Error("增量后验配置错误");
  const quality = inspectQuality(rows);
  if (quality.errors.length || !rows.length || rows.length > 10000)
    throw Error("增量历史数据错误");
  const sorted = [...rows].sort((a, b) => a.date.localeCompare(b.date)),
    used = config.mode === "all" ? sorted : sorted.slice(-config.window);
  let counts = count([]),
    added = used.length,
    action: "append" | "unchanged" | "rebuild" = "rebuild",
    removed = 0,
    reason = previous
      ? "缓存记录或计数校验失败，从可靠历史重建"
      : "首次同步，没有缓存";
  if (previous && previous.version !== "incremental-v1")
    reason = "缓存版本不兼容";
  else if (previous && previous.source !== source) reason = "历史来源变化";
  else if (
    previous &&
    JSON.stringify(previous.config) !== JSON.stringify(config)
  )
    reason = "先验或计数模式/窗口配置变化";
  const valid =
    previous?.version === "incremental-v1" &&
    previous.source === source &&
    JSON.stringify(previous.config) === JSON.stringify(config) &&
    Array.isArray(previous.records) &&
    !inspectQuality(previous.records).errors.length &&
    JSON.stringify(count(previous.records)) === JSON.stringify(previous.counts);
  if (valid) {
    reason = "历史前缀修订、回退或窗口不重叠";
    const old = previous!.records,
      start = old.findIndex((r) => r.issue === used[0].issue);
    if (start >= 0) {
      const kept = old.slice(start),
        overlap = Math.min(kept.length, used.length);
      if (
        JSON.stringify(kept.slice(0, overlap)) ===
          JSON.stringify(used.slice(0, overlap)) &&
        kept.length <= used.length
      ) {
        counts = previous!.counts.map((r) => [...r]);
        for (const r of old.slice(0, start))
          [...r.number].forEach((d, p) => counts[p][Number(d)]--);
        removed = start;
        added = used.length - kept.length;
        for (const r of used.slice(kept.length))
          [...r.number].forEach((d, p) => counts[p][Number(d)]++);
        action = added || removed ? "append" : "unchanged";
        reason = removed
          ? "验证通过：滑窗移出旧记录并追加新记录"
          : added
            ? "验证通过：仅追加新记录"
            : "前缀和计数一致，没有新记录";
      }
    }
  }
  if (action === "rebuild") counts = count(used);
  const total = used.length + 10 * config.alpha,
    cells = counts.flatMap((row, p) =>
      row.map((n, d) => {
        const a = n + config.alpha,
          b = total - a;
        return {
          position: p,
          digit: d,
          count: n,
          mean: a / total,
          low: betaQuantile(0.025, a, b),
          high: betaQuantile(0.975, a, b),
        };
      }),
    );
  return {
    action,
    reason,
    added,
    removed,
    used: used.length,
    range: [used[0].issue, used.at(-1)!.issue],
    cells,
    state: {
      version: "incremental-v1" as const,
      source,
      config,
      records: used,
      counts,
    },
    quality,
  };
}
