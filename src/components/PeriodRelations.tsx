import { useEffect, useMemo, useState } from "react";
import {
  defaultRelation,
  inspectRelations,
  prepareRelation,
  relationLabels,
  relationMetricLabels,
  type RelationConfig,
} from "../domain/relations";
import type { FilterInput, Rule } from "../domain/pick5";
import "./relations.css";
const places = ["万位", "千位", "百位", "十位", "个位"];
const instructions = {
  repeat:
    "比较候选与滞后L期的值；相等记1，逐位模式统计相等位置数。滞后1为截止期，滞后2为再前一期。",
  neighbor:
    "绝对差恰为1才算邻号，不包含重号；0与9不循环相邻。可设置候选位与来源位，观察跨位传递。",
  mirror:
    "按所选映射比较候选数字与滞后期数字；可选9减原数，或加5取尾。只有位置数字支持镜像。",
  inherit:
    "指定指标模式：候选值在最近D期来源指标中出现的期数。逐位模式：候选的五个位置中，至少在最近D期同位出现过一次的位置数。",
  delta:
    "候选指标减去滞后期指标，保留正负方向；例如和值差为-2表示比参考期小2。",
};
const stamp = (r: Rule) => JSON.stringify({ ...r, enabled: undefined });
export default function PeriodRelations({
  input,
  onChange,
  onOpenHistory,
}: {
  input: FilterInput;
  onChange: (input: FilterInput) => void;
  onOpenHistory?: () => void;
}) {
  const [config, setConfig] = useState<RelationConfig>({ ...defaultRelation });
  const [editing, setEditing] = useState<{ id: string; stamp: string } | null>(
      null,
    ),
    [error, setError] = useState("");
  const [sample, setSample] = useState("12345");
  const patch = (change: Partial<RelationConfig>) => {
    setConfig((c) => ({ ...c, ...change }));
    setError("");
  };
  useEffect(() => {
    if (!editing) return;
    const r = input.rules.find((r) => r.id === editing.id);
    if (!r || stamp(r) !== editing.stamp) {
      setEditing(null);
      setError("原跨期条件已改变或移除，请重新编辑。");
    }
  }, [input.rules, editing]);
  const inspection = useMemo(() => {
    try {
      return { data: inspectRelations(input.history, config), error: "" };
    } catch (e) {
      return { data: null, error: (e as Error).message };
    }
  }, [input.history, config]);
  const model = useMemo(() => {
    try {
      return { data: prepareRelation(config, input.history), error: "" };
    } catch (e) {
      return { data: null, error: (e as Error).message };
    }
  }, [input.history, config]);
  const rules = input.rules.filter((r) => r.kind === "relation");
  const save = () => {
    try {
      prepareRelation(config, input.history);
      const original = editing
        ? input.rules.find((r) => r.id === editing.id)
        : undefined;
      if (editing && (!original || stamp(original) !== editing.stamp))
        throw new Error("原跨期条件已改变或移除，请重新编辑。");
      const rule: Rule = {
        id: original?.id ?? crypto.randomUUID(),
        kind: "relation",
        values: [],
        enabled: original?.enabled ?? true,
        mode: ruleMode,
        group: group.trim() || undefined,
        relation: { ...config },
      };
      onChange({
        ...input,
        rules: original
          ? input.rules.map((r) => (r.id === rule.id ? rule : r))
          : [...input.rules, rule],
      });
      setEditing(null);
      setError("");
      setNotice("跨期条件已保存，点击开始缩水后按当前历史快照计算。");
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const [ruleMode, setRuleMode] = useState<Rule["mode"]>("include"),
    [group, setGroup] = useState(""),
    [notice, setNotice] = useState("");
  const maxScore =
    config.method === "delta"
      ? 45
      : config.method === "inherit" && config.scope === "indicator"
        ? config.depth
        : config.scope === "positions"
          ? 5
          : 1;
  const series = inspection.data?.rows ?? [];
  const values = series.map((r) => r.value),
    lo = Math.min(...values),
    hi = Math.max(...values);
  const preview =
    /^\d{5}$/.test(sample) && model.data
      ? { score: model.data.score(sample), match: model.data.test(sample) }
      : null;
  const percent = (n: number, total: number) =>
    total ? `${((n / total) * 100).toFixed(1)}%` : "—";
  return (
    <section className="card period-card" aria-labelledby="period-title">
      <div className="section-head">
        <h2 id="period-title">
          跨期关联与指标观察 <span className="muted">{rules.length}</span>
        </h2>
        {onOpenHistory && (
          <button className="button secondary" onClick={onOpenHistory}>
            加载/导入历史
          </button>
        )}
      </div>
      <p
        className={
          input.historySource?.includes("演示") ? "notice small" : "muted small"
        }
      >
        数据来源：{input.historySource || "未载入历史"} ·{" "}
        {input.history?.length ?? 0}期。
        {input.historySource?.includes("演示")
          ? "当前为模拟数据，不能当作真实开奖规律。"
          : ""}
        按记录顺序计算滞后，不推断日历连续性。
      </p>
      {rules.map((r) => (
        <div className="period-rule" key={r.id}>
          <label>
            <input
              type="checkbox"
              aria-label={`启用跨期条件 ${relationLabels[r.relation!.method]}`}
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
            {relationLabels[r.relation!.method]}
          </label>
          <small>
            {r.mode === "include" ? "保留" : "排除"} ·{" "}
            {r.relation!.scope === "positions"
              ? "五位逐位"
              : `${relationMetricLabels[r.relation!.metric]}${r.relation!.metric === "position" ? ` ${places[r.relation!.position]}←${places[r.relation!.previousPosition]}` : ""}`}{" "}
            ·{" "}
            {r.relation!.method === "inherit"
              ? `近${r.relation!.depth}期`
              : `滞后${r.relation!.lag}期`}{" "}
            ·{" "}
            {r.relation!.strategy === "historical"
              ? `窗口${r.relation!.window}期，出现比例≥${r.relation!.minSupport * 100}%`
              : `分数${r.relation!.min}—${r.relation!.max}`}
            {r.relation!.referenceIssue
              ? ` · 截至${r.relation!.referenceIssue}`
              : ""}
          </small>
          <button
            className="text-button"
            aria-label={`编辑跨期条件 ${relationLabels[r.relation!.method]}`}
            onClick={() => {
              setConfig({ ...r.relation! });
              setRuleMode(r.mode);
              setGroup(r.group ?? "");
              setEditing({ id: r.id, stamp: stamp(r) });
              setError("");
              setNotice("");
            }}
          >
            编辑
          </button>
          <button
            className="text-button"
            aria-label={`删除跨期条件 ${relationLabels[r.relation!.method]}`}
            onClick={() =>
              onChange({
                ...input,
                rules: input.rules.filter((x) => x.id !== r.id),
              })
            }
          >
            删除
          </button>
        </div>
      ))}
      <div className="period-fields">
        <label>
          关联方法
          <select
            aria-label="跨期方法"
            value={config.method}
            onChange={(e) => {
              const method = e.target.value as RelationConfig["method"];
              patch({
                method,
                ...(method === "mirror"
                  ? { metric: "position" as const, lag: 2 }
                  : {}),
                ...(method === "delta"
                  ? { scope: "indicator" as const, min: -5, max: 5 }
                  : { min: 1, max: 1 }),
              });
            }}
          >
            {Object.entries(relationLabels).map(([v, n]) => (
              <option key={v} value={v}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <label>
          比较范围
          <select
            aria-label="跨期比较范围"
            value={config.scope}
            onChange={(e) =>
              patch({
                scope: e.target.value as RelationConfig["scope"],
                metric:
                  e.target.value === "positions" ? "position" : config.metric,
                min: 1,
                max: 1,
              })
            }
          >
            <option value="indicator">指定指标 / 位置</option>
            <option value="positions" disabled={config.method === "delta"}>
              五个位置逐位比较
            </option>
          </select>
        </label>
        <label>
          观察指标
          <select
            aria-label="跨期观察指标"
            value={config.metric}
            onChange={(e) =>
              patch({ metric: e.target.value as RelationConfig["metric"] })
            }
            disabled={
              config.scope === "positions" || config.method === "mirror"
            }
          >
            {Object.entries(relationMetricLabels).map(([v, n]) => (
              <option key={v} value={v}>
                {n}
              </option>
            ))}
          </select>
        </label>
        {config.metric === "position" && (
          <>
            <label>
              候选/观察位置
              <select
                aria-label="跨期候选位置"
                value={config.position}
                onChange={(e) => patch({ position: Number(e.target.value) })}
              >
                {places.map((n, i) => (
                  <option key={n} value={i}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
            <label>
              历史来源位置
              <select
                aria-label="跨期来源位置"
                disabled={config.scope === "positions"}
                value={config.previousPosition}
                onChange={(e) =>
                  patch({ previousPosition: Number(e.target.value) })
                }
              >
                {places.map((n, i) => (
                  <option key={n} value={i}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
          </>
        )}
        {config.method === "inherit" ? (
          <label>
            延续观察深度D
            <input
              aria-label="跨期延续深度"
              type="number"
              min="1"
              max="60"
              value={config.depth}
              onChange={(e) =>
                patch({ depth: Number(e.target.value), min: 1, max: 1 })
              }
            />
          </label>
        ) : (
          <label>
            比较滞后L（1=上一期）
            <input
              aria-label="跨期滞后期数"
              type="number"
              min="1"
              max="60"
              value={config.lag}
              onChange={(e) => patch({ lag: Number(e.target.value) })}
            />
          </label>
        )}
        {config.method === "mirror" && (
          <label>
            镜像定义
            <select
              aria-label="跨期镜像定义"
              value={config.mirror}
              onChange={(e) =>
                patch({ mirror: e.target.value as RelationConfig["mirror"] })
              }
            >
              <option value="nine">9减原数（0↔9、1↔8…）</option>
              <option value="five">加5取尾（0↔5、1↔6…）</option>
            </select>
          </label>
        )}
        <label>
          观察/训练窗口W
          <input
            aria-label="跨期窗口"
            type="number"
            min="3"
            max="1000"
            value={config.window}
            onChange={(e) => patch({ window: Number(e.target.value) })}
          />
        </label>
        <label>
          历史截止期（空为最新）
          <input
            aria-label="跨期参考期"
            value={config.referenceIssue ?? ""}
            list="period-issues"
            onChange={(e) =>
              patch({ referenceIssue: e.target.value.trim() || undefined })
            }
          />
          <datalist id="period-issues">
            {input.history?.slice(-200).map((r) => (
              <option key={r.issue} value={r.issue}>
                {r.date}
              </option>
            ))}
          </datalist>
        </label>
        <label>
          过滤依据
          <select
            aria-label="跨期过滤依据"
            value={config.strategy}
            onChange={(e) =>
              patch({ strategy: e.target.value as RelationConfig["strategy"] })
            }
          >
            <option value="range">手动指定关联分数范围</option>
            <option value="historical">历史关联分数分布</option>
          </select>
        </label>
        {config.strategy === "range" ? (
          <>
            <label>
              分数最小值
              <input
                aria-label="跨期最小分数"
                type="number"
                min={config.method === "delta" ? -45 : 0}
                max={maxScore}
                value={config.min}
                onChange={(e) => patch({ min: Number(e.target.value) })}
              />
            </label>
            <label>
              分数最大值
              <input
                aria-label="跨期最大分数"
                type="number"
                min={config.method === "delta" ? -45 : 0}
                max={maxScore}
                value={config.max}
                onChange={(e) => patch({ max: Number(e.target.value) })}
              />
            </label>
          </>
        ) : (
          <label>
            历史最低出现比例（%）
            <input
              aria-label="跨期最低比例"
              type="number"
              min="0"
              max="100"
              step="1"
              value={config.minSupport * 100}
              onChange={(e) =>
                patch({ minSupport: Number(e.target.value) / 100 })
              }
            />
          </label>
        )}
        <label>
          规则模式
          <select
            aria-label="跨期规则模式"
            value={ruleMode}
            onChange={(e) => setRuleMode(e.target.value as Rule["mode"])}
          >
            <option value="include">包含符合项</option>
            <option value="exclude">排除符合项</option>
          </select>
        </label>
        <label>
          容错分组（可选）
          <input
            aria-label="跨期分组"
            value={group}
            onChange={(e) => setGroup(e.target.value)}
          />
        </label>
      </div>
      <p className="period-help">{instructions[config.method]}</p>
      <p className="muted small">
        {editing
          ? "正在编辑已保存条件；保存前右侧计算仍使用原条件。"
          : "以下为观察配置；添加后才参与缩水。"}
        历史分布只描述样本，不代表未来预测优势。
      </p>
      <div className="period-preview">
        <label>
          候选五位号码
          <input
            aria-label="跨期预览号码"
            value={sample}
            maxLength={5}
            inputMode="numeric"
            onChange={(e) => setSample(e.target.value)}
          />
        </label>
        {preview && (
          <p>
            关联分数 <strong>{preview.score}</strong> ·{" "}
            {preview.match ? "符合当前条件" : "不符合当前条件"} · 参考截止{" "}
            {model.data!.diagnostics.lastIssue}
          </p>
        )}
      </div>
      {model.error && <p className="notice small">{model.error}</p>}
      {model.data && config.strategy === "historical" && (
        <div className="period-fit">
          <strong>历史拟合：{config.window}个目标期</strong>
          <p>
            保留分数：
            {model.data.diagnostics.allowedScores.join("、") ||
              "无（当前阈值下全部排除）"}
          </p>
          <div className="period-distribution">
            {model.data.diagnostics.distribution.map((d) => (
              <span key={d.value}>
                分数{d.value}：{d.count}次（{percent(d.count, config.window)}）
              </span>
            ))}
          </div>
        </div>
      )}
      <div className="head-actions">
        <button className="button primary" onClick={save}>
          {editing ? "保存关联条件" : "添加关联条件"}
        </button>
        {editing && (
          <button
            className="button secondary"
            onClick={() => {
              setEditing(null);
              setError("");
            }}
          >
            取消关联编辑
          </button>
        )}
      </div>
      {notice && (
        <p className="notice small" role="status">
          {notice}
        </p>
      )}
      {error && (
        <p className="validation" role="alert">
          {error}
        </p>
      )}
      {inspection.error ? (
        <p className="validation">指标观察不可用：{inspection.error}</p>
      ) : (
        inspection.data && (
          <div className="period-observation">
            <h3>指标历史序列</h3>
            <p className="muted small">
              {relationMetricLabels[config.metric]}
              {config.metric === "position"
                ? ` · ${places[config.position]}`
                : ""}{" "}
              · 窗口{series.length}期 / 截止前共{inspection.data.available}期 ·
              截至{inspection.data.lastIssue}
              。重复间隔使用截止前全部记录；首次可见且无更早记录时标为窗口外未知。
            </p>
            <svg viewBox="0 0 640 110" role="img" aria-label="跨期指标历史折线">
              <line x1="8" y1="95" x2="630" y2="95" stroke="#eadfd2" />
              <polyline
                points={series
                  .map(
                    (r, i) =>
                      `${8 + (i / Math.max(1, series.length - 1)) * 622},${hi === lo ? 52 : 95 - ((r.value - lo) / (hi - lo)) * 80}`,
                  )
                  .join(" ")}
                fill="none"
                stroke="#ef7a28"
                strokeWidth="2"
              />
              <text x="10" y="12" fill="#88725b" fontSize="11">
                {lo} — {hi}
              </text>
            </svg>
            <div className="period-scroll">
              <table aria-label="跨期指标明细">
                <thead>
                  <tr>
                    {[
                      "期号 / 日期",
                      "开奖号码",
                      "指标值",
                      "较上期差",
                      "重复间隔",
                      "连续重复",
                      "关联分数",
                    ].map((n) => (
                      <th key={n}>{n}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...series].reverse().map((r) => (
                    <tr key={r.issue}>
                      <td>
                        {r.issue}
                        <small>{r.date}</small>
                      </td>
                      <td className="period-number">{r.number}</td>
                      <td>{r.value}</td>
                      <td>
                        {r.delta === null
                          ? "—"
                          : r.delta > 0
                            ? `+${r.delta}`
                            : r.delta}
                      </td>
                      <td>
                        {r.repeatGap === null
                          ? "窗口外未知"
                          : `${r.repeatGap}期`}
                      </td>
                      <td>{r.streak}期</td>
                      <td>{r.score ?? "历史不足"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <h3>滞后关系对照</h3>
            <p className="muted small">
              比较目标期的所选指标与L期前的来源指标；逐位模式的五位计数见上表关联分数。比例=匹配数/有效目标期数，非中奖概率。当前镜像定义：
              {config.mirror === "nine" ? "9减原数" : "加5取尾"}。
            </p>
            <div className="period-scroll">
              <table aria-label="跨期滞后对照">
                <thead>
                  <tr>
                    {[
                      "滞后",
                      "有效样本",
                      "重号匹配",
                      "邻号匹配",
                      "镜像匹配",
                      "操作",
                    ].map((n) => (
                      <th key={n}>{n}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {inspection.data.lags.map((l) => (
                    <tr
                      key={l.lag}
                      className={l.lag === config.lag ? "period-selected" : ""}
                    >
                      <td>{l.lag}期</td>
                      <td>{l.samples}</td>
                      <td>
                        {l.repeat} / {l.samples} ·{" "}
                        {percent(l.repeat, l.samples)}
                      </td>
                      <td>
                        {l.neighbor} / {l.samples} ·{" "}
                        {percent(l.neighbor, l.samples)}
                      </td>
                      <td>
                        {l.mirror === null
                          ? "仅数字支持"
                          : `${l.mirror} / ${l.samples} · ${percent(l.mirror, l.samples)}`}
                      </td>
                      <td>
                        <button
                          className="text-button"
                          aria-label={`使用滞后${l.lag}期`}
                          onClick={() => patch({ lag: l.lag })}
                        >
                          使用此滞后
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )
      )}
    </section>
  );
}
