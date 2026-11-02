import { evaluateExclusion, type AlignedRow, type DigitOperator } from "./dualEngine";

export type RollingResult = {
  windows: { trainStart: string; trainEnd: string; testStart: string; testEnd: string; selectedOperator: string; position: number; trainMissRate: number; testMissRate: number; testCount: number }[];
  pooledMissRate: number;
  baseline: 0.1;
  totalTestRows: number;
  eligibleForProduction: false;
};
/** Rolling evaluation: candidates are chosen using only past issues.
 * Caller must supply chronological, timestamp-aligned rows; issue IDs are unique.
 * All external features must be available before the corresponding draw.
 */
export function rollingExclusion(
  rows: readonly AlignedRow[], operators: readonly DigitOperator[],
  trainSize: number, testSize: number,
): RollingResult {
  if (!Number.isInteger(trainSize) || trainSize < 20 || !Number.isInteger(testSize) || testSize < 1 ||
      !operators.length || rows.length < trainSize + testSize)
    throw Error("invalid rolling experiment configuration");
  if (new Set(rows.map(r => r.issue)).size !== rows.length)
    throw Error("duplicate issues");
  if (rows.some(r => !r.availableBeforeDraw || !/^\\d{5}$/.test(r.draw) ||
      !Number.isInteger(r.externalDigit) || r.externalDigit < 0 || r.externalDigit > 9))
    throw Error("invalid or future feature");
  // Issue identifiers must be monotonically increasing in a consistent format.
  if (rows.some((r, i) => i > 0 && r.issue <= rows[i - 1]!.issue))
    throw Error("issues must be strictly chronological");
  const windows: RollingResult["windows"] = [];
  let missTotal = 0, totalTestRows = 0;
  for (let start = 0; start + trainSize + testSize <= rows.length; start += testSize) {
    const train = rows.slice(start, start + trainSize);
    const test = rows.slice(start + trainSize, start + trainSize + testSize);
    let best: { op: DigitOperator; position: number; missRate: number } | undefined;
    for (const op of operators) for (let position = 0; position < 5; position++) {
      const missRate = evaluateExclusion(train, op, position);
      if (!best || missRate < best.missRate)
        best = { op, position, missRate };
    }
    const chosen = best!;
    const testMissRate = evaluateExclusion(test, chosen.op, chosen.position);
    missTotal += testMissRate * test.length;
    totalTestRows += test.length;
    windows.push({
      trainStart: train[0]!.issue, trainEnd: train[train.length - 1]!.issue,
      testStart: test[0]!.issue, testEnd: test[test.length - 1]!.issue,
      selectedOperator: chosen.op.id, position: chosen.position,
      trainMissRate: chosen.missRate, testMissRate, testCount: test.length,
    });
  }
  return { windows, pooledMissRate: missTotal / totalTestRows, baseline: 0.1,
    totalTestRows, eligibleForProduction: false };
}
