import { describe, expect, it } from "vitest";
import { evaluateExclusion, runDualEngine, shiftOperators } from "./dualEngine";
describe("V3.6 research dual engine", () => {
  const row = (issue: string, draw: string, externalDigit: number) =>
    ({ issue, draw, externalDigit, availableBeforeDraw: true });
  it("creates valid learnable operator candidates", () => {
    expect(shiftOperators()).toHaveLength(10);
    expect(shiftOperators()[0]!.table).toEqual([0,1,2,3,4,5,6,7,8,9]);
  });
  it("preserves leading zeros", () => {
    expect(evaluateExclusion([row("1","00001",0)], shiftOperators()[0]!, 0)).toBe(1);
  });
  it("rejects lookahead", () => {
    expect(() => evaluateExclusion([{...row("1","00001",0),availableBeforeDraw:false}],shiftOperators()[0]!,0)).toThrow();
  });
  it("rejects train/test overlap", () => {
    expect(() => runDualEngine([row("1","00001",0)],[row("1","00002",0)])).toThrow();
  });
  it("evaluates on untouched holdout", () => {
    const result = runDualEngine([row("1","00001",0),row("2","00002",1)],[row("3","99999",0)]);
    expect(result.baseline).toBe(0.1);
    expect(result.testCount).toBe(1);
    expect(result.testMissRate).toBeGreaterThanOrEqual(0);
  });
});
