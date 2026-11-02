import { describe, expect, it } from "vitest";
import { evolveOperators } from "./operatorEvolution";
const row = (issue: string, draw: string, externalDigit: number) =>
  ({ issue, draw, externalDigit, availableBeforeDraw: true });
describe("V3.6 train-only finite operator evolution", () => {
  it("learns a finite operator and reports untouched test results", () => {
    const result = evolveOperators(
      [row("1","00000",0),row("2","11111",1)],
      [row("3","22222",2)],
      [row("4","33333",3)],
    );
    expect(result.operator.table).toHaveLength(10);
    expect(result.baseline).toBe(0.1);
    expect(result.eligibleForProduction).toBe(false);
  });
  it("rejects reused issue identifiers", () => {
    expect(() => evolveOperators([row("1","00000",0)],[row("1","11111",1)],[row("3","22222",2)])).toThrow();
  });
  it("rejects future training features", () => {
    expect(() => evolveOperators([{...row("1","00000",0),availableBeforeDraw:false}],[row("2","11111",1)],[row("3","22222",2)])).toThrow();
  });
});
