import { useState } from "react";
import { Plus, Pencil, Trash2, Settings2 } from "lucide-react";
import {
  validateInput,
  ruleLabels,
  type Rule,
  type FilterInput,
} from "../domain/pick5";
import {
  advancedKinds,
  advancedLabels,
  advancedDefaults,
  type AdvancedKind,
} from "../domain/advanced";
const historyKinds = [
  "historyExclude",
  "samePosition",
  "historyOverlap",
  "neighborCounts",
  "historyDelta",
  "omission",
  "frequency",
];
const stringKinds = [
  "oddPattern",
  "bigPattern",
  "primePattern",
  "routeCounts",
  "routePattern",
  "positionTrend",
  "neighborCounts",
];
const noValues = ["danGroups", "partition", "historyExclude"];
const placeNames = ["万位", "千位", "百位", "十位", "个位"];
export const explanations: Record<AdvancedKind, string> = {
  danGroups: "每组数字按命中的不同数字种数计算。每组可设精确数，或共用范围。",
  oddPattern: "五位有序形态：1为奇，0为偶，?为不限。例如1?0??。",
  bigPattern: "五位有序形态：1为大（5–9），0为小（0–4），?为不限。",
  primePattern: "五位有序形态：1为质类12357，0为合类04689，?为不限。",
  routeCounts: "按数字除3的余数计数。例如2:2:1，三路个数合计5。",
  routePattern: "五位分别对3取余，输入五位0/1/2形态，?为不限，例如0?201。",
  positionDiff: "指定两个位置的绝对差，范围0–9。",
  positionTrend: "相邻位置后位减前位：上升、相等或下降。",
  max: "五位数字中的最大值。",
  min: "五位数字中的最小值。",
  median: "包含重复数字排序后的第三个数字。",
  mean: "五位之和除以5，间隔0.2，不取整。",
  pairSum: "指定位置对或全部10对的两数之和，范围0–18；限制匹配对数。",
  pairDiff: "位置对两数的绝对差，范围0–9；限制匹配对数。",
  pairTail: "位置对两数的和对10取余，范围0–9。",
  pairProductTail: "位置对两数的乘积对10取余，范围0–9。",
  classSum: "对指定类别的全部位置数字求和，重复数字重复计入；没有该类别时为0。",
  remainderSum: "每位分别对模数取余，再把五个余数相加。",
  partition: "各分区互斥且完整覆盖0–9；各区命中位置数的总和为5。",
  historyExclude:
    "保留模式排除指定历史窗口中完全相同的五位号码；排除模式则仅保留历史出现过的号码。",
  samePosition: "与参考期逐位比较，相等位置个数0–5。",
  historyOverlap: "候选与参考期不同数字集合的交集种数；重复出现不重复计数。",
  neighborCounts:
    "参考数字集合中为重，差1且不在集合为邻，其余为孤；9与0不相邻。按位置计数，三类合计5。",
  historyDelta: "候选和值或跨度与参考期指标之差，可选绝对值。",
  omission:
    "截至参考期的指定位置数字当前遗漏。若从窗口起点从未出现则不能视为精确遗漏，计算会提示历史不足。",
  frequency: "指定位置的候选数字，在截至参考期的最近N期里出现次数。",
};
function parseValues(text: string, kind: AdvancedKind): (number | string)[] {
  const parts = text
    .trim()
    .split(/[\s,，]+/)
    .filter(Boolean);
  if (stringKinds.includes(kind)) return parts;
  return parts.flatMap((part) => {
    if (part.includes("..")) {
      const pair = part.split("..").map(Number);
      if (
        pair.length !== 2 ||
        pair.some((n) => !Number.isFinite(n)) ||
        pair[1] < pair[0] ||
        pair[1] - pair[0] > 100000
      )
        throw new Error("数值区间格式错误");
      const step = kind === "mean" ? 0.2 : 1;
      return Array.from(
        { length: Math.floor((pair[1] - pair[0]) / step + 1e-8) + 1 },
        (_, i) => Math.round((pair[0] + i * step) * 10) / 10,
      );
    }
    const n = Number(part);
    if (!Number.isFinite(n)) throw new Error("请输入数值，多个值用逗号分隔");
    return [n];
  });
}
export default function AdvancedRules({
  input,
  onChange,
  historySource,
}: {
  input: FilterInput;
  onChange: (i: FilterInput) => void;
  historySource: string;
}) {
  const [kind, setKind] = useState<AdvancedKind>("oddPattern"),
    [draft, setDraft] = useState<Rule | null>(null),
    [values, setValues] = useState(""),
    [groupText, setGroupText] = useState(""),
    [countsText, setCountsText] = useState(""),
    [error, setError] = useState(""),
    [search, setSearch] = useState("");
  const list = input.rules.filter((r) =>
    advancedKinds.includes(r.kind as AdvancedKind),
  );
  const select = (k: AdvancedKind, existing?: Rule) => {
    const def = advancedDefaults[k];
    const r: Rule = existing
      ? JSON.parse(JSON.stringify(existing))
      : {
          id: crypto.randomUUID(),
          kind: k,
          enabled: true,
          mode: "include",
          ...JSON.parse(JSON.stringify(def)),
        };
    setKind(k);
    setDraft(r);
    setValues(r.values.join(","));
    setGroupText(
      (r.params?.groups ?? r.params?.partitions ?? [])
        .map((g) => g.join(""))
        .join(";"),
    );
    setCountsText(r.params?.counts?.join(",") ?? "");
    setError("");
  };
  const patch = (change: Partial<Rule>) =>
    setDraft((prev) => (prev ? { ...prev, ...change } : prev));
  const param = (change: NonNullable<Rule["params"]>) =>
    setDraft((prev) =>
      prev ? { ...prev, params: { ...prev.params, ...change } } : prev,
    );
  const save = () => {
    if (!draft) return;
    try {
      const params = { ...draft.params };
      if (kind === "danGroups" || kind === "partition") {
        const groups = groupText
          .split(/[;；\n]+/)
          .map((g) => [...g.replace(/[\s,，]/g, "")].map(Number));
        if (kind === "partition") params.partitions = groups;
        else params.groups = groups;
        params.counts = countsText.trim()
          ? countsText.split(/[,，\s]+/).map(Number)
          : undefined;
      }
      const rule = {
        ...draft,
        values: noValues.includes(kind) ? [] : parseValues(values, kind),
        params,
      };
      validateInput({
        ...input,
        rules: [{ ...rule, enabled: true }],
        combination: undefined,
      });
      onChange({
        ...input,
        rules: [...input.rules.filter((r) => r.id !== rule.id), rule],
      });
      setDraft(null);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const groups = new Set(
    input.rules.filter((r) => r.enabled).map((r) => r.group ?? r.id),
  ).size;
  return (
    <section className="card advanced-card">
      <div className="section-head">
        <h2>
          <Settings2 size={17} />
          进阶与历史过滤 <span className="count-badge">{list.length}</span>
        </h2>
        <button
          className="text-button"
          onClick={() => (draft ? setDraft(null) : select(kind))}
        >
          <Plus size={14} />
          {draft ? "收起编辑" : "添加条件"}
        </button>
      </div>
      <div className="advanced-content">
        <div className="tolerance-box">
          <label>
            组合方式
            <select
              value={input.combination?.mode ?? "strict"}
              onChange={(e) =>
                onChange({
                  ...input,
                  combination: {
                    mode: e.target.value as "strict" | "atLeast",
                    minimum: Math.min(
                      input.combination?.minimum ?? groups,
                      groups,
                    ),
                  },
                })
              }
            >
              <option value="strict">全部满足</option>
              <option value="atLeast">条件组容错</option>
            </select>
          </label>
          {input.combination?.mode === "atLeast" && (
            <label>
              至少满足
              <input
                type="number"
                min={0}
                max={groups}
                value={input.combination.minimum}
                onChange={(e) =>
                  onChange({
                    ...input,
                    combination: {
                      mode: "atLeast",
                      minimum: Number(e.target.value),
                    },
                  })
                }
              />{" "}
              / {groups} 组
            </label>
          )}
          <p>同名规则组内全部满足；空组名各自独立。0组表示不限制。</p>
        </div>
        {list.length > 0 && (
          <div className="advanced-list">
            {list.map((r) => (
              <div key={r.id}>
                <label>
                  <input
                    type="checkbox"
                    checked={r.enabled}
                    onChange={(e) =>
                      onChange({
                        ...input,
                        rules: input.rules.map((s) =>
                          s.id === r.id
                            ? { ...s, enabled: e.target.checked }
                            : s,
                        ),
                      })
                    }
                  />
                  <strong>{ruleLabels[r.kind]}</strong>
                </label>
                <small>
                  {r.mode === "include" ? "保留" : "排除"}{" "}
                  {r.values.length ? r.values.join("、") : "按参数"}
                  {r.group ? ` · ${r.group}组` : ""}
                </small>
                <button
                  className="icon-button"
                  aria-label={`编辑${ruleLabels[r.kind]}`}
                  onClick={() => select(r.kind as AdvancedKind, r)}
                >
                  <Pencil size={13} />
                </button>
                <button
                  className="icon-button"
                  aria-label={`删除${ruleLabels[r.kind]}`}
                  onClick={() =>
                    onChange({
                      ...input,
                      rules: input.rules.filter((s) => s.id !== r.id),
                    })
                  }
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
          </div>
        )}
        {draft && (
          <div className="advanced-editor">
            <div className="advanced-field">
              <label>
                查找条件
                <input
                  aria-label="查找过滤条件"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="形态、两码、历史…"
                />
              </label>
              <label>
                过滤规则
                <select
                  aria-label="高级过滤规则"
                  value={kind}
                  onChange={(e) => select(e.target.value as AdvancedKind)}
                >
                  {advancedKinds
                    .filter(
                      (k) => advancedLabels[k].includes(search) || k === kind,
                    )
                    .map((k) => (
                      <option value={k} key={k}>
                        {advancedLabels[k]}
                      </option>
                    ))}
                </select>
              </label>
            </div>
            <p className="rule-help">{explanations[kind]}</p>
            <div className="advanced-field">
              <label>
                筛选模式
                <select
                  value={draft.mode}
                  onChange={(e) =>
                    patch({ mode: e.target.value as Rule["mode"] })
                  }
                >
                  <option value="include">保留符合条件</option>
                  <option value="exclude">排除符合条件</option>
                </select>
              </label>
              <label>
                规则组名（选填）
                <input
                  value={draft.group ?? ""}
                  onChange={(e) =>
                    patch({ group: e.target.value.trim() || undefined })
                  }
                  placeholder="同组条件同时满足"
                />
              </label>
            </div>
            {[
              "positionDiff",
              "positionTrend",
              "omission",
              "frequency",
            ].includes(kind) && (
              <div className="advanced-field">
                <label>
                  第一个位置
                  <select
                    value={draft.params?.positions?.[0] ?? 0}
                    onChange={(e) =>
                      param({
                        positions: [
                          Number(e.target.value),
                          ...(draft.params?.positions?.slice(1) ?? []),
                        ],
                      })
                    }
                  >
                    {placeNames.map((n, i) => (
                      <option value={i} key={n}>
                        {n}
                      </option>
                    ))}
                  </select>
                </label>
                {["positionDiff", "positionTrend"].includes(kind) && (
                  <label>
                    第二个位置
                    <select
                      value={draft.params?.positions?.[1] ?? 1}
                      onChange={(e) =>
                        param({
                          positions: [
                            draft.params?.positions?.[0] ?? 0,
                            Number(e.target.value),
                          ],
                        })
                      }
                    >
                      {placeNames.map((n, i) => (
                        <option value={i} key={n}>
                          {n}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </div>
            )}
            {kind.startsWith("pair") && (
              <>
                <label className="field-label">
                  位置组合
                  <select
                    value={draft.params?.positions?.join(",") ?? "all"}
                    onChange={(e) =>
                      param({
                        positions:
                          e.target.value === "all"
                            ? undefined
                            : e.target.value.split(",").map(Number),
                        countMin: 1,
                        countMax: e.target.value === "all" ? 10 : 1,
                      })
                    }
                  >
                    <option value="all">全部10个位置对</option>
                    {placeNames.flatMap((n, i) =>
                      placeNames.slice(i + 1).map((m, j) => (
                        <option
                          value={`${i},${i + j + 1}`}
                          key={`${i},${i + j + 1}`}
                        >
                          {n} + {m}
                        </option>
                      )),
                    )}
                  </select>
                </label>
                <div className="advanced-field">
                  <label>
                    最少匹配对数
                    <input
                      type="number"
                      min={0}
                      max={draft.params?.positions ? 1 : 10}
                      value={draft.params?.countMin ?? 1}
                      onChange={(e) =>
                        param({ countMin: Number(e.target.value) })
                      }
                    />
                  </label>
                  <label>
                    最多匹配对数
                    <input
                      type="number"
                      min={0}
                      max={draft.params?.positions ? 1 : 10}
                      value={draft.params?.countMax ?? 10}
                      onChange={(e) =>
                        param({ countMax: Number(e.target.value) })
                      }
                    />
                  </label>
                </div>
              </>
            )}
            {kind === "classSum" && (
              <label className="field-label">
                数字类别
                <select
                  value={draft.params?.class ?? "odd"}
                  onChange={(e) =>
                    param({
                      class: e.target.value as NonNullable<
                        Rule["params"]
                      >["class"],
                    })
                  }
                >
                  {[
                    ["odd", "奇数"],
                    ["even", "偶数"],
                    ["big", "大数"],
                    ["small", "小数"],
                    ["prime", "质类"],
                    ["composite", "合类"],
                  ].map(([v, n]) => (
                    <option value={v} key={v}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {kind === "remainderSum" && (
              <label className="field-label">
                模数
                <select
                  value={draft.params?.modulus ?? 3}
                  onChange={(e) => param({ modulus: Number(e.target.value) })}
                >
                  {[3, 4, 5].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {["danGroups", "partition"].includes(kind) && (
              <>
                <label className="field-label">
                  数字分组（分号分组，每组内填写数字）
                  <input
                    value={groupText}
                    onChange={(e) => setGroupText(e.target.value)}
                    placeholder="01234;56789"
                  />
                </label>
                <label className="field-label">
                  每组精确命中个数（逗号分隔
                  {kind === "danGroups" ? "，留空则用范围" : ""}）
                  <input
                    value={countsText}
                    onChange={(e) => setCountsText(e.target.value)}
                    placeholder="2,3"
                  />
                </label>
                {kind === "danGroups" && (
                  <div className="advanced-field">
                    <label>
                      每组最少种数
                      <input
                        type="number"
                        min={0}
                        max={5}
                        value={draft.params?.countMin ?? 1}
                        onChange={(e) =>
                          param({ countMin: Number(e.target.value) })
                        }
                      />
                    </label>
                    <label>
                      每组最多种数
                      <input
                        type="number"
                        min={0}
                        max={5}
                        value={draft.params?.countMax ?? 5}
                        onChange={(e) =>
                          param({ countMax: Number(e.target.value) })
                        }
                      />
                    </label>
                  </div>
                )}
              </>
            )}
            {historyKinds.includes(kind) && (
              <div className="history-rule-info">
                <p>
                  历史来源：{historySource} · {input.history?.length ?? 0}期
                </p>
                <label>
                  参考截止期
                  <select
                    value={draft.params?.referenceIssue ?? ""}
                    onChange={(e) =>
                      param({ referenceIssue: e.target.value || undefined })
                    }
                  >
                    <option value="">快照最新一期</option>
                    {[...(input.history ?? [])].reverse().map((d) => (
                      <option value={d.issue} key={d.issue}>
                        {d.issue} · {d.date} · {d.number}
                      </option>
                    ))}
                  </select>
                </label>
                {["frequency", "historyExclude"].includes(kind) && (
                  <label>
                    历史窗口期数
                    <input
                      type="number"
                      min={1}
                      max={input.history?.length ?? 100000}
                      value={
                        draft.params?.window ?? input.history?.length ?? 30
                      }
                      onChange={(e) =>
                        param({ window: Number(e.target.value) })
                      }
                    />
                  </label>
                )}
                <small>
                  只使用截止期及以前的记录。可先去历史走势载入真实数据。
                </small>
              </div>
            )}
            {kind === "historyDelta" && (
              <div className="advanced-field">
                <label>
                  指标
                  <select
                    value={draft.params?.metric ?? "sum"}
                    onChange={(e) =>
                      param({ metric: e.target.value as "sum" | "span" })
                    }
                  >
                    <option value="sum">和值</option>
                    <option value="span">跨度</option>
                  </select>
                </label>
                <label>
                  差值方向
                  <select
                    value={
                      draft.params?.absolute === false ? "signed" : "absolute"
                    }
                    onChange={(e) =>
                      param({ absolute: e.target.value === "absolute" })
                    }
                  >
                    <option value="absolute">绝对差</option>
                    <option value="signed">候选减参考（有正负）</option>
                  </select>
                </label>
              </div>
            )}
            {!noValues.includes(kind) && (
              <label className="field-label">
                允许值（逗号分隔
                {!stringKinds.includes(kind) ? "，或用 1..5 表示区间" : ""}）
                <input
                  aria-label="高级规则允许值"
                  value={values}
                  onChange={(e) => setValues(e.target.value)}
                  placeholder={
                    stringKinds.includes(kind)
                      ? "10101 或 2:2:1"
                      : "0,1,2 或 0..9"
                  }
                />
              </label>
            )}
            {kind === "positionTrend" && (
              <small>up=上升，equal=相等，down=下降。</small>
            )}
            {error && (
              <div className="error-box" role="alert">
                {error}
              </div>
            )}
            <div className="head-actions">
              <button className="button primary" onClick={save}>
                应用高级条件
              </button>
              <button
                className="button secondary"
                onClick={() => setDraft(null)}
              >
                取消
              </button>
            </div>
          </div>
        )}
        {!draft && !list.length && (
          <p className="muted small advanced-empty">
            按需添加形态、两码关系、分区和历史条件，基础面板保持简洁。
          </p>
        )}
      </div>
    </section>
  );
}
