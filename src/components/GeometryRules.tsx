import { geometryExample } from "../domain/geometryExamples";
import { useEffect, useMemo, useState } from "react";
import {
  defaultGeometry,
  geometryLabels,
  geometryPoints,
  prepareGeometry,
  validateGeometry,
  type GeometryConfig,
  type GeometryMethod,
} from "../domain/geometry";
import type { FilterInput, Rule } from "../domain/pick5";
import "./geometry.css";
const layouts = {
  trend: "折线走势（横轴顺序，纵轴数字）",
  phone: "电话键盘（123在上）",
  calculator: "计算器键盘（789在上）",
};
const places = ["万位", "千位", "百位", "十位", "个位"];
const explanations: Record<GeometryMethod, string> = {
  line: "所有点到直线的垂距≤容差；全重合点不算直线。容差单位：坐标格。",
  polyline: "至少三个不同点，且不满足直线条件。容差单位：坐标格。",
  v: "横坐标不折返，允许竖直段；两臂各有横向跨度。屏幕纵坐标先增后减，恰好一个谷底，无水平段。折线走势中对应数字先降后升；键盘按屏幕坐标判断。",
  invertedV:
    "横坐标不折返，允许竖直段；两臂各有横向跨度。屏幕纵坐标先减后增，恰好一个峰顶，无水平段。折线走势中对应数字先升后降；键盘按屏幕坐标判断。",
  arithmetic: "各相邻差相等（允许恒定序列）。容差为差值的绝对残差。",
  geometric:
    "各项为正，公比为正且不等于1；逐项检查预测残差。例如前3位124、前4位1248。",
  fibonacci:
    "从第三项起，每项等于前两项之和；排除全零。例如11235、01123。容差为递推绝对残差。",
  triangle:
    "点集凸包恰有三个顶点，允许其他点在边上或内部。不要求连线闭合，容差不合并顶点。",
  trapezoid:
    "点集凸包恰有四个顶点，至少一组对边平行（包括平行四边形）。容差是归一化叉积，0为精确平行。",
  mirror:
    "点集关于边界框中线镜像对称，重复点须一一匹配；至少三个不同点。容差单位：坐标格。",
  central:
    "点集关于边界框中心对称，重复点须一一匹配；至少三个不同点。容差单位：坐标格。",
};
const stamp = (rule: Rule) => JSON.stringify({ ...rule, enabled: undefined });
export default function GeometryRules({
  input,
  onChange,
}: {
  input: FilterInput;
  onChange: (input: FilterInput) => void;
}) {
  const [draft, setDraft] = useState<Rule | null>(null),
    [editing, setEditing] = useState<{ id: string; stamp: string } | null>(
      null,
    );
  const [error, setError] = useState(""),
    [manualSample, setManualSample] = useState<string | null>(null);
  useEffect(() => {
    if (!editing) return;
    const original = input.rules.find((r) => r.id === editing.id);
    if (!original || stamp(original) !== editing.stamp) {
      setDraft(null);
      setEditing(null);
      setError("原空间条件已改变或移除，请重新编辑。");
    }
  }, [input.rules, editing]);
  const c = draft?.geometry;
  const automaticSample = useMemo(
    () => (c ? geometryExample(c, input.history) : null),
    [c, input.history],
  );
  const sample = manualSample ?? automaticSample ?? "";
  const patch = (change: Partial<GeometryConfig>) =>
    setDraft((d) => d && { ...d, geometry: { ...d.geometry!, ...change } });
  const start = (rule?: Rule) => {
    setManualSample(null);
    setDraft(
      rule
        ? structuredClone(rule)
        : {
            id: crypto.randomUUID(),
            kind: "geometry",
            enabled: true,
            mode: "include",
            values: [],
            geometry: { ...defaultGeometry },
          },
    );
    setEditing(rule ? { id: rule.id, stamp: stamp(rule) } : null);
    setError("");
  };
  const save = () => {
    if (!draft || !c) return;
    try {
      const original = editing
        ? input.rules.find((r) => r.id === editing.id)
        : undefined;
      if (editing && (!original || stamp(original) !== editing.stamp))
        throw new Error("原空间条件已改变或移除，请重新编辑。");
      validateGeometry(c);
      prepareGeometry(c, input.history);
      const saved = { ...draft, enabled: original?.enabled ?? draft.enabled };
      onChange({
        ...input,
        rules: original
          ? input.rules.map((r) => (r.id === saved.id ? saved : r))
          : [...input.rules, saved],
      });
      setDraft(null);
      setEditing(null);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  };
  let preview: {
      digits: number[];
      points: [number, number][];
      matches: boolean;
      lastIssue?: string;
    } | null = null,
    previewError = "";
  if (c) {
    try {
      if (!/^\d{5}$/.test(sample))
        throw new Error(
          manualSample === null
            ? "当前条件暂无符合示例，可调整条件或手动输入号码检查。"
            : "预览请输入完整五位号码，保留前导零。",
        );
      const p = prepareGeometry(c, input.history),
        digits = p.digits(sample);
      preview = {
        digits,
        points: geometryPoints(digits, c.layout),
        matches: p.test(sample),
        lastIssue: p.diagnostics.lastIssue,
      };
    } catch (e) {
      previewError = (e as Error).message;
    }
  }
  const rules = input.rules.filter((r) => r.kind === "geometry");
  const numeric =
    !!c && ["arithmetic", "geometric", "fibonacci"].includes(c.method);
  return (
    <section className="card geometry-card" aria-labelledby="geometry-title">
      <div className="section-head">
        <h2 id="geometry-title">
          空间形态过滤 <span className="muted">{rules.length}</span>
        </h2>
        <button className="button secondary" onClick={() => start()}>
          添加空间条件
        </button>
      </div>
      <p className="muted small">
        观察连线、间距与点集形状。坐标由规则固定，结果可复算；单注条件与历史衔接条件可组合。
      </p>
      {rules.map((r) => (
        <div className="geometry-rule" key={r.id}>
          <label>
            <input
              type="checkbox"
              aria-label={`启用空间条件 ${geometryLabels[r.geometry!.method]}`}
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
            {geometryLabels[r.geometry!.method]}
          </label>
          <small>
            {r.mode === "include" ? "保留" : "排除"} ·{" "}
            {layouts[r.geometry!.layout]} ·{" "}
            {r.geometry!.source === "number"
              ? `从${places[r.geometry!.position]}起${r.geometry!.length}点`
              : `${places[r.geometry!.position]}历史+候选，共${r.geometry!.length}点`}{" "}
            · 容差 {r.geometry!.tolerance}
            {r.geometry!.referenceIssue
              ? ` · 截至${r.geometry!.referenceIssue}期`
              : ""}
          </small>
          <div className="head-actions">
            <button
              className="text-button"
              aria-label={`编辑空间条件 ${geometryLabels[r.geometry!.method]}`}
              onClick={() => start(r)}
            >
              编辑
            </button>
            <button
              className="text-button"
              aria-label={`删除空间条件 ${geometryLabels[r.geometry!.method]}`}
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
        </div>
      ))}
      {draft && c && (
        <div className="geometry-editor">
          <h3>{editing ? "编辑空间条件" : "新建空间条件"}</h3>
          <div className="geometry-fields">
            <label>
              空间方法
              <select
                aria-label="空间方法"
                value={c.method}
                onChange={(e) => {
                  const method = e.target.value as GeometryMethod;
                  patch({
                    method,
                    ...(method === "geometric"
                      ? { length: c.sequence === "gaps" ? 4 : 3, position: 0 }
                      : {}),
                  });
                }}
              >
                {Object.entries(geometryLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              坐标布局
              <select
                aria-label="坐标布局"
                value={c.layout}
                onChange={(e) =>
                  patch({ layout: e.target.value as GeometryConfig["layout"] })
                }
              >
                {Object.entries(layouts).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              路径来源
              <select
                aria-label="路径来源"
                value={c.source}
                onChange={(e) =>
                  patch({
                    source: e.target.value as GeometryConfig["source"],
                    position: 0,
                    referenceIssue: undefined,
                  })
                }
              >
                <option value="number">单注连续位置</option>
                <option value="history">历史轨迹 + 候选位</option>
              </select>
            </label>
            <label>
              路径点数
              <select
                aria-label="路径点数"
                value={c.length}
                onChange={(e) =>
                  patch({
                    length: Number(e.target.value),
                    position: c.source === "number" ? 0 : c.position,
                  })
                }
              >
                {[3, 4, 5].map((n) => (
                  <option key={n} value={n}>
                    {n} 点
                  </option>
                ))}
              </select>
            </label>
            <label>
              {c.source === "number" ? "起始位置" : "分析位置"}
              <select
                aria-label="空间位置"
                value={c.position}
                onChange={(e) => patch({ position: Number(e.target.value) })}
              >
                {places
                  .slice(0, c.source === "number" ? 6 - c.length : 5)
                  .map((p, i) => (
                    <option key={p} value={i}>
                      {p}
                    </option>
                  ))}
              </select>
            </label>
            {c.source === "history" && (
              <label>
                历史截止期（空为最新）
                <input
                  aria-label="空间参考期"
                  value={c.referenceIssue ?? ""}
                  onChange={(e) =>
                    patch({
                      referenceIssue: e.target.value.trim() || undefined,
                    })
                  }
                />
              </label>
            )}
            {numeric && (
              <label>
                规律对象
                <select
                  aria-label="规律对象"
                  value={c.sequence}
                  onChange={(e) =>
                    patch({
                      sequence: e.target.value as GeometryConfig["sequence"],
                      ...(e.target.value === "gaps" && c.length < 4
                        ? { length: 4, position: 0 }
                        : {}),
                    })
                  }
                >
                  <option value="digits">原数字序列</option>
                  <option value="gaps">相邻点欧氏距离序列</option>
                </select>
              </label>
            )}
            {c.method === "mirror" && (
              <label>
                镜像轴
                <select
                  aria-label="镜像轴"
                  value={c.axis}
                  onChange={(e) =>
                    patch({ axis: e.target.value as GeometryConfig["axis"] })
                  }
                >
                  <option value="vertical">垂直中线</option>
                  <option value="horizontal">水平中线</option>
                </select>
              </label>
            )}
            <label>
              判定容差（0—0.25）
              <input
                aria-label="空间容差"
                type="number"
                min="0"
                max="0.25"
                step="0.01"
                value={Number.isFinite(c.tolerance) ? c.tolerance : ""}
                onChange={(e) =>
                  patch({
                    tolerance:
                      e.target.value === "" ? NaN : Number(e.target.value),
                  })
                }
              />
            </label>
            <label>
              空间模式
              <select
                aria-label="空间模式"
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
                aria-label="空间分组"
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
          {c.source === "history" && (
            <p className="notice small">
              历史来源：{input.historySource || "未标注来源"} ·{" "}
              {input.history?.length ?? 0}条。按记录顺序取最近{c.length - 1}
              期，不推断日期连续性。
            </p>
          )}
          <p className="geometry-definition">{explanations[c.method]}</p>
          {c.method === "geometric" &&
            c.sequence === "digits" &&
            c.length === 5 && (
              <p className="notice small">
                0—9内五项非恒定正整数等比序列无精确解，请选择3或4点。
              </p>
            )}
          <div className="geometry-preview">
            <div>
              <label>
                预览五位号码
                <input
                  aria-label="预览五位号码"
                  inputMode="numeric"
                  maxLength={5}
                  value={sample}
                  onChange={(e) => setManualSample(e.target.value)}
                />
              </label>
              <p className="muted small">
                {manualSample === null
                  ? "自动示例 · 随方法和布局切换"
                  : "手动号码 · 切换方法时保留"}
              </p>
              <button
                type="button"
                className="text-button"
                onClick={() => setManualSample(null)}
              >
                使用当前方法示例
              </button>
              {!automaticSample && (
                <p className="muted small">
                  当前参数或历史下没有可用的符合示例；可调整条件或手动输入号码检查。
                </p>
              )}
              <p className="muted small">
                {c.source === "number"
                  ? "按位置顺序取点，不排序。"
                  : "只取截止期以前的历史，再追加候选位。"}{" "}
                {c.layout === "trend"
                  ? "横轴为顺序，纵轴数字从0到9向上递增。"
                  : "按键盘实际坐标连线，0位于下方中间。"}
              </p>
              {preview && (
                <>
                  <strong
                    className={preview.matches ? "geometry-match" : "muted"}
                  >
                    {preview.matches ? "预览符合此条件" : "预览不符合此条件"}
                  </strong>
                  <p className="small">
                    路径数字：{preview.digits.join(" → ")}
                    {preview.lastIssue
                      ? ` · 历史截至 ${preview.lastIssue} 期`
                      : ""}
                  </p>
                  <p className="muted small">
                    这里显示原始匹配；选择排除模式时保留不匹配项。
                  </p>
                </>
              )}
              {previewError && <p className="validation">{previewError}</p>}
            </div>
            {preview && (
              <svg viewBox="0 0 280 180" role="img" aria-label="空间轨迹预览">
                {c.layout !== "trend" &&
                  Array.from({ length: 10 }, (_, d) => {
                    const [x, y] = geometryPoints([d], c.layout)[0];
                    return (
                      <g key={d}>
                        <rect
                          x={25 + x * 95}
                          y={12 + y * 48}
                          width="32"
                          height="24"
                          rx="6"
                          fill="#fff3e5"
                        />
                        <text
                          x={41 + x * 95}
                          y={28 + y * 48}
                          textAnchor="middle"
                          fill="#a1978c"
                          fontSize="12"
                        >
                          {d}
                        </text>
                      </g>
                    );
                  })}
                <polyline
                  points={preview.points
                    .map(
                      ([x, y]) =>
                        `${c.layout === "trend" ? 25 + x * 55 : 41 + x * 95},${c.layout === "trend" ? 15 + y * 16 : 24 + y * 48}`,
                    )
                    .join(" ")}
                  fill="none"
                  stroke="#f47b25"
                  strokeWidth="2.5"
                />
                {preview.points.map(([x, y], i) => (
                  <g key={i}>
                    <circle
                      cx={c.layout === "trend" ? 25 + x * 55 : 41 + x * 95}
                      cy={c.layout === "trend" ? 15 + y * 16 : 24 + y * 48}
                      r="5"
                      fill="#f47b25"
                    />
                    <text
                      x={c.layout === "trend" ? 25 + x * 55 : 41 + x * 95}
                      y={(c.layout === "trend" ? 15 + y * 16 : 24 + y * 48) - 8}
                      textAnchor="middle"
                      fill="#68402a"
                      fontSize="11"
                    >
                      {i + 1}:{preview!.digits[i]}
                    </text>
                  </g>
                ))}
              </svg>
            )}
          </div>
          <div className="head-actions">
            <button className="button primary" onClick={save}>
              保存空间条件
            </button>
            <button
              className="button secondary"
              onClick={() => {
                setDraft(null);
                setEditing(null);
                setError("");
              }}
            >
              取消空间编辑
            </button>
          </div>
        </div>
      )}
      {error && (
        <p className="validation" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
