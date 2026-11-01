import { useMemo, useState } from "react";
import { buildStats, researchHistory } from "../domain/research/statistics";
import type { ResearchConfig } from "../domain/research/types";
import type { HistoryRecord } from "../domain/pick5";
export default function MarkovPreview({
  config,
  history,
}: {
  config: ResearchConfig;
  history?: HistoryRecord[];
}) {
  const [position, setPosition] = useState(0),
    [mode, setMode] = useState("probability");
  const data = useMemo(() => {
    try {
      if (config.window < 2) throw new Error("转移矩阵至少需要2期");
      return { stats: buildStats(researchHistory(config, history)), error: "" };
    } catch (e) {
      return { stats: null, error: (e as Error).message };
    }
  }, [config.window, config.referenceIssue, history]);
  return (
    <div className="potential-editor">
      <div className="research-fields">
        <label>
          转移观察位置
          <select
            aria-label="转移观察位置"
            value={position}
            onChange={(e) => setPosition(Number(e.target.value))}
          >
            {["万位", "千位", "百位", "十位", "个位"].map((s, i) => (
              <option value={i} key={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label>
          转移矩阵显示
          <select
            aria-label="转移矩阵显示"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
          >
            <option value="probability">加一平滑后验概率</option>
            <option value="counts">原始转移次数</option>
          </select>
        </label>
      </div>
      {data.error ? (
        <p className="notice">{data.error}</p>
      ) : (
        data.stats && (
          <>
            <p className="research-context">
              行是前一数字，列是后一数字；当前来源数字{" "}
              {data.stats.last[position]}。{data.stats.n - 1}
              个观测相邻转移；日期缺口不冒充核验过的连续开奖。无出边行的加一后验为均匀10%。
            </p>
            <div style={{ overflowX: "auto" }}>
              <table className="potential-table" aria-label="马尔可夫转移矩阵">
                <thead>
                  <tr>
                    <th>前/后</th>
                    {Array.from({ length: 10 }, (_, d) => (
                      <th key={d}>{d}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.stats.transitions[position].map((row, i) => {
                    const total = row.reduce((a, b) => a + b, 0);
                    return (
                      <tr
                        key={i}
                        style={{
                          background:
                            i === data.stats!.last[position]
                              ? "#fff0dc"
                              : undefined,
                        }}
                      >
                        <td>{i}</td>
                        {row.map((n, j) => (
                          <td key={j}>
                            {mode === "counts"
                              ? n
                              : `${(((n + 1) / (total + 10)) * 100).toFixed(1)}%`}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )
      )}
    </div>
  );
}
