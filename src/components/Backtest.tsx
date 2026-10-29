import { useState } from "react";
import { History, Play } from "lucide-react";
import { backtest, type ReplayRow } from "../domain/backtest";
import { type FilterInput } from "../domain/pick5";
import { download } from "../lib/plans";
const statuses = {
  retained: "保留",
  removed: "过滤移除",
  outside: "不在原始候选",
  insufficient: "历史不足",
  error: "规则错误",
};
export default function Backtest({ input }: { input: FilterInput }) {
  const [count, setCount] = useState(30),
    [result, setResult] = useState<ReplayRow[]>([]),
    [stamp, setStamp] = useState(""),
    [error, setError] = useState("");
  const serialized = JSON.stringify(input),
    stale = Boolean(result.length) && stamp !== serialized;
  const run = () => {
    try {
      setResult(backtest(input, count));
      setStamp(serialized);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const valid = result.filter((r) =>
    ["retained", "removed", "outside"].includes(r.status),
  );
  return (
    <section className="card replay-card">
      <div className="section-head">
        <h2>
          <History size={17} />
          历史回放核验
        </h2>
        <span className="muted small">只用目标期以前的数据</span>
      </div>
      <div className="replay-body">
        <p className="muted small">
          将当前条件逐期应用于已知开奖号码。每期历史参考重新截止到上一期，原始候选范围也参与核对。这是样本内规则核验，不是未来预测。
        </p>
        <div className="head-actions">
          <select
            aria-label="历史回放期数"
            value={count}
            onChange={(e) => {
              setCount(Number(e.target.value));
              setResult([]);
            }}
          >
            {[10, 30, 50, 100, 200].map((n) => (
              <option value={n} key={n}>
                最近{n}期
              </option>
            ))}
          </select>
          <button className="button secondary" onClick={run}>
            <Play size={14} />
            运行历史回放
          </button>
          {result.length > 0 && (
            <button
              className="button secondary"
              disabled={stale}
              onClick={() =>
                download(
                  "pl5-回放.csv",
                  "issue,date,number,reference,status\n" +
                    result
                      .map((r) =>
                        [
                          r.issue,
                          r.date,
                          r.number,
                          r.referenceIssue,
                          r.status,
                        ].join(","),
                      )
                      .join("\n"),
                  "text/csv;charset=utf-8",
                )
              }
            >
              导出回放CSV
            </button>
          )}
        </div>
        {error && (
          <div className="error-box" role="alert">
            {error}
          </div>
        )}
        {stale && <p className="validation">条件或历史已改变，请重新回放。</p>}
        {result.length > 0 && (
          <>
            <div className="replay-summary">
              <span>
                保留{" "}
                <strong>
                  {result.filter((r) => r.status === "retained").length}
                </strong>{" "}
                / {valid.length} 个可评估样本
              </span>
              <span>不足或错误 {result.length - valid.length} 期</span>
            </div>
            <div className="replay-scroll">
              <table>
                <thead>
                  <tr>
                    <th>目标期</th>
                    <th>开奖号码</th>
                    <th>历史截止期</th>
                    <th>判定</th>
                  </tr>
                </thead>
                <tbody>
                  {result.map((r) => (
                    <tr key={r.issue}>
                      <td>{r.issue}</td>
                      <td>{r.number}</td>
                      <td>{r.referenceIssue}</td>
                      <td title={r.reason}>
                        {statuses[r.status]}
                        {r.reason && <small>{r.reason}</small>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
