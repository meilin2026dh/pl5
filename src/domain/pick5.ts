import { validateLab, type LabConfig } from "./lab/config";
import {
  validateProbability,
  type ProbabilityConfig,
} from "./probability/config";
import { validateEvidence, type EvidenceConfig } from "./evidence/config";
import { validateInnovation, type InnovationConfig } from "./innovation/config";
import { validateAudit, type AuditConfig } from "./audit/config";
import { validateSelection, type SelectionConfig } from "./selection/config";
import {
  prepareRelation,
  validateRelation,
  type RelationConfig,
} from "./relations";
import {
  prepareGeometry,
  validateGeometry,
  geometryHistory,
  type GeometryConfig,
} from "./geometry";
import {
  prepareResearch,
  validateResearchConfig,
  researchHistory,
} from "./research";
import type { ResearchConfig, ResearchDiagnostics } from "./research/types";
import {
  advancedLabels,
  validateAdvanced,
  advancedPredicate,
  type AdvancedKind,
} from "./advanced";
/** Digit positions are 万、千、百、十、个. Leading zeroes are significant. */
export type Metrics = {
  sum: number;
  tail: number;
  span: number;
  odd: number;
  big: number;
  prime: number;
  distinct: number;
  repeat: string;
  consecutive: number;
  sumMod3: number;
};
export type RuleKind =
  | "relation"
  | "geometry"
  | "research"
  | AdvancedKind
  | "sum"
  | "tail"
  | "span"
  | "odd"
  | "big"
  | "prime"
  | "distinct"
  | "repeat"
  | "consecutive"
  | "sumMod3"
  | "dan"
  | "kill";
export type Rule = {
  id: string;
  kind: RuleKind;
  enabled: boolean;
  mode: "include" | "exclude";
  values: (number | string)[];
  group?: string;
  research?: ResearchConfig;
  geometry?: GeometryConfig;
  relation?: RelationConfig;
  params?: {
    positions?: number[];
    groups?: number[][];
    counts?: number[];
    countMin?: number;
    countMax?: number;
    modulus?: number;
    gapThreshold?: number;
    class?: "big" | "small" | "odd" | "even" | "prime" | "composite";
    partitions?: number[][];
    referenceIssue?: string;
    startIssue?: string;
    metric?: "sum" | "span";
    absolute?: boolean;
    window?: number;
  };
};
export type HistoryRecord = { issue: string; date: string; number: string };
export type FilterInput = {
  lab?: LabConfig;
  probability?: ProbabilityConfig;
  evidence?: EvidenceConfig;
  innovation?: InnovationConfig;
  audit?: AuditConfig;
  selection?: SelectionConfig;
  positions: number[][];
  rules: Rule[];
  candidates?: string[];
  history?: HistoryRecord[];
  historySource?: string;
  combination?: {
    mode: "strict" | "atLeast" | "violations";
    minimum: number;
    maxViolations?: number;
  };
};
export type FilterResult = {
  research?: { id: string; label: string; diagnostics: ResearchDiagnostics }[];
  numbers: string[];
  initial: number;
  steps: { id: string; label: string; before: number; after: number }[];
};

export const ruleLabels: Record<RuleKind, string> = {
  ...advancedLabels,
  research: "实验方法",
  geometry: "空间形态",
  relation: "跨期关联",
  sum: "和值",
  tail: "和尾",
  span: "跨度",
  odd: "奇数个数",
  big: "大数个数",
  prime: "质数个数",
  distinct: "不同数字个数",
  repeat: "重复形态",
  consecutive: "连号对数",
  sumMod3: "和值余3",
  dan: "胆码",
  kill: "杀号",
};
const digitValues = () => Array.from({ length: 10 }, (_, i) => i);
export function defaultPositions(): number[][] {
  return Array.from({ length: 5 }, digitValues);
}
export function defaultRules(): Rule[] {
  return (
    [
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
      "dan",
      "kill",
    ] as RuleKind[]
  ).map((kind) => ({
    id: kind,
    kind,
    enabled: false,
    mode: "include",
    values: [],
  }));
}

