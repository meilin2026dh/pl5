import { evaluateExclusion, type AlignedRow, type DigitOperator } from "./dualEngine";

/** V3.6 finite-table operator evolution: train-only search with complexity control. */
export type EvolutionResult = {
  operator: DigitOperator;
  position: number;
  trainingMissRate: number;
  validationMissRate: number;
  testMissRate: number;
  baseline: number;
  validationCount: number;
  testCount: number;
  eligibleForProduction: false;
};
export function evolveOperators(
  train: readonly AlignedRow[],
  validation: readonly AlignedRow[],
  test: readonly AlignedRow[],
  maxOperators = 100,
): EvolutionResult {
  if (!train.length || !validation.length || !test.length ||
      !Number.isInteger(maxOperators) || maxOperators < 1 || maxOperators > 10000)
    throw Error("invalid experiment windows or operator budget");
  const all = [...train, ...validation, ...test];
  if (new Set(all.map(r => r.issue)).size !== all.length)
    throw Error("overlapping issue across experimental windows");
  // Generate novel finite operator tables from training data only; no test leakage.
  const candidates: DigitOperator[] = [];
  for (let shift = 0; shift < 10 && candidates.length < maxOperators; shift++)
    candidates.push({ id: `mod10-add-${shift}`, table: Array.from({ length: 10 }, (_, x) => (x + shift) % 10) });
  for (let pos = 0; pos < 5 && candidates.length < maxOperators; pos++) {
    const counts = Array.from({ length: 10 }, () => Array<number>(10).fill(0));
    for (const r of train) {
      if (!r.availableBeforeDraw || !/^\\d{5}$/.test(r.draw) ||
          !Number.isInteger(r.externalDigit) || r.externalDigit < 0 || r.externalDigit > 9)
        throw Error("invalid or future training data");
      counts[r.externalDigit]![Number(r.draw[pos])!]++;
    }
    // Least frequent digit per input symbol: a learned exclusion operator.
    candidates.push({
      id: `learned-min-frequency-position-${pos}`,
      table: counts.map(row => row.indexOf(Math.min(...row))),
    });
  }
  let best: { op: DigitOperator; pos: number; train: number; validation: number } | undefined;
  for (const op of candidates) for (let pos = 0; pos < 5; pos++) {
    const training = evaluateExclusion(train, op, pos);
    const heldValidation = evaluateExclusion(validation, op, pos);
    if (!best || heldValidation < best.validation ||
        (heldValidation === best.validation && training < best.train))
      best = { op, pos, train: training, validation: heldValidation };
  }
  const chosen = best!;
  return {
    operator: chosen.op, position: chosen.pos,
    trainingMissRate: chosen.train, validationMissRate: chosen.validation,
    testMissRate: evaluateExclusion(test, chosen.op, chosen.pos),
    baseline: 0.1, validationCount: validation.length, testCount: test.length,
    eligibleForProduction: false,
  };
}
