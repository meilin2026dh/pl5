import type { HistoryRecord } from "../pick5";
import type { ScoreModel } from "./types";
export type PotentialConfig = {
  short: number;
  blocks: number;
  sensitivity: number;
  mode: "warming" | "cooling" | "transition";
  cycleWeight: number;
  clusterWeight: number;
};
export const defaultPotential: PotentialConfig = {
  short: 10,
  blocks: 6,
  sensitivity: 1,
  mode: "transition",
  cycleWeight: 0.5,
  clusterWeight: 0.5,
};
export function validatePotential(
  c: PotentialConfig | undefined,
  window: number,
): asserts c is PotentialConfig {
  if (
    !c ||
    !Number.isInteger(c.short) ||
    c.short < 2 ||
    c.short > 200 ||
    !Number.isInteger(c.blocks) ||
    c.blocks < 3 ||
    c.blocks > 12 ||
    !["warming", "cooling", "transition"].includes(c.mode) ||
    ![c.sensitivity, c.cycleWeight, c.clusterWeight].every(
      (n) => typeof n === "number" && Number.isFinite(n) && n >= 0 && n <= 5,
    )
  )
    throw new Error("冷热势能参数不合法：短窗2—200，分窗3—12，灵敏带与权重0—5");
  if (
    !Number.isInteger(window) ||
    window > 2000 ||
    window < c.short * (c.blocks + 1)
  )
    throw new Error(
      `历史不足：冷热势能窗口至少${c.short * (c.blocks + 1)}期，最多2000期`,
    );
}
export type PotentialSignal = {
  digit: number;
  recentRate: number;
  baselineRate: number;
  band: number;
  z: number;
  momentum: number;
  crossing: string;
  alternation: number;
  states: string[];
  score: number;
  state: number;
};
export function fitPotential(
  rows: HistoryRecord[],
  c: PotentialConfig,
): ScoreModel & { signals: PotentialSignal[][]; blockIssues: string[] } {
  validatePotential(c, rows.length);
  const digits = rows.map((r) => [...r.number].map(Number));
  const ends = Array.from(
    { length: c.blocks },
    (_, i) => rows.length - (c.blocks - 1 - i) * c.short,
  );
  const blocks = ends.map((end) => {
    const start = end - c.short;
    const prior = Array.from(
        { length: 5 },
        () => Array(10).fill(0) as number[],
      ),
      recent = prior.map(() => Array(10).fill(0) as number[]);
    for (let i = 0; i < end; i++)
      for (let p = 0; p < 5; p++)
        (i < start ? prior : recent)[p][digits[i][p]]++;
    return prior.map((counts, p) =>
      counts.map((count, d) => {
        const baselineRate = count / start,
          recentRate = recent[p][d] / c.short;
        const se = Math.sqrt(
          Math.max(0.01, baselineRate * (1 - baselineRate)) *
            (1 / c.short + 1 / start),
        );
        const z = (recentRate - baselineRate) / se;
        return {
          baselineRate,
          recentRate,
          z,
          band: c.sensitivity * se,
          state: z > c.sensitivity ? 1 : z < -c.sensitivity ? -1 : 0,
        };
      }),
    );
  });
  const signals = Array.from({ length: 5 }, (_, p) =>
    Array.from({ length: 10 }, (_, digit) => {
      const series = blocks.map((b) => b[p][digit]),
        last = series.at(-1)!,
        previous = series.at(-2)!;
      const up = previous.z <= c.sensitivity && last.z > c.sensitivity,
        down = previous.z >= -c.sensitivity && last.z < -c.sensitivity;
      const flips = series
        .slice(1)
        .filter((s, i) => s.state !== 0 && s.state === -series[i].state).length;
      const alternation = flips / (c.blocks - 1),
        momentum = last.z - previous.z;
      const cycleDirection = -last.state * alternation;
      const cycle =
        c.mode === "warming"
          ? Math.max(0, cycleDirection)
          : c.mode === "cooling"
            ? Math.max(0, -cycleDirection)
            : alternation;
      const base =
        c.mode === "warming"
          ? momentum + Number(up)
          : c.mode === "cooling"
            ? -momentum + Number(down)
            : Math.abs(momentum) + Number(up || down);
      return {
        digit,
        ...last,
        momentum,
        crossing: up ? "升温越界" : down ? "降温越界" : "未越界",
        alternation,
        states: series.map((s) =>
          s.state > 0 ? "热" : s.state < 0 ? "冷" : "中",
        ),
        score: base + c.cycleWeight * cycle,
      };
    }),
  );
  const score = (number: string) => {
    let total = 0,
      cluster = 0;
    for (let p = 0; p < 5; p++) {
      const s = signals[p][Number(number[p])];
      total += s.score;
      if (
        p &&
        s.state !== 0 &&
        s.state === signals[p - 1][Number(number[p - 1])].state
      )
        cluster++;
    }
    return total / 5 + (c.clusterWeight * cluster) / 4;
  };
  const blockIssues = ends.map((i) => rows[i - 1].issue);
  return {
    signals,
    blockIssues,
    score,
    details: {
      potentialConfig: c,
      blockIssues,
      signals: signals.map((row, p) => ({
        position: ["万位", "千位", "百位", "十位", "个位"][p],
        digits: row,
      })),
      thresholdPolicy:
        "每个截止期重算全量10万组分数，以保留比例分位生成动态阈值；阈值随历史变化，比例固定。",
      clusterPolicy: "候选相邻位置均为热或均为冷的对数/4；中性不计。",
      cyclePolicy:
        "连续分窗热冷直接翻转次数/(分窗数-1)；中性中断，不把未知认作周期。",
    },
  };
}