export function metrics(number: string): Metrics {
  if (typeof number !== "string" || !/^\d{5}$/.test(number))
    throw new Error("号码必须是五位数字，前导零需保留");
  const digits = [...number].map(Number);
  const sum = digits.reduce((a, b) => a + b, 0);
  const unique = [...new Set(digits)].sort((a, b) => a - b);
  const counts = new Map<number, number>();
  for (const digit of digits) counts.set(digit, (counts.get(digit) ?? 0) + 1);
  return {
    sum,
    tail: sum % 10,
    span: unique[unique.length - 1]! - unique[0]!,
    odd: digits.filter((d) => d % 2 === 1).length,
    big: digits.filter((d) => d >= 5).length,
    // Lottery digit convention includes 1; it is not the mathematical prime set.
    prime: digits.filter((d) => [1, 2, 3, 5, 7].includes(d)).length,
    distinct: unique.length,
    repeat: [...counts.values()].sort((a, b) => b - a).join(""),
    // Count adjacent distinct sorted values, never wrap 9 to 0.
    consecutive: unique.slice(1).filter((d, i) => d - unique[i]! === 1).length,
    sumMod3: sum % 3,
  };
}

const ranges: Partial<Record<RuleKind, [number, number]>> = {
  sum: [0, 45],
  tail: [0, 9],
  span: [0, 9],
  odd: [0, 5],
  big: [0, 5],
  prime: [0, 5],
  distinct: [1, 5],
  consecutive: [0, 4],
  sumMod3: [0, 2],
  dan: [0, 9],
  kill: [0, 9],
};
const repeatShapes = ["5", "41", "32", "311", "221", "2111", "11111"];

export function validateInput(input: FilterInput): void {
  if (!input || !Array.isArray(input.positions) || input.positions.length !== 5)
    throw new Error("必须设置五个位置");
  if (input.lab !== undefined) validateLab(input.lab);
  if (input.probability !== undefined) validateProbability(input.probability);
  if (input.evidence !== undefined) validateEvidence(input.evidence);
  if (input.innovation !== undefined) validateInnovation(input.innovation);
  if (input.selection !== undefined) validateSelection(input.selection);
  if (input.audit !== undefined) validateAudit(input.audit);
  for (const values of input.positions) {
    if (!Array.isArray(values) || values.length === 0)
      throw new Error("每个位置至少选择一个数字");
    if (values.some((v) => !Number.isInteger(v) || v < 0 || v > 9))
      throw new Error("位置数字必须为0至9的整数");
    if (new Set(values).size !== values.length)
      throw new Error("位置数字不能重复");
  }
  if (!Array.isArray(input.rules)) throw new Error("过滤规则格式错误");
  validateAdvanced(input);
  const ids = new Set<string>();
  for (const rule of input.rules) {
    if (
      !rule ||
      typeof rule.id !== "string" ||
      !rule.id.trim() ||
      ids.has(rule.id)
    )
      throw new Error("规则标识必须唯一且非空");
    ids.add(rule.id);
    if (
      rule.group !== undefined &&
      (typeof rule.group !== "string" || !rule.group.trim())
    )
      throw new Error("规则组名不合法");
    if (
      !Object.hasOwn(ruleLabels, rule.kind) ||
      typeof rule.enabled !== "boolean" ||
      !["include", "exclude"].includes(rule.mode) ||
      !Array.isArray(rule.values)
    )
      throw new Error("过滤规则格式错误");
    if (
      rule.enabled &&
      rule.values.length === 0 &&
      ![
        "historyExclude",
        "danGroups",
        "partition",
        "research",
        "geometry",
        "relation",
      ].includes(rule.kind)
    )
      throw new Error(`${ruleLabels[rule.kind]}至少选择一个值`);
    if (rule.kind === "relation") {
      validateRelation(rule.relation);
      if (rule.enabled) prepareRelation(rule.relation, input.history);
      continue;
    }
    if (rule.kind === "geometry") {
      validateGeometry(rule.geometry);
      if (rule.enabled) geometryHistory(rule.geometry, input.history);
      continue;
    }
    if (rule.kind === "research") {
      validateResearchConfig(rule.research);
      if (rule.enabled) researchHistory(rule.research, input.history);
      continue;
    }
    if (rule.kind === "dan" && rule.params !== undefined) {
      const p = rule.params;
      if (
        !p ||
        typeof p !== "object" ||
        [p.countMin ?? 1, p.countMax ?? 5].some(
          (n) => !Number.isInteger(n) || n < 0 || n > 5,
        ) ||
        (p.countMin ?? 1) > (p.countMax ?? 5)
      )
        throw new Error("胆码命中种数范围必须在0至5之间");
    }
    if (Object.hasOwn(advancedLabels, rule.kind)) continue;
    for (const value of rule.values) {
      if (rule.kind === "repeat") {
        if (typeof value !== "string" || !repeatShapes.includes(value))
          throw new Error("重复形态不合法");
      } else {
        const [min, max] = ranges[rule.kind]!;
        if (
          typeof value !== "number" ||
          !Number.isInteger(value) ||
          value < min ||
          value > max
        )
          throw new Error(`${ruleLabels[rule.kind]}数值超出范围`);
      }
    }
  }
}

