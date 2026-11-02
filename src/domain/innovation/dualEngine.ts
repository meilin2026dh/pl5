/** V3.6 research-only dual engine. No rule is automatically activated for betting. */
export type DigitOperator = { id: string; table: readonly number[] };
export type AlignedRow = { issue: string; draw: string; externalDigit: number; availableBeforeDraw: boolean };
export type Candidate = { operator: DigitOperator; position: number; trainMissRate: number; testMissRate: number; testCount: number; baseline: number };
export function validateOperator(op: DigitOperator): void {
  if (!op.id || op.table.length !== 10 || op.table.some(x => !Number.isInteger(x) || x < 0 || x > 9))
    throw new Error("invalid digit operator");
}
export function shiftOperators(): DigitOperator[] {
  return Array.from({ length: 10 }, (_, k) => ({
    id: `shift-${k}`, table: Array.from({ length: 10 }, (_, d) => (d + k) % 10),
  }));
}
export function evaluateExclusion(rows: readonly AlignedRow[], operator: DigitOperator, position: number): number {
  validateOperator(operator);
  if (!Number.isInteger(position) || position < 0 || position > 4 || rows.length === 0)
    throw new Error("invalid evaluation window or position");
  let misses = 0;
  for (const row of rows) {
    if (!/^\d{5}$/.test(row.draw) || !Number.isInteger(row.externalDigit) ||
        row.externalDigit < 0 || row.externalDigit > 9 || !row.availableBeforeDraw)
      throw new Error("invalid row or future information leakage");
    misses += Number(Number(row.draw[position]) === operator.table[row.externalDigit]);
  }
  return misses / rows.length;
}
/** Train-only selection. Test rows must be held out and never influence selection. */
export function runDualEngine(train: readonly AlignedRow[], test: readonly AlignedRow[], ops = shiftOperators()): Candidate {
  if (!train.length || !test.length || !ops.length) throw new Error("empty data");
  const trainIssues = new Set(train.map(r => r.issue));
  if (test.some(r => trainIssues.has(r.issue))) throw new Error("train/test issue overlap");
  let best: { operator: DigitOperator; position: number; trainMissRate: number } | undefined;
  for (const operator of ops) for (let position = 0; position < 5; position++) {
    const trainMissRate = evaluateExclusion(train, operator, position);
    if (!best || trainMissRate < best.trainMissRate)
      best = { operator, position, trainMissRate };
  }
  const selected = best!;
  return { ...selected, testMissRate: evaluateExclusion(test, selected.operator, selected.position),
    testCount: test.length, baseline: 0.1 };
}
