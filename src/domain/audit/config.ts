export type AuditConfig = {
  pool: "suggested" | "current";
  training: number;
  target: number;
  correlation: number;
  dedupe: boolean;
  folds: number;
  validation: number;
  referenceIssue?: string;
};
export const defaultAudit: AuditConfig = {
  pool: "suggested",
  training: 100,
  target: 1000,
  correlation: 0.9,
  dedupe: true,
  folds: 3,
  validation: 20,
};
export function validateAudit(c: AuditConfig) {
  if (
    !c ||
    typeof c !== "object" ||
    Array.isArray(c) ||
    !["suggested", "current"].includes(c.pool) ||
    typeof c.dedupe !== "boolean" ||
    typeof c.correlation !== "number" ||
    !Number.isFinite(c.correlation) ||
    c.correlation < 0 ||
    c.correlation > 1
  )
    throw new Error("条件体检参数错误");
  for (const [key, lo, hi] of [
    ["training", 20, 500],
    ["target", 1, 100000],
    ["folds", 1, 5],
    ["validation", 1, 100],
  ] as const) {
    const n = c[key];
    if (!Number.isInteger(n) || n < lo || n > hi)
      throw new Error(`条件体检${key}须为${lo}至${hi}整数`);
  }
  if (
    c.referenceIssue !== undefined &&
    (typeof c.referenceIssue !== "string" || !c.referenceIssue.trim())
  )
    throw new Error("体检参考期错误");
}
