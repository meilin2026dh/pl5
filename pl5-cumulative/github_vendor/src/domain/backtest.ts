import {
  filter,
  type FilterInput,
  type HistoryRecord,
  type Rule,
} from "./pick5";
const historical = new Set([
  "research",
  "relation",
  "historyExclude",
  "samePosition",
  "historyOverlap",
  "neighborCounts",
  "historyDelta",
  "omission",
  "frequency",
]);
export type ReplayRow = HistoryRecord & {
  referenceIssue: string;
  status: "retained" | "removed" | "outside" | "insufficient" | "error";
  reason?: string;
};
export function backtest(input: FilterInput, count: number): ReplayRow[] {
  if (!Number.isInteger(count) || count < 1 || count > 2000)
    throw new Error("回放范围为1–2000期");
  if (!input.history?.length) throw new Error("请先载入历史数据");
  const rows = [...input.history].sort((a, b) => a.date.localeCompare(b.date));
  const base = input.candidates ? new Set(input.candidates) : null;
  return rows.slice(-count).map((row) => {
    const i = rows.indexOf(row),
      past = rows.slice(0, i);
    const referenceIssue = past.at(-1)?.issue ?? "无";
    const result: ReplayRow = {
      ...row,
      referenceIssue,
      status: "insufficient",
    };
    if (
      input.rules.some(
        (r) =>
          r.enabled &&
          (historical.has(r.kind) ||
            (r.kind === "geometry" && r.geometry?.source === "history")),
      ) &&
      !past.length
    )
      return result;
    const allowed = base
      ? base.has(row.number)
      : [...row.number].every((d, p) => input.positions[p].includes(Number(d)));
    if (!allowed) return { ...result, status: "outside" };
    const rules = rulesAtCutoff(input.rules, past.at(-1)?.issue);
    try {
      return {
        ...result,
        status: filter({
          ...input,
          candidates: [row.number],
          history: past,
          rules,
        }).numbers.length
          ? "retained"
          : "removed",
      };
    } catch (e) {
      const message = (e as Error).message;
      return {
        ...result,
        status: /历史不足|历史过滤需要|研究方法需要历史/.test(message)
          ? "insufficient"
          : "error",
        reason: message,
      };
    }
  });
}

export function rulesAtCutoff(rules: Rule[], referenceIssue?: string): Rule[] {
  return rules.map((r) =>
    r.kind === "relation"
      ? {
          ...r,
          relation: { ...r.relation!, referenceIssue: referenceIssue },
        }
      : r.kind === "geometry" && r.geometry?.source === "history"
        ? {
            ...r,
            geometry: { ...r.geometry, referenceIssue: referenceIssue },
          }
        : r.kind === "research"
          ? {
              ...r,
              research: {
                ...r.research!,
                referenceIssue: referenceIssue,
              },
            }
          : historical.has(r.kind)
            ? {
                ...r,
                params: { ...r.params, referenceIssue: referenceIssue },
              }
            : r,
  );
}
