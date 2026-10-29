import { describe, expect, it } from "vitest";
import {
  defaultPositions,
  defaultRules,
  filter,
  metrics,
  validateInput,
  type Rule,
} from "../src/domain/pick5";

const rule = (
  kind: Rule["kind"],
  values: Rule["values"],
  mode: Rule["mode"] = "include",
): Rule => ({ id: kind, kind, values, mode, enabled: true });
const sample = [[0], [0], [1], [2], [7]];

describe("排列五指标", () => {
  it("保留前导零并按彩票质数口径计算", () => {
    expect(metrics("00127")).toEqual({
      sum: 10,
      tail: 0,
      span: 7,
      odd: 2,
      big: 1,
      prime: 3,
      distinct: 4,
      repeat: "2111",
      consecutive: 2,
      sumMod3: 1,
    });
    expect(metrics("00000")).toEqual({
      sum: 0,
      tail: 0,
      span: 0,
      odd: 0,
      big: 0,
      prime: 0,
      distinct: 1,
      repeat: "5",
      consecutive: 0,
      sumMod3: 0,
    });
    expect(metrics("99999").sum).toBe(45);
    expect(metrics("01234").repeat).toBe("11111");
    expect(metrics("01999").consecutive).toBe(1);
    expect(metrics("00999").consecutive).toBe(0);
    expect(metrics("11223").repeat).toBe("221");
  });
  it("拒绝非五位数字", () => {
    for (const value of ["1234", "123456", "12a45", "-1234"])
      expect(() => metrics(value)).toThrow();
  });
});

describe("过滤引擎", () => {
  it("生成唯一有序全量十万组，默认对象彼此独立", () => {
    const result = filter({
      positions: defaultPositions(),
      rules: defaultRules(),
    });
    expect(result.initial).toBe(100000);
    expect(result.numbers.length).toBe(100000);
    expect(new Set(result.numbers).size).toBe(100000);
    expect(result.numbers[0]).toBe("00000");
    expect(result.numbers.at(-1)).toBe("99999");
    const positions = defaultPositions();
    positions[0]!.pop();
    expect(positions[1]!.length).toBe(10);
    expect(defaultPositions()[0]!.length).toBe(10);
  });
  it("每类指标都能包含或排除，禁用规则不生效", () => {
    const expected = metrics("00127");
    for (const kind of [
      "sum",
      "tail",
      "span",
      "odd",
      "big",
      "prime",
      "distinct",
      "repeat",
      "consecutive",
      "sumMod3",
    ] as const) {
      expect(
        filter({ positions: sample, rules: [rule(kind, [expected[kind]])] })
          .numbers,
      ).toEqual(["00127"]);
      expect(
        filter({
          positions: sample,
          rules: [rule(kind, [expected[kind]], "exclude")],
        }).numbers,
      ).toEqual([]);
    }
    expect(
      filter({
        positions: sample,
        rules: [{ ...rule("sum", []), enabled: false }],
      }).numbers,
    ).toEqual(["00127"]);
  });
  it("多选为或，规则为且，顺序记录各阶段数量", () => {
    const result = filter({
      positions: [[0], [0], [0], [0], [0, 1, 2, 3]],
      rules: [rule("sum", [1, 2, 3]), rule("odd", [1])],
    });
    expect(result.numbers).toEqual(["00001", "00003"]);
    expect(result.steps.map((s) => [s.id, s.before, s.after])).toEqual([
      ["sum", 4, 3],
      ["odd", 3, 2],
    ]);
  });
  it("包含与排除构成全集互补，输入位置保持不变", () => {
    const positions = [[1, 0], [0], [0], [0], [3, 2, 1, 0]];
    const snapshot = JSON.stringify(positions);
    const included = filter({
      positions,
      rules: [rule("sum", [0, 1, 2])],
    }).numbers;
    const excluded = filter({
      positions,
      rules: [rule("sum", [0, 1, 2], "exclude")],
    }).numbers;
    expect(included.length + excluded.length).toBe(8);
    expect(included.filter((n) => excluded.includes(n))).toEqual([]);
    expect(JSON.stringify(positions)).toBe(snapshot);
    expect(included).toEqual(["00000", "00001", "00002", "10000", "10001"]);
  });
  it("胆码为至少出现一个选中数字，杀号为全部未出现，支持反选", () => {
    expect(
      filter({ positions: sample, rules: [rule("dan", [2, 9])] }).numbers,
    ).toEqual(["00127"]);
    expect(
      filter({ positions: sample, rules: [rule("dan", [2], "exclude")] })
        .numbers,
    ).toEqual([]);
    expect(
      filter({ positions: sample, rules: [rule("kill", [3, 9])] }).numbers,
    ).toEqual(["00127"]);
    expect(
      filter({ positions: sample, rules: [rule("kill", [2])] }).numbers,
    ).toEqual([]);
    expect(
      filter({ positions: sample, rules: [rule("kill", [2], "exclude")] })
        .numbers,
    ).toEqual(["00127"]);
  });
  it("拒绝空位置、越界、重复数字、空规则及非法值", () => {
    const bad = [
      [],
      [[0]],
      [[], ...sample.slice(1)],
      [[10], ...sample.slice(1)],
      [[0, 0], ...sample.slice(1)],
    ];
    for (const positions of bad)
      expect(() => validateInput({ positions, rules: [] })).toThrow();
    for (const r of [
      rule("sum", []),
      rule("sum", [46]),
      rule("span", [-1]),
      rule("dan", [10]),
      rule("repeat", ["123"]),
      rule("odd", ["2"]),
    ])
      expect(() => filter({ positions: sample, rules: [r] })).toThrow();
    expect(() =>
      filter({
        positions: sample,
        rules: [rule("sum", [10]), rule("sum", [11])],
      }),
    ).toThrow();
  });
});
