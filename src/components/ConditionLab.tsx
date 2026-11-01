import { useEffect, useRef, useState } from "react";
import type { FilterInput } from "../domain/pick5";
import {
  defaultAudit,
  validateAudit,
  type AuditConfig,
} from "../domain/audit/config";
import type { analyzeConditions } from "../domain/audit/engine";
export default function ConditionLab({
  input,
  onChange,
}: {
  input: FilterInput;
  onChange: (i: FilterInput) => void;
}) {
  const c = input.audit ?? defaultAudit,
    signature = JSON.stringify({ ...input, audit: c });
  const [result, setResult] = useState<ReturnType<
      typeof analyzeConditions
    > | null>(null),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  const worker = useRef<Worker | null>(null),
    serial = useRef(0);
  useEffect(() => {
    serial.current++;
    worker.current?.terminate();
    worker.current = null;
    setResult(null);
    setBusy(false);
    setNotice("");
  }, [signature]);
  useEffect(() => () => worker.current?.terminate(), []);
  const patch = (p: Partial<AuditConfig>) =>
    onChange({ ...input, audit: { ...c, ...p } });
  const numeric = (
    label: string,
    key: "training" | "target" | "correlation" | "folds" | "validation",
    min: number,
    max: number,
    step = 1,
  ) => (
    <label>
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
    setNotice("已取消条件体检；没有采用部分结果。");
  };
  const run = (walk: boolean) => {
    try {
      validateAudit(c);
      if (!input.audit) onChange({ ...input, audit: { ...c } });
      worker.current?.terminate();
      const id = ++serial.current,
        w = new Worker(new URL("../workers/audit.worker.ts", import.meta.url), {
          type: "module",
        });
      worker.current = w;
      setResult(null);
      setBusy(true);
      setNotice("准备计算条件掩码");
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
        else {
          setResult(e.data.result);
          setNotice(
            walk
              ? "Walk-forward体检完成；验证期未参与本折选条件。"
              : "相关性分析与注数预算选择完成。",
          );
        }
      };
      w.onerror = () => {
        if (id !== serial.current) return;
        finish();
        setNotice("条件体检线程失败，请重试。");
      };
      w.postMessage({ id, input, config: c, walk });
    } catch (e) {
      setNotice((e as Error).message);
    }
  };
  return (
    <section className="research-card" aria-labelledby="condition-title">
      <header>
        <div>
          <span className="research-kicker">CONDITION HEALTH</span>
          <h2 id="condition-title">条件池与样本外体检</h2>
        </div>
      </header>
      <p className="research-context">
        历史来源：{input.historySource || "未载入"} ·{" "}
        {input.history?.length ?? 0}
        期。先看10万组二值相关性，再按“新增压缩量÷(1+位置数字覆盖损失)”贪心选择，目标为注数上限，不保证恰好等于目标。
      </p>
      <div className="research-fields">
        <label>
          体检条件池
          <select
            aria-label="体检条件池"
            value={c.pool}
            onChange={(e) =>
              patch({ pool: e.target.value as AuditConfig["pool"] })
            }
          >
            <option value="suggested">内置18条研究条件</option>
            <option value="current">当前启用条件（最多20条）</option>
          </select>
        </label>
        {numeric("体检训练期数", "training", 20, 500)}
        {numeric("体检目标注数", "target", 1, 100000)}
        {numeric("去冗相关阈值", "correlation", 0, 1, 0.01)}
        {numeric("体检滚动折数", "folds", 1, 5)}
        {numeric("每折样本外期数", "validation", 1, 100)}
        <label>
          体检参考期
          <input
            aria-label="体检参考期"
            value={c.referenceIssue ?? ""}
            placeholder="留空为最新"
            onChange={(e) =>
              patch({ referenceIssue: e.target.value.trim() || undefined })
            }
          />
        </label>
      </div>
      <label className="research-context">
        <input
          aria-label="启用相关性去冗"
          type="checkbox"
          checked={c.dedupe}
          onChange={(e) => patch({ dedupe: e.target.checked })}
        />{" "}
        先去冗再选条件：按条件池顺序保留代表，正相关达到阈值才删；负相关不冒充重复。
      </label>
      <p className="research-context">
        多样性代价仅用“五个位置可出现数字种数之和”（最多50）作代理；贪心非最优、去冗非无损。常量掩码相关性未定义，完全相同常量可合并。空集不会被当作达标方案。应用历史条件会固定本次训练起止范围。
      </p>
      <div className="research-actions">
        <button disabled={busy} onClick={() => run(false)}>
          分析相关性与预算
        </button>
        <button disabled={busy} onClick={() => run(true)}>
          运行Walk-forward体检
        </button>
        {busy && <button onClick={cancel}>取消条件体检</button>}
      </div>
      {notice && (
        <p role="status" className="research-context">
          {notice}
        </p>
      )}
      {result && (
        <div aria-label="条件体检结果">
          <p className="research-context">
            训练{result.analysis.trainingStart}—{result.analysis.trainingEnd} ·
            当前候选{result.analysis.initial} → 保留{result.analysis.remaining}
            ，目标≤{result.analysis.target}；位置数字覆盖
            {result.analysis.positionCoverage}/50。
            {result.analysis.reached
              ? "达到注数上限。"
              : "未达标：剩余条件没有非空的新增压缩。"}
          </p>
          <ol className="research-context">
            {result.analysis.conditions.map((r, i) => (
              <li key={r.id}>
                {i + 1}. {r.label}：单条件通过{r.count}/100000
              </li>
            ))}
          </ol>
          <details>
            <summary>查看二值条件相关矩阵（Phi）</summary>
            <div style={{ overflow: "auto", maxHeight: 420 }}>
              <table className="potential-table" aria-label="条件相关性矩阵">
                <thead>
                  <tr>
                    <th>条件</th>
                    {result.analysis.conditions.map((r, i) => (
                      <th title={r.label} key={r.id}>
                        {i + 1}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.analysis.matrix.map((row, i) => (
                    <tr key={i}>
                      <td title={result.analysis.conditions[i].label}>
                        {i + 1}
                      </td>
                      {row.map((p, j) => (
                        <td
                          key={j}
                          style={{
                            background:
                              p !== null && p >= c.correlation
                                ? "#ffead2"
                                : p !== null && p < 0
                                  ? "#edf3f5"
                                  : undefined,
                          }}
                        >
                          {p === null ? "—" : p.toFixed(2)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
          <p className="research-context">
            去冗{result.analysis.redundant.length}条：
            {result.analysis.redundant
              .map(
                (r) =>
                  `${r.id}→${r.against}（${r.correlation === null ? "相同常量" : r.correlation.toFixed(3)}）`,
              )
              .join("；") || "无"}
            。
          </p>
          {result.analysis.errors.length > 0 && (
            <p className="notice">
              未参与计算的条件：
              {result.analysis.errors
                .map((r) => `${r.id}：${r.reason}`)
                .join("；")}
            </p>
          )}
          <div style={{ overflowX: "auto" }}>
            <table className="potential-table" aria-label="预算贪心步骤">
              <thead>
                <tr>
                  <th>条件</th>
                  <th>筛前</th>
                  <th>筛后</th>
                  <th>新增压缩</th>
                  <th>覆盖损失</th>
                  <th>比值</th>
                </tr>
              </thead>
              <tbody>
                {result.analysis.steps.map((s) => (
                  <tr key={s.id}>
                    <td>{s.label}</td>
                    <td>{s.before}</td>
                    <td>{s.after}</td>
                    <td>{s.removed}</td>
                    <td>{s.diversityLoss}</td>
                    <td>{s.ratio.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="research-actions">
            <button
              disabled={!result.analysis.selectedRules.length}
              onClick={() => {
                const selected = result.analysis.selectedRules;
                onChange({
                  ...input,
                  rules: [
                    ...input.rules
                      .filter((r) => !selected.some((s) => s.id === r.id))
                      .map((r) => ({ ...r, enabled: false })),
                    ...selected,
                  ],
                  combination: { mode: "strict", minimum: 0 },
                });
              }}
            >
              应用选中条件（其余停用）
            </button>
          </div>
          {result.folds && (
            <>
              <h3>Walk-forward样本外曲线</h3>
              <p className="research-context">
                每折只用此前训练窗拟合、去冗和选条件，验证段保持掩码不变；外部大底和人工条件池仍可能含事后选择。小样本零覆盖不等于条件失效，不自动淘汰。
              </p>
              <svg
                role="img"
                aria-label="样本外覆盖与压缩曲线"
                viewBox="0 0 460 120"
                style={{ width: "100%", maxWidth: 600 }}
              >
                <line x1="20" y1="100" x2="440" y2="100" stroke="#ccc" />
                {(["coverage", "compression"] as const).map((key, k) => (
                  <polyline
                    key={key}
                    fill="none"
                    stroke={k ? "#6d8f9b" : "#f57b32"}
                    strokeWidth="2"
                    points={result
                      .folds!.map(
                        (f, i) =>
                          `${20 + (i * 420) / Math.max(1, result.folds!.length - 1)},${100 - f[key] * 80}`,
                      )
                      .join(" ")}
                  />
                ))}
              </svg>
              <p className="small muted">
                橙线：覆盖率；蓝线：压缩率。横轴按验证折次顺序，纵轴0—100%。
              </p>
              <div style={{ overflowX: "auto" }}>
                <table
                  className="potential-table"
                  aria-label="Walk-forward逐折记录"
                >
                  <thead>
                    <tr>
                      {[
                        "训练截止",
                        "验证范围",
                        "保留注数",
                        "覆盖",
                        "压缩率",
                        "覆盖×压缩",
                        "均匀期望覆盖",
                        "大底外",
                      ].map((t) => (
                        <th key={t}>{t}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.folds.map((f) => (
                      <tr key={f.validationStart}>
                        <td>{f.trainingEnd}</td>
                        <td>
                          {f.validationStart}—{f.validationEnd}
                        </td>
                        <td>{f.remaining}</td>
                        <td>
                          {f.hits}/{f.validationCount}
                        </td>
                        <td>{(f.compression * 100).toFixed(1)}%</td>
                        <td>{f.product.toFixed(4)}</td>
                        <td>{f.expectedUniformHits.toFixed(3)}</td>
                        <td>{f.outside}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </section>
  );
}
