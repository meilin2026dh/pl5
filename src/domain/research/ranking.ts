import type { PreparedResearch, ResearchConfig, ScoreModel } from "./types";
const TOTAL = 100000;
// Stable integer avalanche hash: deterministic across browsers, independent of enumeration order.
function tieHash(index: number, seed: number) {
  let x = (index ^ (seed >>> 0)) >>> 0;
  x = Math.imul(x ^ (x >>> 16), 0x7feb352d);
  x = Math.imul(x ^ (x >>> 15), 0x846ca68b);
  return (x ^ (x >>> 16)) >>> 0;
}
export function rankSelection(
  config: ResearchConfig,
  model: ScoreModel,
): PreparedResearch {
  if (
    !Number.isFinite(config.retain) ||
    config.retain <= 0 ||
    config.retain > 1
  )
    throw new Error("排名保留比例必须大于0且不超过1");
  if (config.ties !== "inclusive" && config.ties !== "seeded")
    throw new Error("未知并列策略");
  if (!Number.isSafeInteger(config.seed))
    throw new Error("排名种子必须是安全整数");
  const scores = new Float64Array(TOTAL),
    order = Array.from({ length: TOTAL }, (_, i) => i),
    hashes = new Uint32Array(TOTAL);
  for (let i = 0; i < TOTAL; i++) {
    const raw = model.score(String(i).padStart(5, "0"));
    if (Number.isNaN(raw) || raw === Infinity)
      throw new Error("评分包含无效数值");
    scores[i] = raw === -Infinity ? -Infinity : Math.round(raw * 1e12) / 1e12;
    hashes[i] = tieHash(i, config.seed);
  }
  order.sort((a, b) =>
    scores[a] === scores[b]
      ? config.ties === "seeded"
        ? hashes[a] - hashes[b] || a - b
        : a - b
      : scores[a] > scores[b]
        ? -1
        : 1,
  );
  const targetCount = Math.max(1, Math.floor(TOTAL * config.retain)),
    boundary = scores[order[targetCount - 1]];
  let actualCount = targetCount;
  if (config.ties === "inclusive")
    while (actualCount < TOTAL && scores[order[actualCount]] === boundary)
      actualCount++;
  const selected = new Uint8Array(TOTAL);
  for (let i = 0; i < actualCount; i++) selected[order[i]] = 1;
  let boundaryTies = 0;
  for (const score of scores) if (score === boundary) boundaryTies++;
  return {
    test: (n) => /^\d{5}$/.test(n) && selected[Number(n)] === 1,
    diagnostics: {
      ...model.details,
      universe: TOTAL,
      targetCount,
      actualCount,
      boundaryScore: boundary === -Infinity ? "-Infinity" : boundary,
      boundaryTies,
      allUniform: scores[order[0]] === scores[order[TOTAL - 1]],
      quantizationDecimals: 12,
      ties: config.ties,
      seed: config.seed,
    },
  };
}
