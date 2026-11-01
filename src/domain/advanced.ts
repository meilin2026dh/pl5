import { structure } from "./structure";
import { digitClass, gcd, lcm, inversionCount, mathClassCounts } from "./math";
import type { FilterInput, Rule, HistoryRecord } from "./pick5";
export const advancedLabels = {
  ac: "AC差值复杂度",
  largeGaps: "大间距个数",
  gapPattern: "排序间距形态",
  mathPrimePattern: "数学质合形态",
  mathClassCounts: "数学质合分布",
  sumModulo: "和值取模",
  productTail: "五位乘积尾数",
  inversions: "排列逆序数",
  digitGcd: "五位最大公约数",
  digitLcm: "五位最小公倍数",
  pairGcd: "两码最大公约数",
  pairLcm: "两码最小公倍数",
  danGroups: "分组胆码",
  oddPattern: "奇偶形态",
  bigPattern: "大小形态",
  primePattern: "质合形态",
  routeCounts: "012路个数",
  routePattern: "012路形态",
  positionDiff: "位置差",
  positionTrend: "位置升平降",
  max: "最大值",
  min: "最小值",
  median: "中位数",
  mean: "平均值",
  pairSum: "两码和",
  pairDiff: "两码差",
  pairTail: "两码和尾",
  pairProductTail: "两码积尾",
  classSum: "分类和值",
  remainderSum: "余数和",
  partition: "自定义分区",
  historyExclude: "历史号码排除",
  samePosition: "同位重号",
  historyOverlap: "不定位重号",
  neighborCounts: "重邻孤",
  historyDelta: "历史指标差",
  omission: "当前遗漏",
  frequency: "窗口频次",
} as const;
export type AdvancedKind = keyof typeof advancedLabels;
export const advancedKinds = Object.keys(advancedLabels) as AdvancedKind[];
const historical = new Set([
  "historyExclude",
  "samePosition",
  "historyOverlap",
  "neighborCounts",
  "historyDelta",
  "omission",
  "frequency",
]);
const primes = [1, 2, 3, 5, 7];
const integer = (v: unknown, min: number, max: number) =>
  typeof v === "number" && Number.isInteger(v) && v >= min && v <= max;
