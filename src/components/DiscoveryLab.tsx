import { useEffect, useMemo, useRef, useState } from "react";
import type { FilterInput } from "../domain/pick5";
import {
  defaultDiscovery,
  validateDiscovery,
  type DiscoveryConfig,
} from "../domain/discovery/config";
import type { DiscoveryResult } from "../domain/discovery/engine";
export default function DiscoveryLab({
  input,
  onChange,
}: {
  input: FilterInput;
  onChange: (i: FilterInput) => void;
}) {
  const c = input.discovery ?? defaultDiscovery,
    signature = useMemo(
      () =>
        JSON.stringify({
          ...input,
          discovery: input.discovery ?? defaultDiscovery,
        }),
      [input],
    ),
    serial = useRef(0),
    worker = useRef<Worker | null>(null);
  const [result, setResult] = useState<DiscoveryResult | null>(null),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState(""),
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
  const patch = (p: Partial<DiscoveryConfig>) =>
    onChange({ ...input, discovery: { ...c, ...p } });
  const cancel = () => {
    serial.current++;
    worker.current?.terminate();
    worker.current = null;
    setBusy(false);
    setResult(null);
    setNotice("已取消集合实验，不保留部分结果");
  };
  const run = (rolling = false) => {
    try {
      validateDiscovery(c);
      if (!input.discovery) onChange({ ...input, discovery: { ...c } });
      worker.current?.terminate();
      const id = ++serial.current,
        w = new Worker(
          new URL("../workers/discovery.worker.ts", import.meta.url),
          { type: "module" },
        );
      worker.current = w;
      setBusy(true);
      setResult(null);
      setNotice("准备评分与集合实验");
      w.onmessage = (e) => {
        if (e.data.id !== serial.current) return;
        if (e.data.stage) {
          setNotice(e.data.stage);
          return;
        }
        w.terminate();
        worker.current = null;
        setBusy(false);
        setResult(e.data.result ?? null);
        setNotice(e.data.error ?? "实验完成，最终测试未参与调参");
      };
      w.onerror = () => {
        if (id !== serial.current) return;
        w.terminate();
        worker.current = null;
        setBusy(false);
        setNotice("实验线程失败，请重试");
      };
      w.postMessage({ id, input, config: c, rolling });
    } catch (e) {
      setNotice((e as Error).message);
    }
  };
  const num = (
    label: string,
    key: keyof DiscoveryConfig,
    min: number,
    max: number,
    step = 1,
  ) => (
    <label>
      {label}
      <input
        aria-label={label}
        type="number"
        value={c[key] ?? (key === "delta" ? 0.02 : 0.05)}
        min={min}
        max={max}
        step={step}
        onChange={(e) => patch({ [key]: Number(e.target.value) })}
      />
    </label>
  );
  return (
    <section
      className="research-card sequence-lab"
      aria-labelledby="discovery-title"
    >
      <header>
        <div>
          <span className="research-kicker">SCORE · CALIBRATE · DIVERSIFY</span>
          <h2 id="discovery-title">评分与集合实验室</h2>
        </div>
      </header>
      <p className="research-context">
        来源：{input.historySource ?? "未标注"} · {input.history?.length ?? 0}
        期。对抗MLP、张量列车、联合注意力、GNN、遮位对比与后验三态软决策，共用普通校准和DPP。不是GAN、加权保形或精确DPP抽样。AUC仅诊断，未实现显著性门控；重复查看过的时间外区间不再是未见测试。先在历史走势载入真实历史。
      </p>
      <div className="research-grid">
        <label>
          实验评分模型
          <select
            aria-label="实验评分模型"
            value={c.model}
            onChange={(e) =>
              patch({ model: e.target.value as DiscoveryConfig["model"] })
            }
          >
            <option value="tensor">非负张量列车</option>
            <option value="ratio">密度比对抗MLP</option>
            <option value="joint">跨位置联合Transformer</option>
            <option value="gnn">位置数字GNN对照</option>
            <option value="contrast">遮位对比表示（人工任务）</option>
            <option value="uncertainty">后验三态软决策</option>
          </select>
        </label>
        <label>
          张量秩
          <select
            aria-label="张量秩"
            value={c.rank}
            onChange={(e) =>
              patch({ rank: Number(e.target.value) as DiscoveryConfig["rank"] })
            }
          >
            {[1, 2, 4].map((r) => (
              <option key={r}>{r}</option>
            ))}
          </select>
        </label>
        {num("实验训练期数", "train", 80, 500)}
        {num("实验验证期数", "validation", 20, 100)}
        {num("实验校准期数", "calibration", 20, 200)}
        {num("实验最终检验期数", "test", 10, 100)}
        {num("校准目标覆盖率", "coverage", 0.01, 0.99, 0.01)}
        {num("DPP候选池", "pool", 16, 256)}
        {num("实验预算注数", "budget", 1, 64)}
        {num("DPP核宽度", "sigma", 0.2, 5, 0.1)}
        {num("集合实验种子", "seed", 0, 4294967295)}
        {num("实际偏差δ", "delta", 0, 0.09, 0.005)}
        {num("后验联合风险上限", "posteriorRisk", 0.001, 0.2, 0.005)}
        <label>
          集合历史截止期
          <input
            aria-label="集合历史截止期"
            value={c.referenceIssue}
            onChange={(e) => patch({ referenceIssue: e.target.value })}
          />
        </label>
      </div>
      <p className="research-context">
        新增神经模型训练上限200期；联合模型学习整注前缀，不额外输入跨期状态。至少需要
        {c.train + c.validation + c.calibration + c.test}
        期。冻结训练→验证选均匀混合→校准→最终检验；三折回放另需{2 * c.test}
        期，每折重新拟合。α对应真实样本遗漏风险，不是候选淘汰比例。DPP后不继承校准覆盖保证；公平独立下n注精确覆盖=n/100000。
      </p>
      <div className="research-actions">
        <button disabled={busy} onClick={() => run()}>
          运行评分与集合实验
        </button>
        <button disabled={busy} onClick={() => run(true)}>
          三折滚动集合回放
        </button>
        {busy && <button onClick={cancel}>取消集合实验</button>}
      </div>
      <p role="status">{notice}</p>
      {result && (
        <div aria-label="评分与集合结果">
          <h3>冻结模型的时间外结果</h3>
          <p>
            共同MLP对照 AUC {result.validation.auc.toFixed(4)} · BCE{" "}
            {result.validation.bce.toFixed(5)}（均匀分类基线{" "}
            {result.validation.uniformBce.toFixed(5)}）；验证选混合λ=
            {result.validation.weight}。
          </p>
          <p>
            所选模型 {c.model}；新增模型参数
            {result.extra?.parameterCount ?? "—"}；TT对照参数
            {result.training.tensorParameters}；校准集合
            {result.calibration.size}注；DPP {result.numbers.length}注 / 请求
            {c.budget}注，停止原因 {result.dpp.stop}
            。完整校准集合与预算集合分开统计。
          </p>
          <p>
            最终{result.evaluation.periods}期：完整校准集合覆盖
            {result.evaluation.calibratedHits}；预算集合覆盖
            {result.evaluation.budgetHits}，随机期望
            {result.evaluation.expectedHits.toFixed(4)}，提升倍数
            {result.evaluation.lift.toFixed(3)}。淘汰率
            {(100 * result.evaluation.elimination).toFixed(3)}%，log loss{" "}
            {result.evaluation.loss.toFixed(5)}，均匀
            {result.evaluation.uniformLoss.toFixed(5)}。少量期数不证明优势。
          </p>
          <table aria-label="集合实验时间切分">
            <thead>
              <tr>
                <th>阶段</th>
                <th>起期</th>
                <th>止期</th>
                <th>样本</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(result.ranges).map(([k, r]) => (
                <tr key={k}>
                  <td>{k}</td>
                  <td>{r.start}</td>
                  <td>{r.end}</td>
                  <td>{r.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p>{result.note}</p>
          <p>预算集合：{result.numbers.join(" ")}</p>
          {result.walkForward && (
            <p>
              三折重新拟合：
              {result.walkForward
                .map(
                  (r) =>
                    `${r.start}–${r.end}：${r.hits}/${r.periods}（随机期望${r.expected.toFixed(4)}）`,
                )
                .join("；")}
            </p>
          )}
          <details>
            <summary>验证混合与训练诊断</summary>
            <pre>
              {JSON.stringify(
                {
                  training: result.training,
                  extra: result.extra,
                  validation: result.validation,
                  dpp: result.dpp,
                },
                null,
                2,
              )}
            </pre>
          </details>
          <details>
            <summary>位置数字不确定性（50项）</summary>
            <p>
              {result.uncertainty.policy} 实际偏差δ={result.uncertainty.delta}
              ，联合后验风险上限={result.uncertainty.risk}
              。新增神经模型训练最多200期；对比视图是人工任务，不是已标注异常。
            </p>
            <table aria-label="后验三态决策">
              <thead>
                <tr>
                  <th>位置</th>
                  <th>数字</th>
                  <th>均值</th>
                  <th>保守区间</th>
                  <th>判断</th>
                </tr>
              </thead>
              <tbody>
                {result.uncertainty.cells.map((x) => (
                  <tr key={`${x.position}-${x.digit}`}>
                    <td>{"万千百十个"[x.position]}</td>
                    <td>{x.digit}</td>
                    <td>{x.mean.toFixed(4)}</td>
                    <td>
                      [{x.low.toFixed(4)}, {x.high.toFixed(4)}]
                    </td>
                    <td>
                      {x.state === "high"
                        ? "偏高"
                        : x.state === "low"
                          ? "偏低"
                          : "证据不足，保留"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
          <div className="research-actions">
            <button
              onClick={() => {
                const next = {
                  ...input,
                  candidates: result.numbers,
                  rules: [],
                  combination: { mode: "strict" as const, minimum: 0 },
                };
                setUndo({ before: input, applied: JSON.stringify(next) });
                onChange(next);
              }}
            >
              载入实验预算集合
            </button>
            <button
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(
                    JSON.stringify(
                      { version: "discovery-v1", input, result },
                      null,
                      2,
                    ),
                  );
                  setNotice("集合完整报告已复制");
                } catch {
                  setNotice("复制失败，结果仍保留");
                }
              }}
            >
              复制集合完整报告
            </button>
          </div>
        </div>
      )}
      {undo && (
        <button
          disabled={JSON.stringify(input) !== undo.applied}
          onClick={() => {
            onChange(undo.before);
            setUndo(null);
          }}
        >
          撤销实验载入
        </button>
      )}
    </section>
  );
}