/** Rules combine by AND; selected values within a rule combine by OR.
 * 胆码: at least one selected digit occurs. 杀号: none of the selected digits occurs.
 * Exclude inverts the complete predicate, for every kind including 胆码 and 杀号.
 */
export function filter(input: FilterInput): FilterResult {
  validateInput(input);
  const rules = input.rules.filter((rule) => rule.enabled);
  const steps = rules.map((rule) => ({
    id: rule.id,
    label: ruleLabels[rule.kind],
    before: 0,
    after: 0,
  }));
  const positions = input.positions.map((values) =>
    [...values].sort((a, b) => a - b),
  );
  const candidates = input.candidates
    ? [...new Set(input.candidates)].sort()
    : undefined;
  const initial =
    candidates?.length ??
    positions.reduce((total, values) => total * values.length, 1);
  const soft = input.combination?.mode === "violations";
  const tolerant = input.combination?.mode === "atLeast" || soft;
  const research = rules
    .filter(
      (rule) =>
        rule.kind === "research" ||
        rule.kind === "geometry" ||
        rule.kind === "relation",
    )
    .map((rule) => ({
      id: rule.id,
      label: ruleLabels[rule.kind],
      prepared:
        rule.kind === "relation"
          ? prepareRelation(rule.relation!, input.history)
          : rule.kind === "geometry"
            ? prepareGeometry(rule.geometry!, input.history)
            : prepareResearch(rule.research!, input.history),
    }));
  const researchDiagnostics = research.map(({ id, label, prepared }) => ({
    id,
    label,
    diagnostics: prepared.diagnostics,
  }));
  const predicates = rules.map((rule) =>
    rule.kind === "research" ||
    rule.kind === "geometry" ||
    rule.kind === "relation"
      ? research.find((r) => r.id === rule.id)!.prepared.test
      : Object.hasOwn(advancedLabels, rule.kind)
        ? advancedPredicate(rule, input)
        : undefined,
  );
  const numbers: string[] = [];
  // One metrics calculation per candidate, regardless of the number of active rules.
  const needsMetrics = rules.some(
    (rule, index) =>
      !predicates[index] && rule.kind !== "dan" && rule.kind !== "kill",
  );
  function visit(prefix: string, position: number): void {
    if (position < 5) {
      for (const value of positions[position]!)
        visit(prefix + value, position + 1);
      return;
    }
    const values = needsMetrics ? metrics(prefix) : undefined;
    const groups = new Map<string, boolean>();
    let violations = 0;
    for (let index = 0; index < rules.length; index++) {
      const rule = rules[index]!;
      const step = steps[index]!;
      step.before++;
      let pass: boolean;
      if (predicates[index]) {
        pass = predicates[index]!(prefix);
      } else if (rule.kind === "dan" || rule.kind === "kill") {
        const contains = rule.values.some((value) =>
          prefix.includes(String(value)),
        );
        const distinctHits = [...new Set(rule.values)].filter((value) =>
          prefix.includes(String(value)),
        ).length;
        pass =
          rule.kind === "dan"
            ? distinctHits >= (rule.params?.countMin ?? 1) &&
              distinctHits <= (rule.params?.countMax ?? 5)
            : !contains;
      } else {
        pass = rule.values.includes(values![rule.kind as keyof Metrics]);
      }
      if (rule.mode === "exclude") pass = !pass;
      if (soft) {
        violations += Number(!pass);
        continue;
      }
      if (tolerant) {
        const key = rule.group ?? rule.id;
        groups.set(key, (groups.get(key) ?? true) && pass);
        continue;
      }
      if (!pass) return;
      step.after++;
    }
    if (
      !soft &&
      tolerant &&
      [...groups.values()].filter(Boolean).length < input.combination!.minimum
    )
      return;
    if (soft && violations > input.combination!.maxViolations!) return;
    numbers.push(prefix);
  }
  if (candidates) candidates.forEach((candidate) => visit(candidate, 5));
  else visit("", 0);
  if (tolerant)
    return {
      numbers,
      initial,
      research: researchDiagnostics,
      steps: [
        {
          id: "combination",
          label: soft ? "逐条违规预算" : "容错组合",
          before: initial,
          after: numbers.length,
        },
      ],
    };
  return { numbers, initial, steps, research: researchDiagnostics };
}