function fail(message: string): never {
  throw new Error(message);
}
function snapshot(rule: Rule, input: FilterInput): HistoryRecord[] {
  if (!Array.isArray(input.history) || !input.history.length)
    return fail("历史过滤需要非空历史快照");
  const issues = new Set<string>(),
    dates = new Set<string>();
  for (const row of input.history) {
    if (
      !row ||
      typeof row.issue !== "string" ||
      !row.issue.trim() ||
      typeof row.date !== "string" ||
      !/^\d{4}-\d{2}-\d{2}$/.test(row.date) ||
      !Number.isFinite(Date.parse(row.date)) ||
      new Date(row.date).toISOString().slice(0, 10) !== row.date ||
      typeof row.number !== "string" ||
      !/^\d{5}$/.test(row.number) ||
      issues.has(row.issue) ||
      dates.has(row.date)
    )
      fail("历史快照格式错误或期号日期重复");
    issues.add(row.issue);
    dates.add(row.date);
  }
  let rows = [...input.history].sort(
    (a, b) => a.date.localeCompare(b.date) || a.issue.localeCompare(b.issue),
  );
  if (rule.params?.referenceIssue) {
    const i = rows.findIndex(
      (row) => row.issue === rule.params!.referenceIssue,
    );
    if (i < 0) fail("参考期不在历史快照中");
    rows = rows.slice(0, i + 1);
  }
  if (rule.params?.startIssue) {
    const i = rows.findIndex((row) => row.issue === rule.params!.startIssue);
    if (i < 0) fail("历史起始期不在参考快照中");
    rows = rows.slice(i);
  }
  return rows;
}
export function validateAdvanced(input: FilterInput): void {
  if (
    input.candidates !== undefined &&
    (!Array.isArray(input.candidates) ||
      input.candidates.length === 0 ||
      input.candidates.length > 100000 ||
      input.candidates.some((n) => typeof n !== "string" || !/^\d{5}$/.test(n)))
  )
    fail("外部号码必须为五位数字且不超过100000条");
  if (input.combination !== undefined) {
    const c = input.combination;
    if (
      !c ||
      !["strict", "atLeast", "violations"].includes(c.mode) ||
      !integer(
        c.minimum,
        0,
        c.mode !== "atLeast"
          ? Number.MAX_SAFE_INTEGER
          : new Set(
              input.rules.filter((r) => r?.enabled).map((r) => r.group ?? r.id),
            ).size,
      )
    )
      fail("容错组合最少组数不合法");
    if (c.mode === "violations" && !integer(c.maxViolations, 0, 1000))
      fail("逐条违规预算须为0至1000整数");
  }
  for (const r of input.rules) {
    if (!r || !Object.hasOwn(advancedLabels, r.kind)) continue;
    if (
      !Array.isArray(r.values) ||
      r.values.some(
        (v) =>
          typeof v !== "string" &&
          !(typeof v === "number" && Number.isFinite(v)),
      )
    )
      fail("规则值必须是有限数值或字符串");
    if (
      r.group !== undefined &&
      (typeof r.group !== "string" || !r.group.trim())
    )
      fail("规则组名不合法");
    if (!r.enabled) continue;
    if (r.params === null) fail("规则参数格式错误");
    const p = r.params ?? {};
    if (typeof p !== "object" || Array.isArray(p)) fail("规则参数格式错误");
    if (
      p.positions !== undefined &&
      (!Array.isArray(p.positions) ||
        !p.positions.length ||
        p.positions.some((v) => !integer(v, 0, 4)) ||
        new Set(p.positions).size !== p.positions.length)
    )
      fail("位置必须为不重复的0至4索引");
    if (
      ["positionDiff", "positionTrend"].includes(r.kind) &&
      p.positions?.length !== 2
    )
      fail("必须选择两个位置");
    if (r.kind === "positionTrend" && p.positions![1] !== p.positions![0]! + 1)
      fail("升平降必须选择相邻位置");
    if (["omission", "frequency"].includes(r.kind) && p.positions?.length !== 1)
      fail("请选择一个统计位置");
    if (
      r.kind.startsWith("pair") &&
      p.positions !== undefined &&
      p.positions.length !== 2
    )
      fail("两码规则必须选择两个位置");
    for (const key of ["countMin", "countMax"] as const)
      if (p[key] !== undefined && !integer(p[key], 0, 10))
        fail("匹配个数必须为0至10");
    if ((p.countMin ?? 0) > (p.countMax ?? 10))
      fail("匹配个数下限不能大于上限");
    if (p.window !== undefined && !integer(p.window, 1, 100000))
      fail("历史窗口必须为正整数");
    if (
      p.referenceIssue !== undefined &&
      (typeof p.referenceIssue !== "string" || !p.referenceIssue.trim())
    )
      fail("参考期号不合法");
    if (
      p.startIssue !== undefined &&
      (typeof p.startIssue !== "string" || !p.startIssue.trim())
    )
      fail("历史起始期不合法");
    if (p.absolute !== undefined && typeof p.absolute !== "boolean")
      fail("绝对值参数不合法");
    if (
      r.kind === "historyDelta" &&
      p.metric !== undefined &&
      !["sum", "span"].includes(p.metric)
    )
      fail("历史差指标不合法");
    if (
      ["largeGaps", "gapPattern"].includes(r.kind) &&
      !integer(p.gapThreshold, 1, 9)
    )
      fail("大间距下限必须为1至9整数");
    if (r.kind === "sumModulo" && !integer(p.modulus, 2, 100))
      fail("和值取模的模数必须为2至100的整数");
    if (r.kind === "remainderSum" && ![3, 4, 5].includes(p.modulus!))
      fail("余数和模数必须为3、4或5");
    if (
      r.kind === "classSum" &&
      !["big", "small", "odd", "even", "prime", "composite"].includes(p.class!)
    )
      fail("请选择合法数字分类");
    if (r.kind === "danGroups" || r.kind === "partition") {
      const groups = r.kind === "partition" ? p.partitions : p.groups;
      if (
        !Array.isArray(groups) ||
        !groups.length ||
        groups.some(
          (g) =>
            !Array.isArray(g) ||
            !g.length ||
            g.some((v) => !integer(v, 0, 9)) ||
            new Set(g).size !== g.length,
        )
      )
        fail("数字分组不合法");
      if (
        r.kind === "partition" &&
        (groups.flat().length !== 10 || new Set(groups.flat()).size !== 10)
      )
        fail("分区必须不重叠且覆盖0至9");
      if (
        p.counts !== undefined &&
        (!Array.isArray(p.counts) ||
          p.counts.length !== groups.length ||
          p.counts.some((v) => !integer(v, 0, 5)))
      )
        fail("分组个数不合法");
      if (
        r.kind === "partition" &&
        (!p.counts || p.counts.reduce((a, b) => a + b, 0) !== 5)
      )
        fail("分区个数合计必须为5");
    }
    const patterns: Partial<Record<Rule["kind"], RegExp>> = {
      gapPattern: /^[LS?]{4}$/,
      mathPrimePattern: /^[PCN?]{5}$/,
      mathClassCounts: /^[0-5]:[0-5]:[0-5]$/,
      oddPattern: /^[01?]{5}$/,
      bigPattern: /^[01?]{5}$/,
      primePattern: /^[01?]{5}$/,
      routePattern: /^[012?]{5}$/,
      routeCounts: /^\d:\d:\d$/,
      neighborCounts: /^\d:\d:\d$/,
    };
    const pattern = patterns[r.kind];
    for (const v of r.values) {
      if (pattern) {
        if (
          typeof v !== "string" ||
          !pattern.test(v) ||
          (["routeCounts", "neighborCounts", "mathClassCounts"].includes(
            r.kind,
          ) &&
            v.split(":").reduce((a, b) => a + Number(b), 0) !== 5)
        )
          fail("形态值格式错误");
      } else if (r.kind === "positionTrend") {
        if (!["up", "equal", "down"].includes(String(v))) fail("升平降值错误");
      } else if (
        !["historyExclude", "danGroups", "partition"].includes(r.kind)
      ) {
        const limits: Partial<Record<Rule["kind"], number>> = {
          ac: 5,
          largeGaps: 4,
          inversions: 10,
          digitLcm: 2520,
          pairLcm: 72,
          sum: 45,
          classSum: 45,
          pairSum: 18,
          remainderSum: 20,
          frequency: 100000,
          omission: 100000,
          samePosition: 5,
          historyOverlap: 5,
        };
        const max =
          r.kind === "sumModulo" ? p.modulus! - 1 : (limits[r.kind] ?? 9);
        if (
          typeof v !== "number" ||
          !Number.isFinite(v) ||
          (r.kind !== "mean" && !Number.isInteger(v)) ||
          (r.kind === "mean" && Math.abs(v * 5 - Math.round(v * 5)) > 1e-8) ||
          v > (r.kind === "historyDelta" ? 45 : max) ||
          v <
            (r.kind === "ac"
              ? -4
              : r.kind === "historyDelta" && p.absolute === false
                ? -45
                : 0)
        )
          fail("规则数值超出范围");
      }
    }
    if (historical.has(r.kind)) {
      const rows = snapshot(r, input);
      if (
        r.kind === "frequency" &&
        p.window !== undefined &&
        p.window > rows.length
      )
        fail("历史不足：窗口期数超过参考期以前的有效记录数");
    }
  }
}
export function advancedPredicate(
  rule: Rule,
  input: FilterInput,
): (number: string) => boolean {
  const p = rule.params ?? {},
    v = rule.values,
    rows = historical.has(rule.kind) ? snapshot(rule, input) : [],
    reference = rows.at(-1)?.number ?? "";
  const selected = rows.slice(-(p.window ?? rows.length));
  const sum = (d: number[]) => d.reduce((a, b) => a + b, 0),
    span = (d: number[]) => Math.max(...d) - Math.min(...d);
  const classify = (n: number) =>
    p.class === "big"
      ? n >= 5
      : p.class === "small"
        ? n < 5
        : p.class === "odd"
          ? n % 2 === 1
          : p.class === "even"
            ? n % 2 === 0
            : p.class === "prime"
              ? primes.includes(n)
              : !primes.includes(n);
  const ref = [...reference].map(Number);
  const referenceDigits = new Set(ref);
  const historyNumbers = new Set(selected.map((row) => row.number));
  const frequencies = Array(10).fill(0) as number[];
  const omission = Array(10).fill(-1) as number[];
  const position = p.positions?.[0] ?? 0;
  if (rule.kind === "frequency")
    for (const row of selected) frequencies[Number(row.number[position])]++;
  if (rule.kind === "omission") {
    for (let i = rows.length - 1; i >= 0; i--) {
      if (
        i < rows.length - 1 &&
        Date.parse(rows[i + 1].date) - Date.parse(rows[i].date) !== 86400000
      )
        break;
      const digit = Number(rows[i].number[position]);
      if (omission[digit] === -1) omission[digit] = rows.length - 1 - i;
    }
  }
  const pairPositions = p.positions
    ? [p.positions]
    : [0, 1, 2, 3, 4].flatMap((i) =>
        [0, 1, 2, 3, 4].filter((j) => j > i).map((j) => [i, j]),
      );
  return (number) => {
    const d = [...number].map(Number),
      sorted = [...d].sort((a, b) => a - b),
      kind = rule.kind;
    let value: number | string;
    if (kind === "danGroups")
      return p.groups!.every((g, i) => {
        const count = new Set(d.filter((n) => g.includes(n))).size;
        return p.counts
          ? count === p.counts[i]
          : count >= (p.countMin ?? 1) && count <= (p.countMax ?? g.length);
      });
    if (kind === "partition")
      return p.partitions!.every(
        (g, i) => d.filter((n) => g.includes(n)).length === p.counts![i],
      );
    if (kind === "historyExclude") return !historyNumbers.has(number);
    if (kind === "ac") value = structure(number, 3).ac;
    else if (kind === "largeGaps")
      value = structure(number, p.gapThreshold!).large;
    else if (kind === "gapPattern")
      value = structure(number, p.gapThreshold!)
        .gaps.map((g) => (g >= p.gapThreshold! ? "L" : "S"))
        .join("");
    else if (kind === "mathPrimePattern") value = d.map(digitClass).join("");
    else if (kind === "mathClassCounts") value = mathClassCounts(d);
    else if (kind === "sumModulo") value = sum(d) % p.modulus!;
    else if (kind === "productTail")
      value = d.reduce((a, b) => (a * b) % 10, 1);
    else if (kind === "inversions") value = inversionCount(d);
    else if (kind === "digitGcd") value = d.reduce(gcd, 0);
    else if (kind === "digitLcm") value = d.reduce(lcm, 1);
    else if (kind === "oddPattern") value = d.map((n) => n % 2).join("");
    else if (kind === "bigPattern")
      value = d.map((n) => Number(n >= 5)).join("");
    else if (kind === "primePattern")
      value = d.map((n) => Number(primes.includes(n))).join("");
    else if (kind === "routePattern") value = d.map((n) => n % 3).join("");
    else if (kind === "routeCounts")
      value = [0, 1, 2]
        .map((r) => d.filter((n) => n % 3 === r).length)
        .join(":");
    else if (kind === "positionDiff")
      value = Math.abs(d[p.positions![0]!]! - d[p.positions![1]!]!);
    else if (kind === "positionTrend") {
      const diff = d[p.positions![1]!]! - d[p.positions![0]!]!;
      value = diff > 0 ? "up" : diff < 0 ? "down" : "equal";
    } else if (kind === "max") value = sorted[4]!;
    else if (kind === "min") value = sorted[0]!;
    else if (kind === "median") value = sorted[2]!;
    else if (kind === "mean")
      return v.some(
        (n) => typeof n === "number" && Math.abs(n * 5 - sum(d)) < 1e-8,
      );
    else if (kind.startsWith("pair")) {
      const pairs = pairPositions;
      const count = pairs.filter((pair) => {
        const a = d[pair[0]!]!,
          b = d[pair[1]!]!;
        let pairValue: number;
        switch (kind) {
          case "pairGcd":
            pairValue = gcd(a, b);
            break;
          case "pairLcm":
            pairValue = lcm(a, b);
            break;
          case "pairSum":
            pairValue = a + b;
            break;
          case "pairDiff":
            pairValue = Math.abs(a - b);
            break;
          case "pairTail":
            pairValue = (a + b) % 10;
            break;
          default:
            pairValue = (a * b) % 10;
        }
        return v.includes(pairValue);
      }).length;
      return (
        count >= (p.countMin ?? 1) && count <= (p.countMax ?? pairs.length)
      );
    } else if (kind === "classSum") value = sum(d.filter(classify));
    else if (kind === "remainderSum") value = sum(d.map((n) => n % p.modulus!));
    else if (kind === "samePosition")
      value = d.filter((n, i) => n === ref[i]).length;
    else if (kind === "historyOverlap") {
      value = [...new Set(d)].filter((n) => referenceDigits.has(n)).length;
    } else if (kind === "neighborCounts") {
      let repeat = 0,
        neighbor = 0;
      d.forEach((n) => {
        if (referenceDigits.has(n)) repeat++;
        else if (
          [...referenceDigits].some((value) => Math.abs(n - value) === 1)
        )
          neighbor++;
      });
      value = [repeat, neighbor, 5 - repeat - neighbor].join(":");
    } else if (kind === "historyDelta") {
      const delta =
        p.metric === "span" ? span(d) - span(ref) : sum(d) - sum(ref);
      value = p.absolute === false ? delta : Math.abs(delta);
    } else if (kind === "frequency") value = frequencies[d[position]];
    else if (kind === "omission") {
      const index = omission[d[position]];
      if (index < 0) fail("历史不足：该数字未出现，无法确定当前遗漏边界");
      value = index;
    } else return false;
    if (
      [
        "gapPattern",
        "mathPrimePattern",
        "oddPattern",
        "bigPattern",
        "primePattern",
        "routePattern",
      ].includes(kind)
    )
      return v.some(
        (pattern) =>
          typeof pattern === "string" &&
          [...pattern].every((c, i) => c === "?" || c === String(value)[i]),
      );
    return v.includes(value);
  };
}

