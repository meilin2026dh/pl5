import { it, expect } from "vitest";
import { validateResearchConfig } from "../src/domain/research/config";
import { defaultResearch } from "../src/domain/research/types";
it("validates finite bounded settings and rejects coercion", () => {
  expect(() => validateResearchConfig(defaultResearch)).not.toThrow();
  for (const change of [
    { window: 0 },
    { seed: NaN },
    { retain: 0 },
    { method: "unknown" },
    { parameter: "7" },
    { folds: 6 },
    { ties: "random" },
    { referenceIssue: 5 },
  ])
    expect(() =>
      validateResearchConfig({ ...defaultResearch, ...change }),
    ).toThrow();
});
