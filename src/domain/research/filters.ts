import { feature } from "./statistics";
import {
  filterMethods,
  type FilterMethod,
  type PreparedResearch,
  type ResearchStats,
} from "./types";
export function validateFilterParameter(
  method: FilterMethod,
  parameter: number,
): void {
  if (!filterMethods.includes(method) || !Number.isFinite(parameter))
    throw new Error("研究参数无效");
  const integer = [
    "hotcold",
    "omission",
    "samePosition",
    "positionNeighbor",
    "multiset",
  ].includes(method);
  const minimum = method === "hotcold" || method === "multiset" ? 1 : 0;
  let maximum = Infinity;
  if (method === "hotcold") maximum = 10;
  else if (method === "samePosition" || method === "positionNeighbor")
    maximum = 5;
  else if (
    ["bayes", "markov", "sumQuantile", "spanQuantile"].includes(method) ||
    method.endsWith("Frequency")
  )
    maximum = 1;
  if (
    parameter < minimum ||
    parameter > maximum ||
    (integer && !Number.isInteger(parameter))
  )
    throw new Error("研究参数超出范围");
}
const quantile = (values: number[], q: number) =>
  values[
    Math.min(values.length - 1, Math.max(0, Math.floor(q * values.length)))
  ];
export function fitFilter(
  method: FilterMethod,
  parameter: number,
  stats: ResearchStats,
): PreparedResearch & { testDigits: (digits: number[]) => boolean } {
  validateFilterParameter(method, parameter);
  const diagnostics: PreparedResearch["diagnostics"] = {
    method,
    parameter,
    trainingCount: stats.n,
    firstIssue: stats.rows[0].issue,
    lastIssue: stats.rows[stats.n - 1].issue,
  };
  let testDigits: (digits: number[]) => boolean;
  if (["hotcold", "omission", "bayes", "markov"].includes(method)) {
    const allowed = stats.counts.map((counts, p) => {
      if (method === "hotcold")
        return Array.from({ length: 10 }, (_, d) => d)
          .sort((a, b) => counts[b] - counts[a] || a - b)
          .slice(0, parameter);
      const trans = stats.transitions[p][stats.last[p]],
        total = trans.reduce((a, b) => a + b, 0);
      return Array.from({ length: 10 }, (_, d) => d).filter((d) =>
        method === "omission"
          ? stats.omissions[p][d] >= 0 && stats.omissions[p][d] <= parameter
          : method === "bayes"
            ? (counts[d] + 1) / (stats.n + 10) >= parameter
            : (trans[d] + 1) / (total + 10) >= parameter,
      );
    });
    diagnostics.allowed = allowed;
    if (method === "omission")
      diagnostics.omissionPolicy =
        "窗口内观测记录间隔；未出现数字未知并排除，不将窗口长当成精确遗漏";
    testDigits = (d) => d.every((x, p) => allowed[p].includes(x));
  } else if (["sumSigma", "sumQuantile", "spanQuantile"].includes(method)) {
    const values = method === "spanQuantile" ? stats.spans : stats.sums,
      lo =
        method === "sumSigma"
          ? stats.mean - parameter * stats.sd
          : quantile(values, (1 - parameter) / 2),
      hi =
        method === "sumSigma"
          ? stats.mean + parameter * stats.sd
          : quantile(values, (1 + parameter) / 2);
    Object.assign(diagnostics, { lo, hi, mean: stats.mean, sd: stats.sd });
    testDigits = (d) => {
      const value =
        method === "spanQuantile"
          ? Math.max(...d) - Math.min(...d)
          : d.reduce((a, b) => a + b, 0);
      return value >= lo && value <= hi;
    };
  } else if (method.endsWith("Frequency")) {
    const keys =
      method === "distinctFrequency"
        ? [1, 2, 3, 4, 5]
        : method === "consecutiveFrequency"
          ? [0, 1, 2, 3, 4]
          : method === "tailFrequency"
            ? Array.from({ length: 10 }, (_, i) => i)
            : method === "routeFrequency"
              ? Array.from({ length: 6 }, (_, a) =>
                  Array.from(
                    { length: 6 - a },
                    (_, b) => a * 36 + b * 6 + 5 - a - b,
                  ),
                ).flat()
              : [0, 1, 2, 3, 4, 5];
    const freq = stats.frequencies[method];
    let allowed = keys.filter(
      (k) => (freq.get(String(k)) ?? 0) / stats.n >= parameter,
    );
    const fallback = !allowed.length;
    if (fallback)
      allowed = [
        keys.reduce((best, key) =>
          (freq.get(String(key)) ?? 0) > (freq.get(String(best)) ?? 0)
            ? key
            : best,
        ),
      ];
    Object.assign(diagnostics, { allowed, fallback });
    const set = new Set(allowed.map(String));
    testDigits = (d) => set.has(feature(method, d));
  } else if (method === "samePosition" || method === "positionNeighbor") {
    testDigits = (d) =>
      d.filter((x, p) =>
        method === "samePosition"
          ? x === stats.last[p]
          : Math.abs(x - stats.last[p]) <= 1,
      ).length <= parameter;
    diagnostics.referenceNumber = stats.last.join("");
  } else {
    testDigits = (d) =>
      (stats.multisets.get([...d].sort((a, b) => a - b).join("")) ?? 0) >=
      parameter;
  }
  return {
    testDigits,
    test: (number) =>
      /^\d{5}$/.test(number) && testDigits([...number].map(Number)),
    diagnostics,
  };
}