/** Legal starting values for the advanced rule editor; all rules remain opt-in. */
export const advancedDefaults: Record<
  AdvancedKind,
  { values: (number | string)[]; params?: Rule["params"] }
> = {
  ac: { values: [0, 1, 2, 3, 4, 5] },
  largeGaps: { values: [2], params: { gapThreshold: 3 } },
  gapPattern: { values: ["SSLL"], params: { gapThreshold: 3 } },
  mathPrimePattern: { values: ["?PP?P"] },
  mathClassCounts: { values: ["3:1:1"] },
  sumModulo: { values: [0], params: { modulus: 5 } },
  productTail: { values: [0] },
  inversions: { values: [0] },
  digitGcd: { values: [1] },
  digitLcm: { values: [60] },
  pairGcd: { values: [1], params: { countMin: 1, countMax: 10 } },
  pairLcm: { values: [6], params: { countMin: 1, countMax: 10 } },
  danGroups: {
    values: [],
    params: {
      groups: [
        [1, 2],
        [3, 4],
      ],
      countMin: 1,
      countMax: 2,
    },
  },
  oddPattern: { values: ["10101"] },
  bigPattern: { values: ["00111"] },
  primePattern: { values: ["11101"] },
  routeCounts: { values: ["2:2:1"] },
  routePattern: { values: ["01201"] },
  positionDiff: { values: [1], params: { positions: [0, 1] } },
  positionTrend: { values: ["up"], params: { positions: [0, 1] } },
  max: { values: [9] },
  min: { values: [0] },
  median: { values: [4] },
  mean: { values: [4.4] },
  pairSum: { values: [9], params: { countMin: 1, countMax: 10 } },
  pairDiff: { values: [1], params: { countMin: 1, countMax: 10 } },
  pairTail: { values: [9], params: { countMin: 1, countMax: 10 } },
  pairProductTail: { values: [0], params: { countMin: 1, countMax: 10 } },
  classSum: { values: [15], params: { class: "odd" } },
  remainderSum: { values: [5], params: { modulus: 3 } },
  partition: {
    values: [],
    params: {
      partitions: [
        [0, 1, 2, 3, 4],
        [5, 6, 7, 8, 9],
      ],
      counts: [2, 3],
    },
  },
  historyExclude: { values: [] },
  samePosition: { values: [1] },
  historyOverlap: { values: [2] },
  neighborCounts: { values: ["1:2:2"] },
  historyDelta: { values: [0], params: { metric: "sum", absolute: true } },
  omission: { values: [0], params: { positions: [0] } },
  frequency: { values: [3], params: { positions: [0], window: 30 } },
};
