import { describe, expect, it } from "vitest";
import { mathFeatures } from "../src/domain/math";
import { defaultPositions, filter, type Rule } from "../src/domain/pick5";
const rule = (
  kind: Rule["kind"],
  values: Rule["values"],
  params?: Rule["params"],
): Rule => ({ id: kind, kind, values, params, enabled: true, mode: "include" });
const run = (
  r: Rule,
  candidates = ["01234", "12345", "54321", "24888", "00000", "99999"],
) => filter({ positions: defaultPositions(), candidates, rules: [r] }).numbers;
describe("mathematical digit features", () => {
  it("separates mathematical primes, composites and neither from lottery classification", () => {
    expect(mathFeatures("01234")).toMatchObject({
      pattern: "NNPPC",
      counts: "2:1:2",
      productTail: 0,
      inversions: 0,
      gcd: 1,
      lcm: 0,
    });
    expect(run(rule("mathPrimePattern", ["NNPP?"]))).toEqual(["01234"]);
    expect(run(rule("mathClassCounts", ["3:1:1"]))).toEqual(["12345", "54321"]);
    expect(run(rule("primePattern", ["11101"]), ["12345"])).toEqual(["12345"]);
  });
  it("distinguishes sum modulo, sum of remainders and full product tail", () => {
    expect(run(rule("sumModulo", [0], { modulus: 5 }), ["12345"])).toEqual([
      "12345",
    ]);
    expect(run(rule("remainderSum", [10], { modulus: 5 }), ["12345"])).toEqual([
      "12345",
    ]);
    expect(run(rule("productTail", [8]), ["22223", "12340"])).toEqual([
      "22223",
    ]);
    expect(mathFeatures("99999").productTail).toBe(9);
  });
  it("counts strict inversions with equal digits and leading zeroes", () => {
    expect(mathFeatures("54321").inversions).toBe(10);
    expect(mathFeatures("22110").inversions).toBe(8);
    expect(mathFeatures("00000").inversions).toBe(0);
    expect(run(rule("inversions", [10]))).toEqual(["54321"]);
  });
  it("defines zero-safe whole-digit gcd/lcm and handles maximum lcm", () => {
    expect(mathFeatures("00000")).toMatchObject({ gcd: 0, lcm: 0 });
    expect(mathFeatures("02468")).toMatchObject({ gcd: 2, lcm: 0 });
    expect(mathFeatures("56789").lcm).toBe(2520);
    expect(run(rule("digitGcd", [2]))).toEqual(["24888"]);
    expect(run(rule("digitLcm", [60]))).toEqual(["12345", "54321"]);
  });
  it("filters specified or all positional gcd/lcm pairs by matching counts", () => {
    expect(
      run(rule("pairGcd", [2], { positions: [0, 1] }), ["02468", "12345"]),
    ).toEqual(["02468"]);
    expect(
      run(rule("pairLcm", [72], { positions: [0, 1] }), ["89000", "88000"]),
    ).toEqual(["89000"]);
    expect(
      run(rule("pairGcd", [0], { countMin: 10, countMax: 10 }), [
        "00000",
        "00001",
      ]),
    ).toEqual(["00000"]);
    expect(
      run(rule("pairLcm", [0], { countMin: 4, countMax: 4 }), [
        "01234",
        "00123",
      ]),
    ).toEqual(["01234"]);
  });
  it("rejects malformed patterns, distributions, moduli, bounds and pair scopes", () => {
    for (const r of [
      rule("mathPrimePattern", ["10101"]),
      rule("mathClassCounts", ["2:2:2"]),
      rule("sumModulo", [3], { modulus: 3 }),
      rule("sumModulo", [0], { modulus: 0 }),
      rule("inversions", [11]),
      rule("digitGcd", [-1]),
      rule("digitLcm", [2521]),
      rule("pairLcm", [73]),
      rule("pairGcd", [1], { positions: [0] }),
    ])
      expect(() => run(r)).toThrow();
  });
  it("supports exclude, disabled rules and group tolerance", () => {
    const r = rule("inversions", [0]);
    expect(run({ ...r, mode: "exclude" }, ["12345", "54321"])).toEqual([
      "54321",
    ]);
    expect(run({ ...r, enabled: false }, ["12345", "54321"])).toHaveLength(2);
    expect(
      filter({
        positions: defaultPositions(),
        candidates: ["12345", "54321"],
        rules: [r, { ...rule("productTail", [0]), group: "x" }],
        combination: { mode: "atLeast", minimum: 1 },
      }).numbers,
    ).toHaveLength(2);
  });
});
it("agrees with independent combinatorial totals over the full 100000 candidates", () => {
  const all = (r: Rule) =>
    filter({ positions: defaultPositions(), rules: [r] }).numbers.length;
  expect(all(rule("inversions", [0]))).toBe(2002);
  expect(all(rule("inversions", [10]))).toBe(252);
  expect(all(rule("mathClassCounts", ["3:1:1"]))).toBe(10240);
});
it("round-trips math rules through saved plans and evaluates historical replay", async () => {
  const { encodePlan, decodePlans } = await import("../src/lib/plans");
  const { backtest } = await import("../src/domain/backtest");
  const input = {
    positions: defaultPositions(),
    candidates: ["12345", "54321"],
    rules: [rule("inversions", [10])],
    history: [
      { issue: "1", date: "2026-01-01", number: "12345" },
      { issue: "2", date: "2026-01-02", number: "54321" },
    ],
  };
  const plan = encodePlan("数学测试", input);
  const restored = decodePlans(
    JSON.stringify({ schemaVersion: 1, plans: [plan] }),
  )[0];
  expect(filter(restored.input).numbers).toEqual(["54321"]);
  expect(backtest(restored.input, 2).map((r) => r.status)).toEqual([
    "removed",
    "retained",
  ]);
});
