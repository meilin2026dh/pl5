import EvidenceLab from "../components/EvidenceLab";
import InnovationLab from "../components/InnovationLab";
import ConditionLab from "../components/ConditionLab";
import SelectionLab from "../components/SelectionLab";
import PeriodRelations from "../components/PeriodRelations";
import { relationLabels } from "../domain/relations";
import { geometryLabels } from "../domain/geometry";
import GeometryRules from "../components/GeometryRules";
import ResearchRules, {
  ResearchDiagnosticsView,
} from "../components/ResearchRules";
import "../components/research.css";
import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Check,
  ChevronLeft,
  ChevronRight,
  Copy,
  Download,
  Hash,
  RefreshCw,
  Save,
  Trash2,
  X,
  Layers3,
} from "lucide-react";
import {
  type FilterInput,
  type FilterResult,
  defaultPositions,
  defaultRules,
  validateInput,
  ruleLabels,
} from "../domain/pick5";
import Rules from "../components/Rules";
import AdvancedRules from "../components/AdvancedRules";
import CandidateSource from "../components/CandidateSource";
import Backtest from "../components/Backtest";
import { download } from "../lib/plans";
import "../components/advanced.css";
function quickDigits(mode: string, digits: number[]) {
  const all = Array.from({ length: 10 }, (_, i) => i);
  switch (mode) {
    case "大":
      return all.filter((d) => d >= 5);
    case "小":
      return all.filter((d) => d < 5);
    case "奇":
      return all.filter((d) => d % 2 === 1);
    case "偶":
      return all.filter((d) => d % 2 === 0);
    default:
      return all.filter((d) => !digits.includes(d));
  }
}
const places = ["万位", "千位", "百位", "十位", "个位"];
export default function Workbench({
  input,
  setInput,
  onSave,
  notify,
  onOpenHistory,
}: {
  input: FilterInput;
  setInput: (i: FilterInput) => void;
  onSave: () => void;
  notify: (s: string) => void;
  onOpenHistory?: () => void;
}) {
  const [result, setResult] = useState<FilterResult | null>(null),
    [stamp, setStamp] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [page, setPage] = useState(0);
  const worker = useRef<Worker | null>(null),
    seq = useRef(0);
  const serialized = JSON.stringify(input);
  const current = useRef(serialized);
  current.current = serialized;
  const stale = Boolean(result) && stamp !== serialized;
  const active = input.rules.filter((r) => r.enabled);
  const size = 50;
  useEffect(
    () => () => {
      worker.current?.terminate();
    },
    [],
  );
  useEffect(() => {
    if (worker.current) {
      worker.current.terminate();
      worker.current = null;
      ++seq.current;
      setBusy(false);
    }
  }, [serialized]);
  const updatePosition = (i: number, values: number[]) =>
    setInput({
      ...input,
      positions: input.positions.map((v, j) => (j === i ? values : v)),
    });
  const calculate = () => {
    setError("");
    try {
      validateInput(input);
    } catch (e) {
      setError((e as Error).message);
      return;
    }
    worker.current?.terminate();
    const id = ++seq.current;
    setBusy(true);
    setPage(0);
    try {
      const w = new Worker(
        new URL("../workers/filter.worker.ts", import.meta.url),
        { type: "module" },
      );
      worker.current = w;
      w.onmessage = (e) => {
        if (e.data.requestId !== seq.current) return;
        setBusy(false);
        w.terminate();
        worker.current = null;
        if (e.data.error) {
          setError(e.data.error);
          return;
        }
        if (current.current !== serialized) return;
        setResult(e.data.result);
        setStamp(serialized);
      };
      w.onerror = () => {
        if (id !== seq.current) return;
        setBusy(false);
        setError("计算线程启动失败，请重试。");
        w.terminate();
        worker.current = null;
      };
      w.postMessage({ requestId: id, input });
    } catch {
      setBusy(false);
      setError("当前浏览器无法启动计算线程，请使用新版浏览器。");
    }
  };
  const cancel = () => {
    worker.current?.terminate();
    worker.current = null;
    ++seq.current;
    setBusy(false);
    notify("本次计算已取消");
  };
  const valid = result && !stale && !busy;
  const count =
    input.candidates?.length ??
    input.positions.reduce((a, p) => a * p.length, 1);
  const pages = result ? Math.ceil(result.numbers.length / size) : 0;
  const clear = () => {
    setInput({
      positions: defaultPositions(),
      rules: defaultRules(),
      history: input.history,
      historySource: input.historySource,
    });
    setError("");
  };
  const copy = async () => {
    if (!valid) return;
    try {
      await navigator.clipboard.writeText(result.numbers.join("\n"));
      notify("全部号码已复制");
    } catch {
      notify("复制失败，请使用导出 TXT");
    }
  };
  return (
    <>
      <div className="title-row">
        <div>
          <div className="eyebrow">
            <span className="tiny-dot" /> 排列五 · 组合过滤
          </div>
          <h1>
            少一点繁杂，<span>多一点清晰。</span>
          </h1>
          <p className="muted">把你的想法变成条件，让每一次筛选都有迹可循。</p>
        </div>
        <div className="head-actions">
          <a className="button secondary" href="#evidence-title">
            证据体检
          </a>
          <a className="button secondary" href="#innovation-title">
            覆盖审计
          </a>
          <a className="button secondary" href="#condition-title">
            条件体检
          </a>
          <a className="button secondary" href="#selection-title">
            多阶段精选
          </a>
          <a className="button secondary" href="#period-title">
            跨期关联
          </a>
          <a className="button secondary" href="#geometry-title">
            空间形态
          </a>
          <a className="button secondary" href="#research-title">
            实验方法
          </a>
          <button className="button secondary save-top" onClick={onSave}>
            <Save size={16} />
            保存方案
          </button>
        </div>
      </div>
      <div className="flow-strip">
        <span className="flow-active">
          <b>01</b>选择号码
        </span>
        <i />
        <span>
          <b>02</b>设置条件
        </span>
        <i />
        <span>
          <b>03</b>查看结果
        </span>
        <div className="flow-hint">你的组合，由你定义</div>
      </div>
      <div className="workspace-grid">
        <div className="workspace-left">
          <CandidateSource input={input} onChange={setInput} />
          <section className="card numbers-card">
            <div className="section-head">
              <h2>
                <Hash size={18} />
                号码选择
              </h2>
              <div className="head-actions">
                <button
                  className="text-button"
                  onClick={() =>
                    setInput({ ...input, positions: [[], [], [], [], []] })
                  }
                >
                  <Trash2 size={14} />
                  清空
                </button>
                <button
                  className="text-button"
                  onClick={() =>
                    setInput({ ...input, positions: defaultPositions() })
                  }
                >
                  全选
                </button>
              </div>
            </div>
            <div className="number-rows">
              {input.positions.map((digits, i) => (
                <div className="number-row" key={i}>
                  <span className="place-label">{places[i]}</span>
                  <div className="number-buttons">
                    {Array.from({ length: 10 }, (_, d) => (
                      <button
                        key={d}
                        aria-label={`${places[i]}号码${d}`}
                        aria-pressed={digits.includes(d)}
                        className={digits.includes(d) ? "selected" : ""}
                        onClick={() =>
                          updatePosition(
                            i,
                            digits.includes(d)
                              ? digits.filter((v) => v !== d)
                              : [...digits, d].sort((a, b) => a - b),
                          )
                        }
                      >
                        {d}
                      </button>
                    ))}
                  </div>
                  <div className="quick-select">
                    {["大", "小", "奇", "偶", "反"].map((t) => (
                      <button
                        key={t}
                        aria-label={`${places[i]}${t}`}
                        onClick={() =>
                          updatePosition(i, quickDigits(t, digits))
                        }
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <div className="number-footer">
              <span>
                <span className="green-dot" />
                定位复式 · 保留前导零
              </span>
              <span>
                当前候选 <strong>{count.toLocaleString()}</strong> 组
              </span>
            </div>
          </section>
          <Rules
            rules={input.rules}
            onChange={(rules) => setInput({ ...input, rules })}
          />
          <AdvancedRules
            input={input}
            onChange={setInput}
            historySource={input.historySource ?? "未载入历史数据"}
          />
          <ResearchRules input={input} onChange={setInput} />
          <SelectionLab input={input} onChange={setInput} />
          <EvidenceLab input={input} onChange={setInput} />
          <InnovationLab input={input} onChange={setInput} />
          <ConditionLab input={input} onChange={setInput} />
          <GeometryRules input={input} onChange={setInput} />
          <PeriodRelations
            input={input}
            onChange={setInput}
            onOpenHistory={onOpenHistory}
          />
          <div className="action-bar">
            {busy ? (
              <button className="button primary start-button" onClick={cancel}>
                <X size={16} />
                取消计算
              </button>
            ) : (
              <button
                className="button primary start-button"
                onClick={calculate}
              >
                开始缩水 <ArrowRight size={18} />
              </button>
            )}
            <button className="button secondary" onClick={clear}>
              <RefreshCw size={15} />
              重置全部
            </button>
          </div>
          {error && (
            <div className="error-box" role="alert">
              {error}
            </div>
          )}
        </div>
        <aside className="workspace-right">
          <section className="result-summary">
            <div className="summary-head">
              <span>筛选结果</span>
              <span className="live-pill">
                {busy
                  ? "计算中"
                  : stale
                    ? "条件已变更"
                    : result
                      ? "计算完成"
                      : "等待筛选"}
              </span>
            </div>
            <div className="result-number">
              {busy
                ? "···"
                : result
                  ? result.numbers.length.toLocaleString()
                  : "—"}
              <span>组保留</span>
            </div>
            <div className="summary-stats">
              <div>
                <span>原始组合</span>
                <strong>{(result?.initial ?? count).toLocaleString()}</strong>
              </div>
              <div>
                <span>精简比例</span>
                <strong>
                  {result
                    ? `${((1 - result.numbers.length / Math.max(1, result.initial)) * 100).toFixed(2)}%`
                    : "—"}
                </strong>
              </div>
            </div>
            <div className="progress-track">
              <div
                style={{
                  width: result
                    ? `${(1 - result.numbers.length / Math.max(1, result.initial)) * 100}%`
                    : "0%",
                }}
              />
            </div>
            <p>
              {stale
                ? "结果已过期，请重新缩水后导出。"
                : result
                  ? "条件过滤已完成，结果可核对、可导出。"
                  : "选好号码，点击「开始缩水」查看结果。"}
            </p>
          </section>
          <section className="card preview-card">
            <div className="section-head">
              <h2>号码预览</h2>
              <span className="muted small">每页 {size} 组</span>
            </div>
            {!result ? (
              <div className="empty-state">
                <div className="empty-icon">
                  <Layers3 size={28} />
                </div>
                <h3>留一点空间，给好思路</h3>
                <p>你的筛选结果将在这里呈现</p>
                <span>选号码 → 设条件 → 开始缩水</span>
              </div>
            ) : (
              <>
                <div
                  className={"preview-table " + (stale ? "stale" : "")}
                  aria-label="过滤结果"
                >
                  <div className="preview-table-head">
                    <span>序号</span>
                    {places.map((p) => (
                      <span key={p}>{p}</span>
                    ))}
                  </div>
                  {result.numbers
                    .slice(page * size, (page + 1) * size)
                    .map((n, i) => (
                      <div className="preview-number" key={n}>
                        <small>
                          {String(page * size + i + 1).padStart(2, "0")}
                        </small>
                        {n.split("").map((d, j) => (
                          <span key={j}>{d}</span>
                        ))}
                      </div>
                    ))}
                  {result.numbers.length === 0 && (
                    <p className="zero-result">
                      没有符合条件的组合。可关闭部分条件后重试。
                    </p>
                  )}
                </div>
                <div className="pagination">
                  <span>共 {result.numbers.length.toLocaleString()} 组</span>
                  <button
                    aria-label="上一页"
                    disabled={page === 0}
                    onClick={() => setPage(page - 1)}
                  >
                    <ChevronLeft size={15} />
                  </button>
                  <span>
                    {pages ? page + 1 : 0} / {pages}
                  </span>
                  <button
                    aria-label="下一页"
                    disabled={page + 1 >= pages}
                    onClick={() => setPage(page + 1)}
                  >
                    <ChevronRight size={15} />
                  </button>
                </div>
              </>
            )}
            <div className="export-actions">
              <button
                className="button secondary"
                disabled={!valid || result.numbers.length === 0}
                onClick={() => {
                  if (valid)
                    download("pl5-号码.txt", result.numbers.join("\n"));
                }}
              >
                <Download size={15} />
                导出 TXT
              </button>
              <button
                className="button primary"
                disabled={!valid || result.numbers.length === 0}
                onClick={copy}
              >
                <Copy size={15} />
                复制全部
              </button>
            </div>
          </section>
          <section className="condition-note">
            <div>
              <Check size={16} />
              <strong>已启用条件</strong>
              <span>{active.length} 项</span>
            </div>
            {active.length ? (
              <ul>
                {active.map((r) => (
                  <li key={r.id}>
                    {ruleLabels[r.kind]}
                    <span>
                      {r.mode === "exclude" ? "排除" : "保留"}{" "}
                      {r.kind === "relation"
                        ? relationLabels[r.relation!.method]
                        : r.kind === "geometry"
                          ? geometryLabels[r.geometry!.method]
                          : r.values.join("、") || "未选择"}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p>暂未设置条件，将保留所有定位组合。</p>
            )}
          </section>
        </aside>
      </div>
      <section className="card step-card">
        <h2>过滤明细</h2>
        {result ? (
          <div className="step-list">
            <div>
              <b>01</b>
              <span>
                原始候选<strong>{result.initial.toLocaleString()} 组</strong>
              </span>
            </div>
            {result.steps.map((s, i) => (
              <div key={s.id}>
                <ArrowRight size={14} />
                <b>{String(i + 2).padStart(2, "0")}</b>
                <span>
                  {s.label}
                  <strong>
                    {s.after.toLocaleString()} 组{" "}
                    <small>−{(s.before - s.after).toLocaleString()}</small>
                  </strong>
                </span>
              </div>
            ))}
            {result.steps.length === 0 && (
              <p className="muted small">未设置过滤条件，全部候选已保留。</p>
            )}
          </div>
        ) : (
          <p className="muted small">计算后可查看每个条件移除的组合数量。</p>
        )}
      </section>
      {valid && result.research && (
        <ResearchDiagnosticsView items={result.research} />
      )}
      <Backtest input={input} />
    </>
  );
}
