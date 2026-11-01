import PotentialEditor from "./PotentialEditor";
import { defaultPotential } from "../domain/research/potential";
import { researchHistory } from "../domain/research/statistics";
import { useState, useEffect, type ReactNode } from "react";
import type { FilterInput, FilterResult, Rule } from "../domain/pick5";
import {
  defaultResearch,
  filterMethods,
  scoreMethods,
  researchLabels,
  type ResearchConfig,
  type ResearchMethod,
  type FilterMethod,
} from "../domain/research/types";
import { validateResearchConfig } from "../domain/research/config";

function parameterFor(method: ResearchMethod): number {
  if (method === "hotcold") return 7;
  if (method === "omission") return 20;
  if (method === "multiset") return 1;
  if (method === "samePosition" || method === "positionNeighbor") return 2;
  if (method === "sumSigma") return 2;
  if (method === "sumQuantile" || method === "spanQuantile") return 0.9;
  return 0.02;
}
const parameterHelp: Partial<Record<ResearchMethod, string>> = {
  hotcold: "每个位置保留频次最高的 K 个数字（1—10）",
  omission: "每个位置的遗漏期数上限",
  bayes: "逐位平滑概率下限（0—1）",
  markov: "逐位转移概率下限（0—1）",
  sumSigma: "距历史均值的标准差倍数",
  sumQuantile: "中心区间覆盖比例（0—1）",
  spanQuantile: "中心区间覆盖比例（0—1）",
  samePosition: "与上一期同位置相同数字的个数上限",
  positionNeighbor: "与上一期同位置距离不超过1的个数上限",
  multiset: "排序数字多重集在历史中出现次数下限",
};
export default function ResearchRules({
  input,
  onChange,
}: {
  input: FilterInput;
  onChange: (input: FilterInput) => void;
}) {
  const [draft, setDraft] = useState<Rule | null>(null);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<{ id: string; stamp: string } | null>(
    null,
  );
  const signature = (rule: Rule) =>
    JSON.stringify({ ...rule, enabled: undefined });
  useEffect(() => {
    if (!editing) return;
    const latest = input.rules.find((r) => r.id === editing.id);
    if (!latest || signature(latest) !== editing.stamp) {
      setDraft(null);
      setEditing(null);
      setError("原条件已改变或移除，请重新编辑。");
    }
  }, [input.rules, editing]);
  const config = draft?.research;
  const patch = (update: Partial<ResearchConfig>) =>
    setDraft((d) => d && { ...d, research: { ...d.research!, ...update } });
  const start = (rule?: Rule) => {
    setEditing(rule ? { id: rule.id, stamp: signature(rule) } : null);
    setDraft(
      rule
        ? { ...rule, research: { ...rule.research! } }
        : {
            id: crypto.randomUUID(),
            kind: "research",
            enabled: true,
            mode: "include",
            values: [],
            research: { ...defaultResearch },
          },
    );
    setError("");
  };
  const save = () => {
    if (!draft || !config) return;
    try {
      const latest = editing
        ? input.rules.find((r) => r.id === editing.id)
        : undefined;
      if (editing && (!latest || signature(latest) !== editing.stamp))
        throw new Error("原条件已改变或移除，请重新编辑。");
      const saved = latest ? { ...draft, enabled: latest.enabled } : draft;
      validateResearchConfig(config);
      researchHistory(config, input.history);
      onChange({
        ...input,
        rules: input.rules.some((r) => r.id === draft.id)
          ? input.rules.map((r) => (r.id === draft.id ? saved : r))
          : [...input.rules, saved],
      });
      setDraft(null);
      setEditing(null);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "实验参数错误");
    }
  };
  const numeric = (
    label: string,
    key: {
      [K in keyof ResearchConfig]: ResearchConfig[K] extends number ? K : never;
    }[keyof ResearchConfig] &
      string,
    value: number,
    min: number,
    max: number,
    step = 1,
    percent = false,
  ) => (
    <label>
      {label}
      <input
        aria-label={label}
        type="number"
        min={min}
        max={max}
        step={step}
        value={Number.isFinite(value) ? value : ""}
        onChange={(e) =>
          patch({
            [key]:
              e.target.value === ""
                ? NaN
                : Number(e.target.value) / (percent ? 100 : 1),
          })
        }
      />
    </label>
  );
  const scoring =
    config &&
    scoreMethods.includes(config.method as (typeof scoreMethods)[number]);
  return (
    <section className="research-card" aria-labelledby="research-title">
      <header>
        <div>
          <span className="research-kicker">RESEARCH LAB</span>
          <h2 id="research-title">实验方法</h2>
        </div>
        <button type="button" onClick={() => start()}>
          添加实验方法
        </button>
      </header>
      <p className="research-context">
        历史来源：{input.historySource || "未载入"} ·{" "}
        {input.history?.length ?? 0}
        期。点击开始缩水后按所选窗口计算；实验方法不代表预测优势。
      </p>
      <ul className="research-rules">
        {input.rules
          .filter((r) => r.kind === "research" && r.research)
          .map((r) => (
            <li key={r.id}>
              <label>
                <input
                  type="checkbox"
                  checked={r.enabled}
                  onChange={(e) =>
                    onChange({
                      ...input,
                      rules: input.rules.map((x) =>
                        x.id === r.id ? { ...x, enabled: e.target.checked } : x,
                      ),
                    })
                  }
                />
                {researchLabels[r.research!.method]}
              </label>
              <span>
                {r.mode === "exclude" ? "排除" : "包含"} · 最近
                {r.research!.window}期{r.group ? ` · 组 ${r.group}` : ""}
              </span>
              <button
                type="button"
                aria-label={`编辑 ${researchLabels[r.research!.method]}`}
                onClick={() => start(r)}
              >
                编辑
              </button>
              <button
                type="button"
                aria-label={`删除 ${researchLabels[r.research!.method]}`}
                onClick={() => {
                  onChange({
                    ...input,
                    rules: input.rules.filter((x) => x.id !== r.id),
                  });
                  if (draft?.id === r.id) {
                    setDraft(null);
                    setEditing(null);
                    setError("");
                  }
                }}
              >
                删除
              </button>
            </li>
          ))}
      </ul>
      {!draft && error && (
        <p role="alert" className="research-error">
          {error}
        </p>
      )}
      {draft && config && (
        <div className="research-editor">
          <h3>
            {input.rules.some((r) => r.id === draft.id)
              ? "编辑实验条件"
              : "新建实验条件"}
          </h3>
          <div className="research-fields">
            <label>
              实验方法
              <select
                aria-label="实验方法"
                value={config.method}
                onChange={(e) => {
                  const method = e.target.value as ResearchMethod;
                  patch({
                    method,
                    ...(method === "potential"
                      ? {
                          potential: config.potential ?? {
                            ...defaultPotential,
                          },
                        }
                      : {}),
                    parameter: parameterFor(
                      method === "auto" ? config.family : method,
                    ),
                  });
                }}
              >
                <optgroup label="统计过滤">
                  {filterMethods.map((m) => (
                    <option key={m} value={m}>
                      {researchLabels[m]}
                    </option>
                  ))}
                </optgroup>
                <optgroup label="排名评分">
                  {scoreMethods.map((m) => (
                    <option key={m} value={m}>
                      {researchLabels[m]}
                    </option>
                  ))}
                </optgroup>
                <optgroup label="选择与组合">
                  {(["auto", "greedy", "preset"] as const).map((m) => (
                    <option key={m} value={m}>
                      {researchLabels[m]}
                    </option>
                  ))}
                </optgroup>
              </select>
            </label>
            {numeric("历史窗口（期）", "window", config.window, 1, 100000)}
            <label>
              参考期（留空为最新）
              <input
                aria-label="参考期（留空为最新）"
                value={config.referenceIssue ?? ""}
                placeholder="例如 20260200"
                onChange={(e) =>
                  patch({ referenceIssue: e.target.value.trim() || undefined })
                }
              />
            </label>
            {!scoring &&
              !["auto", "greedy", "preset"].includes(config.method) &&
              numeric(
                "方法参数",
                "parameter",
                config.parameter,
                0,
                100000,
                0.001,
              )}
            {config.method === "auto" && (
              <>
                <label>
                  自动选择方法族
                  <select
                    aria-label="自动选择方法族"
                    value={config.family}
                    onChange={(e) => {
                      const family = e.target.value as FilterMethod;
                      patch({ family, parameter: parameterFor(family) });
                    }}
                  >
                    {filterMethods.map((m) => (
                      <option key={m} value={m}>
                        {researchLabels[m]}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  选择标准
                  <select
                    aria-label="选择标准"
                    value={config.selection}
                    onChange={(e) =>
                      patch({
                        selection: e.target
                          .value as ResearchConfig["selection"],
                      })
                    }
                  >
                    <option value="lift60">覆盖≥60%，提升比优先</option>
                    <option value="cov90">覆盖≥90%，集合最小</option>
                    <option value="strict">验证全中，集合最小</option>
                  </select>
                </label>
              </>
            )}
            {(config.method === "auto" || config.method === "greedy") && (
              <>
                {numeric("滚动验证折数", "folds", config.folds, 1, 5)}
                {numeric(
                  "每折验证期数",
                  "validationSize",
                  config.validationSize,
                  1,
                  200,
                )}
              </>
            )}
            {config.method === "greedy" && (
              <>
                {numeric(
                  "目标覆盖率（%）",
                  "targetCoverage",
                  config.targetCoverage * 100,
                  0,
                  100,
                  0.1,
                  true,
                )}
                {numeric("最多组合条件", "maxSteps", config.maxSteps, 1, 8)}
              </>
            )}
            {scoring && (
              <>
                {numeric(
                  "保留比例（%）",
                  "retain",
                  config.retain * 100,
                  0.001,
                  100,
                  0.1,
                  true,
                )}
                <label>
                  并列策略
                  <select
                    aria-label="并列策略"
                    value={config.ties}
                    onChange={(e) =>
                      patch({ ties: e.target.value as ResearchConfig["ties"] })
                    }
                  >
                    <option value="inclusive">保留边界全部并列</option>
                    <option value="seeded">固定种子精确保留</option>
                  </select>
                </label>
                {config.ties === "seeded" &&
                  numeric("随机种子", "seed", config.seed, 0, 4294967295)}
                {config.method === "dsDempster" &&
                  numeric("证据分窗数量", "windows", config.windows, 2, 20)}
              </>
            )}
            {config.method === "preset" && (
              <label>
                固定组合包
                <select
                  aria-label="固定组合包"
                  value={config.preset}
                  onChange={(e) =>
                    patch({
                      preset: e.target.value as ResearchConfig["preset"],
                    })
                  }
                >
                  {["A", "B", "C", "D", "E", "F"].map((p) => (
                    <option key={p} value={p}>
                      组合包 {p}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label>
              规则模式
              <select
                aria-label="规则模式"
                value={draft.mode}
                onChange={(e) =>
                  setDraft({ ...draft, mode: e.target.value as Rule["mode"] })
                }
              >
                <option value="include">包含符合项</option>
                <option value="exclude">排除符合项</option>
              </select>
            </label>
            <label>
              容错分组（可选）
              <input
                aria-label="容错分组（可选）"
                value={draft.group ?? ""}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    group: e.target.value.trim() || undefined,
                  })
                }
              />
            </label>
          </div>
          {config.method === "potential" && (
            <PotentialEditor
              config={config}
              history={input.history}
              onChange={(potential) => patch({ potential })}
            />
          )}
          <p className="research-context">
            {parameterHelp[config.method] ??
              (filterMethods.includes(config.method as FilterMethod)
                ? "历史形态出现频率下限（0—1）"
                : "排名始终以完整10万组为基准。滚动验证只使用验证期之前的训练数据。")}
          </p>
          {error && (
            <p role="alert" className="research-error">
              {error}
            </p>
          )}
          <div className="research-actions">
            <button type="button" onClick={save}>
              保存实验条件
            </button>
            <button
              type="button"
              onClick={() => {
                setDraft(null);
                setEditing(null);
                setError("");
              }}
            >
              取消
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
const diagnosticLabels: Record<string, string> = {
  potentialConfig: "势能参数",
  blockIssues: "分窗截止期",
  signals: "逐位势能明细",
  position: "位置",
  digits: "数字信号",
  digit: "数字",
  recentRate: "短窗频率",
  baselineRate: "此前基线",
  band: "动态带宽",
  z: "标准偏离",
  momentum: "势能变化",
  crossing: "临界转换",
  alternation: "交替比例",
  states: "冷热序列",
  score: "势能分",
  state: "当前状态（热1/中0/冷-1）",
  thresholdPolicy: "动态阈值口径",
  clusterPolicy: "聚集口径",
  cyclePolicy: "周期口径",
  short: "短窗",
  blocks: "分窗数",
  sensitivity: "灵敏带倍数",
  cycleWeight: "周期权重",
  clusterWeight: "聚集权重",
  mode: "侧重方向",
  selectedPosition: "最佳偏离位置（0为万位，-1为均匀）",
  logMarginals: "对数边际似然",
  logBayesFactorUniformVsIID1: "均匀相对IID1对数因子",
  strength: "不精确先验强度",
  uncertaintyWidth: "单位置不确定度宽度",
  finalMasses: "各位置最终质量",
  ignorance: "各位置无知质量",
  omittedLogDenominator: "共同对数分母（排序省略）",
  evidenceIndependence: "窗口独立性",
  model: "模型口径",
  weights: "模型权重",
  models: "模型名称",
  targetCount: "目标保留组数",
  actualCount: "实际保留组数",
  boundaryScore: "边界评分",
  boundaryTies: "边界并列组数",
  allUniform: "评分是否完全退化为并列",
  quantizationDecimals: "评分小数精度",
  ties: "并列策略",
  universe: "排名基准组数",
  trainingCount: "训练期数",
  firstIssue: "起始期",
  lastIssue: "截止期",
  firstDate: "起始日期",
  lastDate: "截止日期",
  allowed: "允许值",
  lo: "下界",
  hi: "上界",
  mean: "历史均值",
  sd: "总体标准差",
  referenceNumber: "参考号码",
  omissionPolicy: "遗漏口径",
  strategy: "选择标准",
  selectedParameter: "选中参数",
  validationCoverage: "验证覆盖率",
  validationCount: "验证期数",
  averageCount: "平均保留组数",
  candidates: "候选参数比较",
  trainingEnd: "训练截止期",
  validationStart: "验证起始期",
  validationEnd: "验证结束期",
  steps: "选择步骤",
  step: "步骤",
  targetCoverage: "目标验证覆盖率",
  emptySelection: "是否未选择任何条件",
  selectionPolicy: "选择口径",
  derived: "重拟合详情",
  preset: "组合包",
  parameter: "方法参数",
  windowSizes: "分窗期数",
  scoreScale: "评分尺度",
  alpha: "平滑浓度",
  selectedModel: "最佳模型",
  conflicts: "冲突系数",
  selected: "选中参数",
  threshold: "排名阈值",
  folds: "滚动验证",
  window: "历史窗口",
  method: "方法",
  coverage: "覆盖率",
  retain: "保留比例",
  seed: "随机种子",
  actual: "实际保留",
  target: "目标保留",
  referenceIssue: "参考期",
  training: "训练记录",
  validation: "验证记录",
  fallback: "回退说明",
  details: "计算详情",
  startIssue: "起始期",
  endIssue: "截止期",
};
function readable(value: unknown, depth = 0): ReactNode {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "是" : "否";
  if (typeof value !== "object") {
    const labels: Record<string, string> = {
      ...researchLabels,
      inclusive: "保留边界全部并列",
      seeded: "固定种子精确保留",
      lift60: "覆盖≥60%，提升比优先",
      cov90: "覆盖≥90%，集合最小",
      strict: "验证全中，集合最小",
      probability: "预测分布评分",
      logProbability: "对数似然",
      logUnnormalized: "未归一化对数评分",
      logPlausibility: "对数似然度",
      "assumed-not-established": "窗口独立性为假设，未经证实",
    };
    return labels[String(value)] ?? String(value);
  }
  if (depth >= 5) return "展开层级已达上限";
  const entries = Array.isArray(value)
    ? value.slice(0, 30).map((v, i) => [String(i + 1), v] as const)
    : Object.entries(value).slice(0, 40);
  return (
    <>
      <dl className="research-diagnostics-grid">
        {entries.map(([k, v]) => (
          <div key={k}>
            <dt>{diagnosticLabels[k] ?? k}</dt>
            <dd>{readable(v, depth + 1)}</dd>
          </div>
        ))}
      </dl>
      {Array.isArray(value) && value.length > 30 && (
        <p>其余{value.length - 30}项已省略</p>
      )}
    </>
  );
}
export function ResearchDiagnosticsView({
  items,
}: {
  items: NonNullable<FilterResult["research"]>;
}) {
  return items.length ? (
    <section className="research-diagnostics">
      <h3>实验计算说明</h3>
      <p>本次输入快照的拟合与选择记录；验证覆盖不等于未来命中保证。</p>
      {items.map((item) => (
        <details key={item.id} open>
          <summary>{item.label}</summary>
          {item.diagnostics.allUniform === true && (
            <p className="research-context">
              本次全部号码评分并列。保留边界全部并列时会保留10万组；固定种子模式只按种子选择指定数量。
            </p>
          )}
          {readable(item.diagnostics)}
        </details>
      ))}
    </section>
  ) : null;
}
