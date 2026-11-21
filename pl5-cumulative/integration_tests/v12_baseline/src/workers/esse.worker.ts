/** GitHub rules remain authoritative: this Worker converts their results to masks.
 * No externally generated code is evaluated here.
 */
import { defaultPositions, filter, type FilterInput } from "../domain/pick5";

const SCHEMA = "pl5-esse-bridge-v1";
const N = 100000;

async function mask(numbers: string[]) {
  const data = new Uint8Array(N / 8);
  for (const number of numbers) {
    if (!/^\d{5}$/.test(number)) throw new Error("检测到非五位号码");
    const index = Number(number);
    data[index >>> 3] |= 1 << (index & 7);
  }
  const hash = await crypto.subtle.digest("SHA-256", data);
  const sha256 = [...new Uint8Array(hash)].map((x) => x.toString(16).padStart(2, "0")).join("");
  return {
    encoding: "bitset-lsb0-base64",
    bits: btoa(String.fromCharCode(...data)),
    sha256,
    count: numbers.length,
  };
}

self.onmessage = async (event: MessageEvent<{ requestId: number; input: FilterInput; k: number; seed: number }>) => {
  const { requestId, input, k, seed } = event.data;
  try {
    if (input.combination?.mode && input.combination.mode !== "strict")
      throw new Error("ESSE V1.2暂不接入容错组或违规预算模式，请切换严格AND");
    const active = input.rules.filter((r) => r.enabled);
    if (active.length > 20) throw new Error("本版ESSE最多分析20条启用条件");
    const original = { positions: input.positions, candidates: input.candidates, history: input.history,
      historySource: input.historySource };
    const baseNumbers = filter({ ...original, rules: [] }).numbers;
    if (!baseNumbers.length) throw new Error("来源集合为空，无法雕塑");
    const base = await mask(baseNumbers);
    const rules = [];
    for (const rule of active) {
      const kept = filter({
        positions: defaultPositions(),
        candidates: baseNumbers,
        history: input.history,
        historySource: input.historySource,
        rules: [rule],
      }).numbers;
      rules.push({ id: rule.id, label: rule.kind, group: rule.group ?? rule.kind,
        enabled: true, kept: await mask(kept) });
    }
    // Independent native strict conjunction; excludes result-sensitive scoring tools.
    const strict = filter({ ...original, rules: active }).numbers;
    const sortedHistory = [...(input.history ?? [])].sort((a,b)=>a.date.localeCompare(b.date));
    const payload = {
      schema: SCHEMA, combination: "strict", k, seed, base, rules,
      expected_strict_keep: strict.length,
      meta: {
        history_source: input.historySource ?? "未标注",
        reference_issue: sortedHistory.at(-1)?.issue ?? null,
        historical_record_count: sortedHistory.length,
        source_kind: input.candidates ? "external_candidates" : "position_selection",
      },
    };
    self.postMessage({ requestId, payload });
  } catch (error) {
    self.postMessage({ requestId, error: error instanceof Error ? error.message : "过滤位图准备失败" });
  }
};
