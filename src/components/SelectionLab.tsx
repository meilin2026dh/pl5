import SequenceDiagnostics from "./SequenceDiagnostics";
import { defaultSequence } from "../domain/selection/sequence-config";
import { useEffect, useRef, useState } from "react";
import type { FilterInput } from "../domain/pick5";
import {
  defaultSelection,
  validateSelection,
  type SelectionConfig,
} from "../domain/selection/config";
import type { ReplayRow } from "../domain/backtest";
import type { SelectionResult } from "../domain/selection/engine";
export default function SelectionLab({
  input,
  onChange,
}: {
  input: FilterInput;
  onChange: (i: FilterInput) => void;
}) {
  const c = input.selection ?? defaultSelection;
  const signature = JSON.stringify({ ...input, selection: c });
  const [result, setResult] = useState<SelectionResult | null>(null),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  const [replay, setReplay] = useState<
    (ReplayRow & { selected: number })[] | null
  >(null);
  const worker = useRef<Worker | null>(null),
    serial = useRef(0);
  useEffect(() => {
    serial.current++;
    worker.current?.terminate();
    worker.current = null;
    setResult(null);
    setReplay(null);
    setBusy(false);
    setNotice("");
  }, [signature]);
  useEffect(() => () => worker.current?.terminate(), []);
  const patch = (p: Partial<SelectionConfig>) =>
    onChange({ ...input, selection: { ...c, ...p } });
  const numeric = (
    label: string,
    key: {
      [K in keyof SelectionConfig]: SelectionConfig[K] extends number
        ? K
        : never;
    }[keyof SelectionConfig] &
      string,
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
        onChange={(e) => patch({ [key]: Number(e.target.value) })}
      />
    </label>
  );
  const cancel = () => {
    serial.current++;
    worker.current?.terminate();
    worker.current = null;
    setBusy(false);
    setNotice("已取消精选；不保留部分结果。");
  };
  const run = (task: "select" | "replay" = "select") => {
    try {
      validateSelection(c);
      if (!input.selection) onChange({ ...input, selection: { ...c } });
      const id = ++serial.current;
      worker.current?.terminate();
      const w = new Worker(
        new URL("../workers/selection.worker.ts", import.meta.url),
        { type: "module" },
      );
      worker.current = w;
      setResult(null);
      setReplay(null);
      setBusy(true);
      setNotice("准备精选计算");
      const finish = () => {
        w.terminate();
        if (worker.current === w) worker.current = null;
        setBusy(false);
      };
      w.onmessage = (e) => {
        if (e.data.id !== serial.current) return;
        if (e.data.stage) {
          setNotice(e.data.stage);
          return;
        }
        finish();
        if (e.data.error) setNotice(e.data.error);
        else if (e.data.replay) {
          setReplay(e.data.replay);
          setNotice(
            "精选组合包回放完成：每个目标期均使用此前历史重新拟合与构包。",
          );
        } else {
          setResult(e.data.result);
          setNotice(
            "精选完成；多样性按分数顺序贪心构造，不承诺全局最优组合包。",
          );
        }
      };
      w.onerror = () => {
        if (id !== serial.current) return;
        finish();
        setNotice("精选线程失败，请检查条件后重试。");
      };
      w.postMessage({ id, input, config: c, task });
    } catch (e) {
      setNotice((e as Error).message);
    }
  };
  return (
    <section className="research-card" aria-labelledby="selection-title">
      <header>
        <div>
          <span className="research-kicker">SELECTION LAB</span>
          <h2 id="selection-title">多阶段精选</h2>
        </div>
      </header>
      <p className="research-context">
        历史来源：{input.historySource || "未载入"} ·{" "}
        {input.history?.length ?? 0}期。现有条件 → AC/间距 → 历史硬约束 →
        评分搜索 → 输出多样性。全部配置随方案保存。
      </p>
      <div className="research-fields">
        <label>
          精选搜索器
          <select
            aria-label="精选搜索器"
            value={c.method}
            onChange={(e) =>
              patch({ method: e.target.value as SelectionConfig["method"] })
            }
          >
            <option value="exact">全遍历排名（对照基准）</option>
            <option value="mcga">加权蒙特卡洛 + 遗传精化</option>
            <option value="anneal">模拟退火</option>
          </select>
        </label>
        <label>
          精选评分器
          <select
            aria-label="精选评分器"
            value={c.scorer}
            onChange={(e) =>
              patch({ scorer: e.target.value as SelectionConfig["scorer"] })
            }
          >
            <option value="bayes">贝叶斯逐位后验</option>
            <option value="neural">35维浅层网络结构分</option>
            <option value="resnet">微型残差Conv1D时序形态分</option>
            <option value="lstm">微型LSTM（全参数训练）</option>
            <option value="transformer">
              微型因果Transformer（全参数训练）
            </option>
          </select>
        </label>
        {numeric("精选历史窗口", "window", 40, 500)}
        {numeric("精选目标注数", "budget", 1, 200)}
        {numeric("精选随机种子", "seed", 0, 4294967295)}
        <label>
          精选参考期
          <input
            aria-label="精选参考期"
            value={c.referenceIssue ?? ""}
            placeholder="留空使用快照最新一期"
            onChange={(e) =>
              patch({ referenceIssue: e.target.value.trim() || undefined })
            }
          />
        </label>
      </div>
      {["lstm", "transformer"].includes(c.scorer) && (
        <div className="research-fields">
          <label>
            时序上下文
            <select
              aria-label="时序上下文"
              value={c.sequence?.context ?? 8}
              onChange={(e) =>
                patch({
                  sequence: {
                    ...defaultSequence,
                    ...c.sequence,
                    context: Number(e.target.value) as 4 | 8 | 12,
                  },
                })
              }
            >
              {[4, 8, 12].map((n) => (
                <option key={n} value={n}>
                  {n}期
                </option>
              ))}
            </select>
          </label>
          <label>
            时序最大训练轮数
            <input
              aria-label="时序最大训练轮数"
              type="number"
              min={1}
              max={20}
              value={c.sequence?.epochs ?? 20}
              onChange={(e) =>
                patch({
                  sequence: {
                    ...defaultSequence,
                    ...c.sequence,
                    epochs: Number(e.target.value),
                  },
                })
              }
            />
          </label>
          <p className="research-context">
            窗口至少80期。独立训练/验证/诊断；回放限窗口200、10轮、上下文8。诊断不选择权重；注意力不是因果解释。
          </p>
        </div>
      )}
      <details open>
        <summary>结构与历史硬约束</summary>
        <div className="research-fields">
          {numeric("精选AC下限", "acMin", -4, 5)}
          {numeric("精选AC上限", "acMax", -4, 5)}
          {numeric("精选大间距下限", "gapThreshold", 1, 9)}
          {numeric("精选大间距最少个数", "minLarge", 0, 4)}
          {numeric("精选大间距最多个数", "maxLarge", 0, 4)}
          {numeric("精选近期比较期数", "recent", 0, 500)}
          {numeric("精选历史同位重号上限", "historySame", 0, 5)}
          {numeric("精选历史Jaccard上限", "jaccard", 0, 1, 0.05)}
          {numeric("精选输出同位重号上限", "maxSame", 0, 4)}
          <label>
            精选输出Jaccard上限
            <input
              aria-label="精选输出Jaccard上限"
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={c.outputJaccard ?? 1}
              onChange={(e) => patch({ outputJaccard: Number(e.target.value) })}
            />
          </label>
        </div>
        <p className="research-context">
          AC=不同非零绝对差种数−4，范围−4至5；排序含重复位，间距大于等于下限为大。近期0期关闭历史约束。Jaccard按不同数字集合比较，等于上限可保留；输出同时限制同位置重合数和数字集合Jaccard相似度。
        </p>
      </details>
      {c.method !== "exact" && (
        <details open>
          <summary>随机搜索参数</summary>
          <div className="research-fields">
            {c.method === "mcga" &&
              numeric("蒙特卡洛采样次数", "samples", 100, 1000000)}
            {numeric("搜索种群规模", "population", 10, 500)}
            {numeric("搜索迭代代数", "generations", 1, 500)}
          </div>
        </details>
      )}
      {c.scorer === "resnet" && (
        <p className="research-context">
          五条位置链、8期独热输入、4通道、两层因果卷积及残差跳连，共990参数；15轮训练，时间留出比较一步马尔可夫与均匀基线。训练只在所选截止期内进行；形态分不是中奖保证。
        </p>
      )}
      {c.scorer === "neural" && (
        <>
          <label className="research-context">
            <input
              aria-label="启用时间留出网格选参"
              type="checkbox"
              checked={c.autoTune}
              onChange={(e) => patch({ autoTune: e.target.checked })}
            />{" "}
            时间留出网格选参（4组浅层网络参数）
          </label>
          <p className="research-context">
            使用逐位多窗频率、遗漏标准化/未知标记及两位共现共35维特征，历史目标特征只使用其此前记录。对比随机负样本的结构分，不是中奖概率；此处没有使用XGBoost或Optuna。
          </p>
        </>
      )}
      <div className="research-actions">
        <button onClick={() => run("select")} disabled={busy}>
          运行多阶段精选
        </button>
        <button onClick={() => run("replay")} disabled={busy}>
          回放最近10期精选
        </button>
        {busy && <button onClick={cancel}>取消精选</button>}
      </div>
      <p className="research-context">
        本面板回放重选完整组合包；页面下方的历史回放仅核验原过滤条件。
      </p>
      {replay && (
        <div aria-label="精选回放结果">
          <p className="research-context">
            组合包覆盖 {replay.filter((r) => r.status === "retained").length}/
            {
              replay.filter((r) => ["retained", "removed"].includes(r.status))
                .length
            }{" "}
            个可评估目标；不足/错误{" "}
            {
              replay.filter((r) => ["insufficient", "error"].includes(r.status))
                .length
            }{" "}
            期。
          </p>
          <div style={{ overflowX: "auto" }}>
            <table className="potential-table">
              <thead>
                <tr>
                  <th>目标期</th>
                  <th>开奖号码</th>
                  <th>训练截止期</th>
                  <th>精选组数</th>
                  <th>判定</th>
                </tr>
              </thead>
              <tbody>
                {replay.map((r) => (
                  <tr key={r.issue}>
                    <td>{r.issue}</td>
                    <td>{r.number}</td>
                    <td>{r.referenceIssue}</td>
                    <td>{r.selected}</td>
                    <td title={r.reason}>
                      {
                        {
                          retained: "包含开奖号",
                          removed: "未包含",
                          outside: "大底外",
                          insufficient: "历史不足",
                          error: "计算错误",
                        }[r.status]
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {notice && (
        <p role="status" className="research-context">
          {notice}
        </p>
      )}
      {result && (
        <div aria-label="精选结果">
          <SequenceDiagnostics value={result.diagnostics.scorer} />
          {["lstm", "transformer"].includes(c.scorer) && (
            <button
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(
                    JSON.stringify(
                      { version: "sequence-model-v1", input, result },
                      null,
                      2,
                    ),
                  );
                  setNotice("完整时序训练报告已复制，含输入快照与诊断");
                } catch {
                  setNotice("报告复制失败，页面诊断仍可查看");
                }
              }}
            >
              复制时序训练报告
            </button>
          )}
          <p className="research-context">
            输入{result.diagnostics.inputCount}组 → 结构
            {result.diagnostics.coarseCount}组 → 可行
            {result.diagnostics.feasibleCount}组 → 搜索覆盖
            {result.diagnostics.searchedCount}组 → 输出{result.numbers.length}/
            {c.budget}组。
          </p>
          {result.diagnostics.exactSeedFallback && (
            <p className="notice">
              加权采样未命中可行种子，已明确使用全遍历最优单号初始化遗传种群；不将此成绩归为随机采样能力。
            </p>
          )}
          {result.diagnostics.shortfall && (
            <p className="notice">
              未凑满目标注数：可行域、搜索覆盖或贪心多样性限制所致；没有放宽约束补数。
            </p>
          )}
          <p className="research-context">
            参考截止{result.diagnostics.lastIssue} · 最优分差{" "}
            {result.diagnostics.bestGap === null
              ? "无可行候选"
              : result.diagnostics.bestGap.toFixed(8)}
            （对比同一可行域的全遍历单号最高分）。随机搜索仍计算全遍历对照，不宣称比它更快或更优。
          </p>
          <details>
            <summary>搜索、模型与选参计算说明</summary>
            <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
              {JSON.stringify(result.diagnostics, null, 2)}
            </pre>
          </details>
          <div className="research-actions">
            <button
              disabled={!result.numbers.length}
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(
                    result.numbers.join("\n"),
                  );
                  setNotice("已复制精选号码");
                } catch {
                  setNotice("复制未完成，可从下方选择号码复制。");
                }
              }}
            >
              复制精选号码
            </button>
            <button
              disabled={!result.numbers.length}
              onClick={() =>
                onChange({ ...input, candidates: [...result.numbers] })
              }
            >
              将精选结果载入大底
            </button>
          </div>
          <p
            aria-label="精选号码"
            style={{
              fontFamily: "monospace",
              lineHeight: 2,
              overflowWrap: "anywhere",
            }}
          >
            {result.numbers.join("　") || "暂无符合条件的号码"}
          </p>
        </div>
      )}
    </section>
  );
}
