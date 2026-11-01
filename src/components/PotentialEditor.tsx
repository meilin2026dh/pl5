import { useMemo, useState } from "react";
import type { HistoryRecord } from "../domain/pick5";
import type { ResearchConfig } from "../domain/research/types";
import { researchHistory } from "../domain/research/statistics";
import {
  defaultPotential,
  fitPotential,
  type PotentialConfig,
} from "../domain/research/potential";
export default function PotentialEditor({
  config,
  history,
  onChange,
}: {
  config: ResearchConfig;
  history?: HistoryRecord[];
  onChange: (p: PotentialConfig) => void;
}) {
  const c = config.potential ?? defaultPotential;
  const [position, setPosition] = useState(0),
    [sample, setSample] = useState("12345");
  const preview = useMemo(() => {
    try {
      return {
        model: fitPotential(researchHistory(config, history), c),
        error: "",
      };
    } catch (e) {
      return { model: null, error: (e as Error).message };
    }
  }, [config.window, config.referenceIssue, c, history]);
  const numeric = (
    label: string,
    key: "short" | "blocks" | "sensitivity" | "cycleWeight" | "clusterWeight",
    min: number,
    max: number,
    step = 1,
  ) => (
    <label key={key}>
      {label}
      <input
        aria-label={label}
        type="number"
        min={min}
        max={max}
        step={step}
        value={c[key]}
        onChange={(e) => onChange({ ...c, [key]: Number(e.target.value) })}
      />
    </label>
  );
  return (
    <div className="potential-editor">
      <p className="research-context">
        短窗与此前基线比较；各分窗只使用自身之前的记录。热/冷由动态波动带划分，中性不计交替。排名阈值在开始缩水后按当前历史重新计算。
      </p>
      <div className="research-fields">
        {numeric("势能短窗", "short", 2, 200)}
        {numeric("势能分窗数", "blocks", 3, 12)}
        {numeric("势能灵敏带", "sensitivity", 0, 5, 0.1)}
        {numeric("势能周期权重", "cycleWeight", 0, 5, 0.1)}
        {numeric("势能聚集权重", "clusterWeight", 0, 5, 0.1)}
        <label>
          势能侧重
          <select
            aria-label="势能侧重"
            value={c.mode}
            onChange={(e) =>
              onChange({
                ...c,
                mode: e.target.value as PotentialConfig["mode"],
              })
            }
          >
            <option value="warming">升温方向</option>
            <option value="cooling">降温方向</option>
            <option value="transition">冷热转换强度</option>
          </select>
        </label>
      </div>
      <p className="small muted">
        窗口至少 {c.short * (c.blocks + 1)}{" "}
        期（分窗前保留至少一个短窗作基线）。周期是历史分窗的交替强度；聚集是候选相邻位置的同热/同冷比例。两项权重设0可关闭。
      </p>
      {preview.error ? (
        <p className="notice">{preview.error}</p>
      ) : (
        preview.model && (
          <>
            <div className="research-fields">
              <label>
                势能观察位置
                <select
                  aria-label="势能观察位置"
                  value={position}
                  onChange={(e) => setPosition(Number(e.target.value))}
                >
                  {["万位", "千位", "百位", "十位", "个位"].map((n, i) => (
                    <option value={i} key={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                势能预览号码
                <input
                  aria-label="势能预览号码"
                  value={sample}
                  maxLength={5}
                  inputMode="numeric"
                  onChange={(e) => setSample(e.target.value)}
                />
              </label>
            </div>
            <p className="research-context">
              候选原始势能分：
              {/^\d{5}$/.test(sample)
                ? preview.model.score(sample).toFixed(6)
                : "请输入五位数字"}
              。完整过滤结论还需应用保留比例、并列策略及其他条件。
            </p>
            <p className="small">
              分窗截止期（从早到晚）：{preview.model.blockIssues.join(" → ")}
              。冷热序列按此顺序。
            </p>
            <div style={{ overflowX: "auto" }}>
              <table aria-label="冷热势能观察" className="potential-table">
                <thead>
                  <tr>
                    {[
                      "数字",
                      "冷热序列",
                      "临界转换",
                      "交替比例",
                      "数字势能",
                      "势能变化",
                      "短窗频率",
                      "此前基线",
                      "动态带宽",
                      "标准偏离",
                    ].map((t) => (
                      <th key={t}>{t}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.model.signals[position].map((s) => (
                    <tr key={s.digit}>
                      <td>{s.digit}</td>
                      <td>{s.states.join("→")}</td>
                      <td>{s.crossing}</td>
                      <td>{(s.alternation * 100).toFixed(1)}%</td>
                      <td>{s.score.toFixed(3)}</td>
                      <td>{s.momentum.toFixed(3)}</td>
                      <td>{(s.recentRate * 100).toFixed(1)}%</td>
                      <td>{(s.baselineRate * 100).toFixed(1)}%</td>
                      <td>±{(s.band * 100).toFixed(1)}%</td>
                      <td>{s.z.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )
      )}
    </div>
  );
}
