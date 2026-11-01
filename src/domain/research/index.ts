import type { HistoryRecord } from "../pick5";
import { validateResearchConfig } from "./config";
import { buildStats, researchHistory } from "./statistics";
import { fitFilter } from "./filters";
import { fitScores } from "./models";
import { rankSelection } from "./ranking";
import { tuneResearch } from "./tuning";
import { presets } from "./presets";
import {
  filterMethods,
  researchLabels,
  type ResearchConfig,
  type PreparedResearch,
  type FilterMethod,
} from "./types";
export { validateResearchConfig, researchHistory };
export function prepareResearch(
  config: ResearchConfig,
  history?: HistoryRecord[],
): PreparedResearch {
  validateResearchConfig(config);
  const rows = researchHistory(config, history),
    stats = buildStats(rows);
  let prepared: PreparedResearch;
  if (filterMethods.includes(config.method as FilterMethod))
    prepared = fitFilter(
      config.method as FilterMethod,
      config.parameter,
      stats,
    );
  else if (
    config.method === "auto" ||
    config.method === "greedy" ||
    config.method === "preset"
  ) {
    const selection =
      config.method === "preset"
        ? {
            selected: presets[config.preset],
            diagnostics: { preset: config.preset },
          }
        : tuneResearch(config, rows);
    const filters = selection.selected.map((s) =>
      fitFilter(s.method, s.parameter, stats),
    );
    prepared = {
      test: (number) => filters.every((f) => f.test(number)),
      diagnostics: {
        ...selection.diagnostics,
        selected: selection.selected,
        derived: filters.map((f) => f.diagnostics),
      },
    };
  } else prepared = rankSelection(config, fitScores(config, stats));
  return {
    test: prepared.test,
    diagnostics: {
      method: researchLabels[config.method],
      window: rows.length,
      firstIssue: rows[0].issue,
      lastIssue: rows.at(-1)!.issue,
      firstDate: rows[0].date,
      lastDate: rows.at(-1)!.date,
      ...prepared.diagnostics,
    },
  };
}
