import { useEffect, useMemo, useRef, useState } from "react";
import type { FilterInput } from "../domain/pick5";
import { defaultLab, validateLab, type LabConfig } from "../domain/lab/config";
import type { LabResult } from "../domain/lab/engine";
import type { PosteriorState } from "../domain/lab/posterior";
import { methods, pipelineStages } from "../domain/lab/registry";
const key = "pl5-incremental-posterior-v1";
function previous(): PosteriorState | undefined {
  try {
    const p = JSON.parse(localStorage.getItem(key) ?? "null");
    return p?.version === "incremental-v1" ? p : undefined;
  } catch {
    return undefined;
  }
}
export default function SequenceResearchLab({
  input,
  onChange,
}: {
  input: FilterInput;
  onChange: (i: FilterInput) => void;
}) {
  const c = input.lab ?? defaultLab,
    signature = useMemo(
      () => JSON.stringify({ ...input, lab: input.lab ?? defaultLab }),
      [input],
    ),
    worker = useRef<Worker | null>(null),
    serial = useRef(0);
  const [result, setResult] = useState<LabResult | null>(null),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState(""),
    [query, setQuery] = useState(""),
    [undo, setUndo] = useState<{ before: FilterInput; applied: string } | null>(
      null,
    );
  useEffect(() => {
    serial.current++;
    worker.current?.terminate();
    worker.current = null;
    setResult(null);
    setBusy(false);
    setNotice("");
  }, [signature]);
  useEffect(() => () => worker.current?.terminate(), []);
  const patch = (p: Partial<LabConfig>) =>
      onChange({ ...input, lab: { ...c, ...p } }),
    post = (p: Partial<LabConfig["posterior"]>) =>
      patch({ posterior: { ...c.posterior, ...p } }),
    cover = (p: Partial<LabConfig["cover"]>) =>
      patch({ cover: { ...c.cover, ...p } });
  const num = (
    label: string,
    v: number,
    min: number,
    max: number,
    fn: (v: number) => void,
    step = 1,
  ) => (
    <label>
      {label}
      <input
        type="number"
        aria-label={label}
        value={v}
        min={min}
        max={max}
        step={step}
        onChange={(e) => fn(Number(e.target.value))}
      />
    </label>
  );
  const run = (task: "posterior" | "cover") => {
    try {
      validateLab(c);
      if (!input.lab) onChange({ ...input, lab: { ...c } });
      worker.current?.terminate();
      const id = ++serial.current,
        w = new Worker(new URL("../workers/lab.worker.ts", import.meta.url), {
          type: "module",
        });
      worker.current = w;
      setResult(null);
      setBusy(true);
      setNotice("准备研究计算");
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
        if (e.data.error) {
          setNotice(e.data.error);
          return;
        }
        const r = e.data.result as LabResult;
        let storage = "";
        if (r.posterior)
          try {
            localStorage.setItem(key, JSON.stringify(r.posterior.state));
          } catch {
            storage = "；缓存写入失败，下次从可靠数据重建";
          }
        setResult(r);
        setNotice(
          (r.posterior ? "增量后验完成" : "有限覆盖求解结束") + storage,
        );
      };
      w.onerror = () => {
        if (id !== serial.current) return;
        finish();
        setNotice("研究线程失败，请重试");
      };
      w.postMessage({ id, input, config: c, task, previous: previous() });
    } catch (e) {
      setNotice((e as Error).message);
    }
  };
  const reportCopy = async () => {
    try {
      await navigator.clipboard.writeText(
        JSON.stringify(
          { version: "sequence-research-v1", input, result },
          null,
          2,
        ),
      );
      setNotice("研究报告已复制，含完整输入、域与求解界");
    } catch {
      setNotice("复制失败，页面结果仍保留");
    }
  };
  return (
    <section
      className="research-card sequence-lab"
      aria-labelledby="sequence-research-title"
    >
      <header>
        <div>
          <span className="research-kicker">INCREMENTAL & CERTIFIED</span>
          <h2 id="sequence-research-title">增量后验与有限覆盖</h2>
        </div>
      </header>
      <p className="research-context">
        来源：{input.historySource ?? "未标注"} · {input.history?.length ?? 0}
        期。LSTM/Transformer评分请使用上方“多阶段精选”。本卡片提供可信区间、有限域整数优化与方法能力目录；不是PyTorch/OR-Tools服务。
      </p>
      <label>
        研究历史截止期
        <input
          aria-label="研究历史截止期"
          value={c.referenceIssue ?? ""}
          placeholder="留空为最新"
          onChange={(e) =>
            patch({ referenceIssue: e.target.value || undefined })
          }
        />
      </label>
      <h3>增量Dirichlet后验</h3>
      <div className="research-fields">
        <label>
          后验计数模式
          <select
            aria-label="后验计数模式"
            value={c.posterior.mode}
            onChange={(e) => post({ mode: e.target.value as "all" | "window" })}
          >
            <option value="all">全部截止历史累计</option>
            <option value="window">固定长度滑动窗口</option>
          </select>
        </label>
        {num("后验窗口期数", c.posterior.window, 1, 10000, (v) =>
          post({ window: v }),
        )}
        {num(
          "每数字先验强度",
          c.posterior.alpha,
          0.1,
          100,
          (v) => post({ alpha: v }),
          0.1,
        )}
      </div>
      <p className="research-context">
        95%等尾Beta可信区间依赖Dirichlet/IID假设，不是下一期中奖置信区间。只在显式同步时更新；验证前缀和缓存计数后只追加新记录，重复同步不累加，修订时重建。
      </p>
      <button disabled={busy} onClick={() => run("posterior")}>
        同步增量后验与区间
      </button>
      <h3>有限整数覆盖求解</h3>
      <div className="research-fields">
        <label>
          有限覆盖目标
          <select
            aria-label="有限覆盖目标"
            value={c.cover.mode}
            onChange={(e) => cover({ mode: e.target.value as "min" | "max" })}
          >
            <option value="min">最小注数完整覆盖</option>
            <option value="max">预算下最大结构覆盖</option>
          </select>
        </label>
        {num("有限覆盖预算", c.cover.budget, 0, 32, (v) =>
          cover({ budget: v }),
        )}
        {num("汉明覆盖半径", c.cover.radius, 0, 5, (v) => cover({ radius: v }))}
        {num("有限候选数", c.shortlist, 1, 32, (v) => patch({ shortlist: v }))}
        {num("候选评分历史窗口", c.window, 40, 500, (v) =>
          patch({ window: v }),
        )}
        {num("求解节点上限", c.cover.nodes, 1, 1000000, (v) =>
          cover({ nodes: v }),
        )}
        {num("求解毫秒上限", c.cover.milliseconds, 1, 5000, (v) =>
          cover({ milliseconds: v }),
        )}
        <label>
          有限目标数字池
          <input
            aria-label="有限目标数字池"
            value={c.digits}
            maxLength={3}
            onChange={(e) => patch({ digits: e.target.value })}
          />
        </label>
      </div>
      <details>
        <summary>显式候选与目标（五位号码，空格分隔）</summary>
        <label>
          显式有限候选
          <textarea
            aria-label="显式有限候选"
            value={c.candidatesText}
            placeholder="留空取当前来源/规则域内冻结贝叶斯软分前N（N≤32）"
            onChange={(e) => patch({ candidatesText: e.target.value })}
          />
        </label>
        <label>
          显式覆盖目标
          <textarea
            aria-label="显式覆盖目标"
            value={c.targetsText}
            placeholder="留空为数字池五位笛卡尔积，最多243目标"
            onChange={(e) => patch({ targetsText: e.target.value })}
          />
        </label>
      </details>
      <p className="research-context">
        最多32候选、256目标，超限拒绝。最优性只针对报告完整短名单；不是十万全集最优。OPTIMAL已闭合证明界；FEASIBLE_LIMIT仅找到可行解；INFEASIBLE已证明无解；UNKNOWN_LIMIT未确认。半径3/4位等几何覆盖不是排列五奖级。
      </p>
      <button disabled={busy} onClick={() => run("cover")}>
        求解有限整数覆盖
      </button>
      {busy && (
        <button
          onClick={() => {
            serial.current++;
            worker.current?.terminate();
            worker.current = null;
            setBusy(false);
            setNotice("已取消研究计算，不发布部分结果");
          }}
        >
          取消研究计算
        </button>
      )}
      {notice && <p role="status">{notice}</p>}
      {result && (
        <>
          <p className="research-context">
            截止{result.cutoff} · 实际阶段：{result.stages.join(" → ")}
          </p>
          {result.posterior && (
            <div aria-label="增量后验结果">
              <p>
                更新状态 {result.posterior.action}（{result.posterior.reason}
                ）；新增{result.posterior.added}
                ，移出{result.posterior.removed}，实际使用
                {result.posterior.used}期（{result.posterior.range.join("—")}
                ）。缓存一致性需要检查原记录；“增量”指拟合计数只处理追加/移出，并非无需读取前缀。
              </p>
              <div style={{ overflowX: "auto" }}>
                <table
                  className="potential-table"
                  aria-label="增量后验可信区间"
                >
                  <thead>
                    <tr>
                      {[
                        "位置",
                        "数字",
                        "次数",
                        "后验均值",
                        "95%下界",
                        "95%上界",
                      ].map((x) => (
                        <th key={x}>{x}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.posterior.cells.map((x) => (
                      <tr key={`${x.position}-${x.digit}`}>
                        <td>{"万千百十个"[x.position]}位</td>
                        <td>{x.digit}</td>
                        <td>{x.count}</td>
                        <td>{(x.mean * 100).toFixed(3)}%</td>
                        <td>{(x.low * 100).toFixed(3)}%</td>
                        <td>{(x.high * 100).toFixed(3)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          {result.cover && (
            <div aria-label="有限覆盖结果">
              <div className="tolerance-box">
                <strong>{result.cover.status}</strong>
                <p>
                  {result.cover.solver} · 停止：{result.cover.stop}
                  。最优性范围仅为{result.cover.candidates.length}候选/
                  {result.cover.targets.length}目标。
                </p>
              </div>
              <p>
                目标值{result.cover.objective ?? "无可行解"}；全局界
                {result.cover.bound ?? "不适用"}；绝对gap{" "}
                {result.cover.gap ?? "不适用"}；搜索{result.cover.nodes}
                节点，耗时{result.cover.elapsed.toFixed(1)}ms。实际
                {result.cover.numbers.length}注，结构覆盖{result.cover.covered}/
                {result.cover.targets.length}；理论精确覆盖
                {(result.cover.exactProbability * 100).toFixed(3)}%。
              </p>
              <p className="research-context">
                {result.candidateSelection?.warning}。来源
                {result.candidateSelection?.source}组；
                {result.candidateSelection?.explicit
                  ? "使用显式候选"
                  : "使用冻结贝叶斯分前N"}
                ，没有静默随机抽目标。
              </p>
              <p>
                求解组合：{result.cover.numbers.join(" ") || "空集"}
                ；未覆盖目标示例：
                {result.cover.uncovered.slice(0, 10).join(" ") || "无"}。
              </p>
              <details>
                <summary>完整求解模型与域清单</summary>
                <pre className="innovation-json">
                  {JSON.stringify(result.cover, null, 2)}
                </pre>
              </details>
              <button
                disabled={
                  !result.cover.numbers.length || !result.cover.certified
                }
                onClick={() => {
                  const next = {
                    ...input,
                    candidates: result.cover!.numbers,
                    rules: input.rules.map((r) => ({ ...r, enabled: false })),
                    combination: { mode: "strict" as const, minimum: 0 },
                  };
                  setUndo({
                    before: input,
                    applied: JSON.stringify({
                      ...next,
                      lab: next.lab ?? defaultLab,
                    }),
                  });
                  onChange(next);
                }}
              >
                载入有限覆盖组合并停用原条件
              </button>
            </div>
          )}
          <button onClick={reportCopy}>复制增量与覆盖报告</button>
        </>
      )}
      {undo && (
        <button
          disabled={signature !== undo.applied}
          onClick={() => {
            onChange(undo.before);
            setUndo(null);
          }}
        >
          撤销有限覆盖载入
        </button>
      )}
      <details>
        <summary>方法能力与执行管道</summary>
        <p className="research-context">
          通用管道：{pipelineStages.join(" → ")}
          。GA/MC属于选择器，不直接作为独立概率模型投票；模型分数、可信区间、结构覆盖与中奖概率分开。
        </p>
        <label>
          查询方法能力
          <input
            aria-label="查询方法能力"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <div style={{ overflowX: "auto" }}>
          <table className="potential-table" aria-label="方法能力目录">
            <thead>
              <tr>
                {[
                  "方法",
                  "类别",
                  "历史最小量",
                  "输出量纲",
                  "依赖",
                  "回放",
                  "冻结保形支持",
                  "状态",
                ].map((x) => (
                  <th key={x}>{x}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {methods
                .filter((m) =>
                  (m.id + m.label + m.type)
                    .toLowerCase()
                    .includes(query.toLowerCase()),
                )
                .map((m) => (
                  <tr key={m.id}>
                    <td>
                      {m.id} · {m.label}
                    </td>
                    <td>{m.type}</td>
                    <td>{m.history}</td>
                    <td>{m.unit}</td>
                    <td>{m.dependencies}</td>
                    <td>{m.replay ? "有限额" : "无"}</td>
                    <td>{m.conformal ? "仅既定协议" : "不继承"}</td>
                    <td>
                      {m.status} · {m.version}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
