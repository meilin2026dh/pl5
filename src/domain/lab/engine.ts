import { filter, validateInput, type FilterInput } from "../pick5";
import { researchHistory } from "../research/statistics";
import { defaultResearch } from "../research/types";
import { rulesAtCutoff } from "../backtest";
import { parseCandidates } from "../../lib/candidates";
import { learnScorer } from "../selection/learning";
import { solveCover } from "./cover";
import { updatePosterior, type PosteriorState } from "./posterior";
import { validateLab, type LabConfig } from "./config";
import { pipelineStages } from "./registry";
export function analyzeLab(
  input: FilterInput,
  c: LabConfig,
  task: "posterior" | "cover",
  previous?: PosteriorState,
  progress?: (s: string) => void,
) {
  validateLab(c);
  validateInput({ ...input, lab: c });
  const latest = researchHistory(
      { ...defaultResearch, window: 1, referenceIssue: c.referenceIssue },
      input.history,
    )[0],
    rows = input
      .history!.filter((r) => r.date <= latest.date)
      .sort((a, b) => a.date.localeCompare(b.date)),
    metadata = {
      version: "sequence-research-v1",
      source: input.historySource ?? "未标注",
      cutoff: latest.issue,
      config: c,
      stages: pipelineStages,
    };
  if (task === "posterior") {
    progress?.("验证历史前缀与增量计数");
    return {
      ...metadata,
      stages: [
        "完整历史质量与截止",
        "缓存前缀验证",
        "增量计数/修订重建",
        "Beta后验区间",
        "完整报告",
      ],
      task,
      posterior: updatePosterior(rows, c.posterior, metadata.source, previous),
      cover: null,
      candidateSelection: null,
    };
  }
  if (rows.length < c.window) throw Error("覆盖评分历史不足指定窗口");
  progress?.("规则来源域与冻结贝叶斯软分");
  const eligible = filter({
      ...input,
      lab: c,
      history: rows,
      rules: rulesAtCutoff(input.rules, latest.issue),
    }).numbers,
    allowed = new Set(eligible),
    model = learnScorer(rows.slice(-c.window), "bayes", false, 0),
    scores = new Map(eligible.map((n) => [n, model.score(n)])),
    ranked = [...eligible].sort(
      (a, b) => scores.get(b)! - scores.get(a)! || a.localeCompare(b),
    );
  const candidates = c.candidatesText.trim()
    ? parseCandidates(c.candidatesText)
    : ranked.slice(0, c.shortlist);
  if (candidates.some((n) => !allowed.has(n)))
    throw Error("显式候选超出当前来源/规则域");
  const targets = c.targetsText.trim()
    ? parseCandidates(c.targetsText)
    : Array.from({ length: c.digits.length ** 5 }, (_, i) => {
        let s = "";
        for (let p = 0; p < 5; p++) {
          s = c.digits[i % c.digits.length] + s;
          i = Math.floor(i / c.digits.length);
        }
        return s;
      });
  progress?.("有限域分支定界，保留完整待搜前沿界");
  const cover = solveCover(candidates, targets, c.cover);
  if (cover.numbers.some((n) => !allowed.has(n))) throw Error("覆盖Guard失败");
  return {
    ...metadata,
    task,
    posterior: null,
    cover,
    candidateSelection: {
      source: eligible.length,
      explicit: !!c.candidatesText.trim(),
      shortlist: candidates.length,
      scorer: "固定Dirichlet逐位后验log分，并列按五位字典序",
      history: [rows.at(-c.window)!.issue, latest.issue],
      warning: "最优证明仅针对报告中的完整短名单和目标域，不是十万全集最优",
    },
  };
}
export type LabResult = ReturnType<typeof analyzeLab>;
