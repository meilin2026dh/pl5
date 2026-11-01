import { useEffect, useMemo, useRef, useState } from "react";
import { metrics, type Rule } from "../domain/pick5";
import {
  historyCsv,
  emptyHistoryRange,
  filterHistory,
  officialHistoryUrl,
  readHistoryCache,
  writeHistoryCache,
  validateSnapshot,
  type HistorySnapshot,
  isAdjacent,
  makeDemo,
  omissions,
  parseHistoryCsv,
  type Draw,
} from "../lib/history";
import "./history.css";
const names = ["万位", "千位", "百位", "十位", "个位"];
type Indicator = "sum" | "span" | "tail";
const tabs = [
  ["matrix", "定位走势"],
  ["line", "指标折线"],
  ["bar", "号码频次"],
  ["heat", "位置热力"],
  ["category", "形态分布"],
  ["table", "开奖明细"],
];
const measure = (d: Draw, key: Indicator) => {
  const values = metrics(d.number);
  return values[key];
};
export default function History({
  onApply,
  onDataChange,
}: {
  onApply: (rules: Rule[]) => void;
  onDataChange?: (draws: Draw[], source: string) => void;
}) {
  const [all, setAll] = useState<Draw[]>(() => makeDemo());
  const [source, setSource] = useState("演示数据 · 非真实开奖");
  const [window, setWindow] = useState(50);
  const [view, setView] = useState("matrix");
  const [pos, setPos] = useState(0);
  const [indicator, setIndicator] = useState<Indicator>("sum");
  const [error, setError] = useState("");
  const [min, setMin] = useState("15");
  const [max, setMax] = useState("30");
  const [preview, setPreview] = useState(false);
  const [notice, setNotice] = useState("");
  const file = useRef<HTMLInputElement>(null);
  const generation = useRef(0);
  const request = useRef<AbortController | null>(null);
  const lineSvg = useRef<SVGSVGElement>(null);
  const [loading, setLoading] = useState(false);
  const [queryCount, setQueryCount] = useState(200);
  const [metadata, setMetadata] = useState<HistorySnapshot | null>(null);
  const [rangeDraft, setRangeDraft] = useState(emptyHistoryRange);
  const [range, setRange] = useState(emptyHistoryRange);
  const [showOmission, setShowOmission] = useState(true);
  const [connections, setConnections] = useState(false);
  const [classification, setClassification] = useState("odd");
  const [selected, setSelected] = useState<Draw | null>(null);
  const filtered = useMemo(() => filterHistory(all, range), [all, range]);
  const draws = useMemo(
    () => filtered.slice(-Math.min(window, 2000)),
    [filtered, window],
  );
  const callback = useRef(onDataChange);
  callback.current = onDataChange;
  useEffect(() => {
    callback.current?.(all, source);
  }, [all, source]);
  useEffect(() => {
    const ticket = generation.current;
    void readHistoryCache()
      .then((snapshot) => {
        if (snapshot && generation.current === ticket) {
          setAll(snapshot.draws);
          setSource(snapshot.source);
          setMetadata(snapshot);
          setNotice("已恢复本机历史数据缓存");
        }
      })
      .catch(() => {})
      .finally(() => {
        if (generation.current === ticket) void fetchOfficial();
      });
    return () => {
      generation.current++;
      request.current?.abort();
    };
  }, []);
  function replaceData(snapshot: HistorySnapshot) {
    setAll(snapshot.draws);
    setSource(snapshot.source);
    setMetadata(snapshot);
    setSelected(null);
    setRange(emptyHistoryRange);
    setRangeDraft(emptyHistoryRange);
    const ticket = generation.current;
    void writeHistoryCache(snapshot).catch(() => {
      if (ticket === generation.current)
        setNotice("数据已加载，但本机缓存不可用");
    });
  }
  async function fetchOfficial() {
    const ticket = ++generation.current;
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    const timeout = globalThis.setTimeout(() => controller.abort(), 30000);
    setLoading(true);
    setError("");
    try {
      const response = await fetch(officialHistoryUrl(queryCount), {
        signal: controller.signal,
      });
      if (!response.ok)
        throw new Error(`获取失败（${response.status}），请稍后重试`);
      const snapshot = validateSnapshot(await response.json());
      if (ticket !== generation.current) return;
      replaceData(snapshot);
      setNotice(
        snapshot.warning || `已加载 ${snapshot.draws.length} 期真实开奖`,
      );
    } catch (e) {
      if (ticket === generation.current)
        setError(
          controller.signal.aborted
            ? "请求已超时或取消，请重试；当前数据已保留"
            : (e as Error).message,
        );
    } finally {
      globalThis.clearTimeout(timeout);
      if (ticket === generation.current) setLoading(false);
    }
  }
  function exportSvg() {
    if (!lineSvg.current) return;
    const clone = lineSvg.current.cloneNode(true) as SVGSVGElement;
    clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    const url = URL.createObjectURL(
      new Blob([new XMLSerializer().serializeToString(clone)], {
        type: "image/svg+xml",
      }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "pl5-history-line.svg";
    a.click();
    URL.revokeObjectURL(url);
  }
  const omission = useMemo(
    () =>
      view === "matrix" ? omissions(filtered, pos, Math.min(window, 2000)) : [],
    [filtered, pos, window, view],
  );
  const freq = Array.from(
    { length: 10 },
    (_, n) => draws.filter((d) => Number(d.number[pos]) === n).length,
  );
  const maxFreq = Math.max(1, ...freq);
  const ruleValid =
    Number.isInteger(Number(min)) &&
    Number.isInteger(Number(max)) &&
    min !== "" &&
    max !== "" &&
    Number(min) >= 0 &&
    Number(max) >= Number(min) &&
    Number(max) <= (indicator === "sum" ? 45 : 9);
  function download() {
    const url = URL.createObjectURL(
      new Blob([historyCsv(draws)], { type: "text/csv;charset=utf-8" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "pl5-history.csv";
    a.click();
    URL.revokeObjectURL(url);
  }
  async function importFile(f: File | undefined) {
    if (!f) return;
    const ticket = ++generation.current;
    request.current?.abort();
    setLoading(true);
    setError("");
    try {
      if (f.size > 10 * 1024 * 1024) throw new Error("文件不能超过 10 MiB");
      const result = parseHistoryCsv(await f.text());
      if (ticket !== generation.current) return;
      replaceData({
        draws: result,
        source: `导入文件：${f.name}`,
        version: "csv-v1",
        updatedAt: new Date().toISOString(),
      });
      setNotice(`已导入 ${result.length} 条记录`);
    } catch (e) {
      if (ticket === generation.current) setError((e as Error).message);
    } finally {
      if (ticket === generation.current) setLoading(false);
      if (file.current) file.current.value = "";
    }
  }
  const categories = (() => {
    const values = new Map<string, number>();
    draws.forEach((d) => {
      const m = metrics(d.number);
      const digits = [...d.number].map(Number);
      const n =
        classification === "big"
          ? m.big
          : classification === "prime"
            ? m.prime
            : m.odd;
      const label =
        classification === "012"
          ? [0, 1, 2]
              .map((r) => digits.filter((n) => n % 3 === r).length)
              .join(":")
          : classification === "big"
            ? `${n} 大 ${5 - n} 小`
            : classification === "prime"
              ? `${n} 质 ${5 - n} 非质`
              : `${n} 奇 ${5 - n} 偶`;
      values.set(label, (values.get(label) || 0) + 1);
    });
    return [...values.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  })();
  return (
    <div className="h-page">
      <div className="h-heading">
        <div>
          <div className="eyebrow">HISTORY & INSIGHTS</div>
          <h1 className="page-title">
            每一期，都有迹可循<span className="h-dot">.</span>
          </h1>
          <p className="muted">用不同视角观察历史，按自己的规则做选择。</p>
        </div>
        <button
          disabled={loading}
          className="button secondary"
          onClick={() => file.current?.click()}
        >
          ↥ 导入 CSV
        </button>
        <input
          ref={file}
          type="file"
          accept=".csv,text/csv"
          hidden
          onChange={(e) => void importFile(e.target.files?.[0])}
        />
      </div>
      <div className="h-source">
        <label>
          真实开奖期数{" "}
          <select
            value={queryCount}
            disabled={loading}
            onChange={(e) => setQueryCount(Number(e.target.value))}
          >
            {[200, 500, 1000, 2000].map((n) => (
              <option value={n} key={n}>
                {n} 期
              </option>
            ))}
          </select>
        </label>
        <button disabled={loading} onClick={() => void fetchOfficial()}>
          {loading ? "正在加载…" : "获取官方开奖"}
        </button>
        <span className="h-source-badge">{source}</span>
        <span>
          数据版本：{metadata?.version || "demo-v1"} · {all.length} 条 ·{" "}
          {all[0]?.date} — {all.at(-1)?.date}
        </span>
        <button
          onClick={() => {
            generation.current++;
            request.current?.abort();
            setLoading(false);
            setError("");
            replaceData({
              draws: makeDemo(),
              source: "演示数据 · 非真实开奖",
              version: "demo-v1",
            });
            setNotice("已切换到演示数据");
          }}
        >
          恢复演示
        </button>
      </div>
      {metadata?.sourceUrl && !metadata.stale && (
        <p className="h-help" role="status">
          北京时间 {new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Shanghai" }).format(new Date())} ·
          官方最新已公布：{all.at(-1)?.date}（第 {all.at(-1)?.issue} 期）。
          {all.at(-1)?.date !== new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Shanghai" }).format(new Date())
            ? "今日结果尚未返回，可点击获取官方开奖再次检查。"
            : "今日开奖已更新。"}
        </p>
      )}
      {metadata?.sourceUrl && (
        <p className="h-help">
          <a href={metadata.sourceUrl} target="_blank" rel="noreferrer">
            查看开奖来源
          </a>{" "}
          · 更新时间：{metadata.updatedAt || "未知"}
          {metadata.stale && " · 缓存数据，尚未刷新"}
        </p>
      )}
      <div className="h-range">
        <label>
          开始日期
          <input
            type="date"
            value={rangeDraft.fromDate}
            onChange={(e) =>
              setRangeDraft({ ...rangeDraft, fromDate: e.target.value })
            }
          />
        </label>
        <label>
          结束日期
          <input
            type="date"
            value={rangeDraft.toDate}
            onChange={(e) =>
              setRangeDraft({ ...rangeDraft, toDate: e.target.value })
            }
          />
        </label>
        <label>
          起始期号
          <input
            inputMode="numeric"
            value={rangeDraft.fromIssue}
            onChange={(e) =>
              setRangeDraft({ ...rangeDraft, fromIssue: e.target.value })
            }
          />
        </label>
        <label>
          结束期号
          <input
            inputMode="numeric"
            value={rangeDraft.toIssue}
            onChange={(e) =>
              setRangeDraft({ ...rangeDraft, toIssue: e.target.value })
            }
          />
        </label>
        <button
          className="button secondary"
          onClick={() => {
            if (
              (rangeDraft.fromDate &&
                rangeDraft.toDate &&
                rangeDraft.fromDate > rangeDraft.toDate) ||
              [rangeDraft.fromIssue, rangeDraft.toIssue].some(
                (v) => v && !/^\d{1,20}$/.test(v),
              ) ||
              (rangeDraft.fromIssue &&
                rangeDraft.toIssue &&
                BigInt(rangeDraft.fromIssue) > BigInt(rangeDraft.toIssue))
            ) {
              setError("请输入有效的日期与期号范围");
              return;
            }
            setError("");
            setRange({ ...rangeDraft });
            setSelected(null);
          }}
        >
          应用范围
        </button>
        <button
          className="button secondary"
          onClick={() => {
            setRange(emptyHistoryRange);
            setRangeDraft(emptyHistoryRange);
            setError("");
          }}
        >
          重置范围
        </button>
      </div>
      {error && (
        <div role="alert" className="h-error">
          {error}
        </div>
      )}
      {notice && (
        <p role="status" className="h-notice">
          {notice}
        </p>
      )}
      <div className="h-stats">
        <div>
          <span>观察期数</span>
          <strong>
            {draws.length}
            <small> 期</small>
          </strong>
        </div>
        <div>
          <span>平均和值</span>
          <strong>
            {(
              draws.reduce((s, d) => s + measure(d, "sum"), 0) /
              Math.max(1, draws.length)
            ).toFixed(1)}
          </strong>
        </div>
        <div>
          <span>平均跨度</span>
          <strong>
            {(
              draws.reduce((s, d) => s + measure(d, "span"), 0) /
              Math.max(1, draws.length)
            ).toFixed(1)}
          </strong>
        </div>
        <div>
          <span>数据用途</span>
          <strong className="h-text-stat">
            历史观察<small> 不代表未来概率</small>
          </strong>
        </div>
      </div>
      <section className="card h-chart-card">
        <div className="h-toolbar">
          <div className="h-tabs" role="tablist" aria-label="走势图形式">
            {tabs.map(([id, label]) => (
              <button
                key={id}
                role="tab"
                aria-selected={view === id}
                className={view === id ? "active" : ""}
                onClick={() => setView(id)}
              >
                {label}
              </button>
            ))}
          </div>
          <label>
            观察范围{" "}
            <select
              value={window}
              onChange={(e) => setWindow(Number(e.target.value))}
            >
              {[30, 50, 100, 200, 500, 1000, 2000].map((n) => (
                <option key={n} value={n}>
                  近 {n} 期
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="h-chart-top">
          <div>
            <h2>{tabs.find((t) => t[0] === view)?.[1]}</h2>
            <p className="muted">
              {view === "matrix"
                ? "圆点为当期号码；灰色数字为已观察记录的未出现次数；≥ 表示边界前未知。连续性未核验。"
                : "统计仅基于当前范围；连续性未核验，非相邻日期保守断线（含休市）。"}
            </p>
          </div>
          {["matrix", "bar"].includes(view) && (
            <label>
              选择位置{" "}
              <select
                value={pos}
                onChange={(e) => setPos(Number(e.target.value))}
              >
                {names.map((n, i) => (
                  <option key={n} value={i}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
          )}
          {view === "line" && (
            <label>
              指标{" "}
              <select
                value={indicator}
                onChange={(e) => {
                  setIndicator(e.target.value as Indicator);
                  setMax(e.target.value === "sum" ? "30" : "9");
                  setMin("0");
                  setPreview(false);
                }}
              >
                <option value="sum">和值</option>
                <option value="span">跨度</option>
                <option value="tail">和尾</option>
              </select>
            </label>
          )}
        </div>
        <div className="h-chart-options">
          {view === "matrix" && (
            <>
              <label>
                <input
                  type="checkbox"
                  checked={showOmission}
                  onChange={(e) => setShowOmission(e.target.checked)}
                />
                显示遗漏
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={connections}
                  onChange={(e) => setConnections(e.target.checked)}
                />
                显示号码连线
              </label>
            </>
          )}
          {view === "category" && (
            <label>
              分类口径{" "}
              <select
                value={classification}
                onChange={(e) => setClassification(e.target.value)}
              >
                <option value="odd">奇偶比</option>
                <option value="big">大小比（5–9 为大）</option>
                <option value="prime">质类比（1、2、3、5、7）</option>
                <option value="012">012 路个数</option>
              </select>
            </label>
          )}
          <button
            className="button secondary"
            onClick={view === "line" ? exportSvg : download}
          >
            {view === "line" ? "导出折线 SVG" : "导出当前范围 CSV"}
          </button>
        </div>
        {draws.length === 0 && (
          <p className="h-empty" role="status">
            当前范围没有开奖记录，请调整范围。
          </p>
        )}
        {view === "matrix" && connections && (
          <div className="h-line">
            <svg
              viewBox="0 0 960 180"
              role="img"
              aria-label={`${names[pos]}号码连接图`}
            >
              {draws
                .slice(1)
                .map(
                  (d, i) =>
                    isAdjacent(draws[i], d) && (
                      <line
                        key={d.issue}
                        x1={30 + (i * 900) / Math.max(1, draws.length - 1)}
                        x2={
                          30 + ((i + 1) * 900) / Math.max(1, draws.length - 1)
                        }
                        y1={150 - Number(draws[i].number[pos]) * 14}
                        y2={150 - Number(d.number[pos]) * 14}
                        stroke="#f47731"
                        strokeWidth="2"
                      />
                    ),
                )}
              {draws.map((d, i) => (
                <circle
                  key={d.issue}
                  cx={30 + (i * 900) / Math.max(1, draws.length - 1)}
                  cy={150 - Number(d.number[pos]) * 14}
                  r="3"
                  fill="#f47731"
                >
                  <title>
                    {d.issue}：{d.number[pos]}
                  </title>
                </circle>
              ))}
            </svg>
          </div>
        )}
        {view === "matrix" && (
          <div className="h-table-scroll h-matrix-scroll">
            <table className="h-table h-matrix">
              <thead>
                <tr>
                  <th>期号 / 日期</th>
                  <th>开奖号码</th>
                  {Array.from({ length: 10 }, (_, n) => (
                    <th key={n}>{n}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {draws.map((d, i) => (
                  <tr
                    key={d.issue}
                    tabIndex={0}
                    aria-label={`查看 ${d.issue} 期详情`}
                    onClick={() => setSelected(d)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        setSelected(d);
                      }
                    }}
                  >
                    <td>
                      {d.issue}
                      <small>{d.date}</small>
                    </td>
                    <td className="h-number">{d.number}</td>
                    {(omission[i] || []).map((o, n) => (
                      <td key={n}>
                        {Number(d.number[pos]) === n ? (
                          <span className="h-hit">{n}</span>
                        ) : showOmission ? (
                          <span className="h-omit">
                            {o.lowerBound ? "≥" : ""}
                            {o.value}
                          </span>
                        ) : null}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {view === "line" && (
          <div className="h-line">
            <svg
              ref={lineSvg}
              viewBox="0 0 960 290"
              role="img"
              aria-label={`${indicator === "sum" ? "和值" : indicator === "span" ? "跨度" : "和尾"}历史折线图`}
            >
              <defs>
                <linearGradient id="h-fill" x1="0" x2="0" y1="0" y2="1">
                  <stop stopColor="#ff7d35" stopOpacity=".2" />
                  <stop offset="1" stopColor="#ff7d35" stopOpacity="0" />
                </linearGradient>
              </defs>
              {[0, 1, 2, 3].map((i) => (
                <g key={i}>
                  <line
                    x1="40"
                    x2="940"
                    y1={30 + i * 70}
                    y2={30 + i * 70}
                    stroke="#eee8e1"
                  />
                  <text x="8" y={35 + i * 70}>
                    {Math.round((indicator === "sum" ? 45 : 9) * (1 - i / 3))}
                  </text>
                </g>
              ))}
              {draws
                .slice(1)
                .map(
                  (d, i) =>
                    isAdjacent(draws[i], d) && (
                      <line
                        key={d.issue}
                        x1={40 + (i * 900) / Math.max(1, draws.length - 1)}
                        x2={
                          40 + ((i + 1) * 900) / Math.max(1, draws.length - 1)
                        }
                        y1={
                          240 -
                          (measure(draws[i], indicator) /
                            (indicator === "sum" ? 45 : 9)) *
                            210
                        }
                        y2={
                          240 -
                          (measure(d, indicator) /
                            (indicator === "sum" ? 45 : 9)) *
                            210
                        }
                        stroke="#f47731"
                        strokeWidth="2.5"
                      />
                    ),
                )}
              {draws.map((d, i) => (
                <circle
                  key={d.issue}
                  cx={40 + (i * 900) / Math.max(1, draws.length - 1)}
                  cy={
                    240 -
                    (measure(d, indicator) / (indicator === "sum" ? 45 : 9)) *
                      210
                  }
                  r="3.5"
                  fill="#f47731"
                >
                  <title>
                    {d.issue} · {d.date} · {measure(d, indicator)}
                  </title>
                </circle>
              ))}
              <text x="40" y="275">
                {draws[0]?.date}
              </text>
              <text x="850" y="275">
                {draws.at(-1)?.date}
              </text>
            </svg>
          </div>
        )}
        {view === "bar" && (
          <div
            className="h-bars"
            role="img"
            aria-label={`${names[pos]}号码出现次数`}
          >
            {freq.map((n, i) => (
              <div className="h-bar-column" key={i}>
                <strong>{n}</strong>
                <div className="h-bar-track">
                  <div style={{ height: `${(n / maxFreq) * 100}%` }} />
                </div>
                <span>{i}</span>
              </div>
            ))}
          </div>
        )}
        {view === "heat" && (
          <div className="h-table-scroll">
            <table className="h-table h-heat">
              <thead>
                <tr>
                  <th>位置 / 号码</th>
                  {Array.from({ length: 10 }, (_, n) => (
                    <th key={n}>{n}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {names.map((name, p) => (
                  <tr key={name}>
                    <th>{name}</th>
                    {Array.from({ length: 10 }, (_, n) => {
                      const count = draws.filter(
                        (d) => Number(d.number[p]) === n,
                      ).length;
                      return (
                        <td key={n}>
                          <span
                            style={{
                              background: `rgba(245,113,42,${0.07 + (count / Math.max(1, draws.length)) * 2})`,
                            }}
                          >
                            {count}
                            <small>次</small>
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="muted">颜色越深，当前范围内出现次数越多。</p>
          </div>
        )}
        {view === "category" && (
          <div className="h-categories">
            {categories.map(([label, n]) => (
              <div key={label}>
                <span>{label}</span>
                <div className="h-category-track">
                  <i
                    style={{
                      width: `${(n / Math.max(1, draws.length)) * 100}%`,
                    }}
                  />
                </div>
                <strong>
                  {n}
                  <small>
                    {" "}
                    次 · {((n / Math.max(1, draws.length)) * 100).toFixed(0)}%
                  </small>
                </strong>
              </div>
            ))}
          </div>
        )}
        {view === "table" && (
          <>
            <div className="h-table-scroll">
              <table className="h-table">
                <thead>
                  <tr>
                    {[
                      "期号",
                      "日期",
                      "开奖号码",
                      "和值",
                      "跨度",
                      "和尾",
                      "奇偶比",
                    ].map((n) => (
                      <th key={n}>{n}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...draws].reverse().map((d) => (
                    <tr
                      key={d.issue}
                      tabIndex={0}
                      aria-label={`查看 ${d.issue} 期详情`}
                      onClick={() => setSelected(d)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          setSelected(d);
                        }
                      }}
                    >
                      <td>{d.issue}</td>
                      <td>{d.date}</td>
                      <td className="h-number">{d.number}</td>
                      <td>{measure(d, "sum")}</td>
                      <td>{measure(d, "span")}</td>
                      <td>{measure(d, "tail")}</td>
                      <td>
                        {metrics(d.number).odd} : {5 - metrics(d.number).odd}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
      {selected && (
        <section className="card h-details" aria-label="开奖详情">
          <button
            className="button secondary"
            onClick={() => setSelected(null)}
          >
            关闭详情
          </button>
          <h2>
            {selected.issue} 期 · {selected.date}
          </h2>
          <p className="h-number">{selected.number}</p>
          <p>
            和值 {metrics(selected.number).sum} · 跨度{" "}
            {metrics(selected.number).span} · 和尾{" "}
            {metrics(selected.number).tail} · 奇偶{" "}
            {metrics(selected.number).odd}:{5 - metrics(selected.number).odd} ·
            大小 {metrics(selected.number).big}:
            {5 - metrics(selected.number).big}
          </p>
          <p className="muted">大小以 5 为界；质类为 1、2、3、5、7（彩票分类约定）。</p>
        </section>
      )}
      <section className="card h-apply">
        <div>
          <div className="eyebrow">FROM INSIGHT TO RULE</div>
          <h2>把观察，变成过滤条件</h2>
          <p className="muted">手动选择区间，确认后添加到缩水工作台。</p>
        </div>
        <div className="h-rule-controls">
          <label>
            过滤指标
            <select
              value={indicator}
              onChange={(e) => {
                setIndicator(e.target.value as Indicator);
                setMin("0");
                setMax(e.target.value === "sum" ? "45" : "9");
                setPreview(false);
              }}
            >
              <option value="sum">和值</option>
              <option value="span">跨度</option>
              <option value="tail">和尾</option>
            </select>
          </label>
          <label>
            最小值
            <input
              type="number"
              min="0"
              max={indicator === "sum" ? 45 : 9}
              value={min}
              onChange={(e) => {
                setMin(e.target.value);
                setPreview(false);
              }}
            />
          </label>
          <span>—</span>
          <label>
            最大值
            <input
              type="number"
              min="0"
              max={indicator === "sum" ? 45 : 9}
              value={max}
              onChange={(e) => {
                setMax(e.target.value);
                setPreview(false);
              }}
            />
          </label>
          <button
            disabled={!ruleValid}
            className="button primary"
            onClick={() => setPreview(true)}
          >
            预览条件 ↗
          </button>
        </div>
        {!ruleValid && (
          <p className="h-error">
            请输入有效整数区间：0–{indicator === "sum" ? 45 : 9}
            ，最小值不能超过最大值。
          </p>
        )}
        {preview && (
          <div className="h-preview" role="status">
            <span>
              将添加：保留
              {indicator === "sum"
                ? "和值"
                : indicator === "span"
                  ? "跨度"
                  : "和尾"}{" "}
              {min}–{max} 的号码。
            </span>
            <button
              className="button primary"
              onClick={() => {
                onApply([
                  {
                    id: `history-${crypto.randomUUID()}`,
                    kind: indicator as Rule["kind"],
                    enabled: true,
                    mode: "include",
                    values: Array.from(
                      { length: Number(max) - Number(min) + 1 },
                      (_, i) => Number(min) + i,
                    ),
                  },
                ]);
                setPreview(false);
                setNotice("条件已添加到工作台");
              }}
            >
              确认添加到工作台
            </button>
            <button onClick={() => setPreview(false)}>取消</button>
          </div>
        )}
      </section>
      <p className="h-help">
        CSV 格式：issue,date,number；日期使用 YYYY-MM-DD，号码须保留五位（例如
        00123）。导入会替换当前数据，不会自动联网。期号用于标识，不推断连续性；非相邻日期可能包括休市，不直接认定缺失开奖。
      </p>
    </div>
  );
}
