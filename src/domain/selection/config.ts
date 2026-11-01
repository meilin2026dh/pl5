export type SelectionConfig = {
  method: "exact" | "mcga" | "anneal";
  scorer: "bayes" | "neural" | "resnet";
  window: number;
  referenceIssue?: string;
  seed: number;
  samples: number;
  population: number;
  generations: number;
  budget: number;
  acMin: number;
  acMax: number;
  gapThreshold: number;
  minLarge: number;
  maxLarge: number;
  recent: number;
  historySame: number;
  jaccard: number;
  maxSame: number;
  autoTune: boolean;
  outputJaccard?: number;
};
export const defaultSelection: SelectionConfig = {
  method: "exact",
  scorer: "bayes",
  window: 100,
  seed: 20261101,
  samples: 100000,
  population: 200,
  generations: 100,
  budget: 20,
  acMin: 0,
  acMax: 5,
  gapThreshold: 3,
  minLarge: 1,
  maxLarge: 3,
  recent: 15,
  historySame: 4,
  jaccard: 0.85,
  maxSame: 3,
  autoTune: true,
  outputJaccard: 1,
};
export function validateSelection(c: SelectionConfig) {
  if (
    !c ||
    typeof c !== "object" ||
    Array.isArray(c) ||
    !["exact", "mcga", "anneal"].includes(c.method) ||
    !["bayes", "neural", "resnet"].includes(c.scorer)
  )
    throw new Error("精选方法或评分器错误");
  if (
    c.outputJaccard !== undefined &&
    (typeof c.outputJaccard !== "number" ||
      !Number.isFinite(c.outputJaccard) ||
      c.outputJaccard < 0 ||
      c.outputJaccard > 1)
  )
    throw new Error("输出Jaccard上限须为0至1");
  const limits = {
    window: [40, 500],
    seed: [0, 4294967295],
    samples: [100, 1000000],
    population: [10, 500],
    generations: [1, 500],
    budget: [1, 200],
    acMin: [-4, 5],
    acMax: [-4, 5],
    gapThreshold: [1, 9],
    minLarge: [0, 4],
    maxLarge: [0, 4],
    recent: [0, 500],
    historySame: [0, 5],
    maxSame: [0, 4],
  } as const;
  for (const [key, [lo, hi]] of Object.entries(limits)) {
    const n = c[key as keyof typeof limits];
    if (typeof n !== "number" || !Number.isInteger(n) || n < lo || n > hi)
      throw new Error(`精选参数${key}须为${lo}至${hi}的整数`);
  }
  if (
    c.acMin > c.acMax ||
    c.minLarge > c.maxLarge ||
    typeof c.jaccard !== "number" ||
    !Number.isFinite(c.jaccard) ||
    c.jaccard < 0 ||
    c.jaccard > 1 ||
    typeof c.autoTune !== "boolean" ||
    (c.referenceIssue !== undefined &&
      (typeof c.referenceIssue !== "string" || !c.referenceIssue.trim()))
  )
    throw new Error("精选区间、相似度或参考期参数错误");
}
export function seededRandom(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
