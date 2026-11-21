import { describe, expect, it } from "vitest";
import { filter, defaultPositions, defaultRules } from "../src/domain/pick5";

/** The native rules are the contract's authority; parity target is deterministic. */
describe("ESSE bridge native contract fixture", () => {
  it("keeps leading zeros and calculates an AND of two overlapping filters", () => {
    const source = ["00127", "00128", "00227", "99999"];
    const rules = [
      {id:"a",kind:"sum" as const,mode:"include" as const,enabled:true,values:[10,11]},
      {id:"b",kind:"odd" as const,mode:"include" as const,enabled:true,values:[2]},
    ];
    const base = filter({positions:defaultPositions(),candidates:source,rules:[]}).numbers;
    const a = filter({positions:defaultPositions(),candidates:source,rules:[rules[0]]}).numbers;
    const b = filter({positions:defaultPositions(),candidates:source,rules:[rules[1]]}).numbers;
    const both = filter({positions:defaultPositions(),candidates:source,rules}).numbers;
    expect(base).toEqual(source);
    expect(both).toEqual(a.filter(n=>b.includes(n)));
    expect(both.every(n=>/^\d{5}$/.test(n))).toBe(true);
  });
  it("the default empty rules leave full universe unchanged", () => {
    const all=filter({positions:defaultPositions(),rules:defaultRules()});
    expect(all.numbers.length).toBe(100000);
  });
});
