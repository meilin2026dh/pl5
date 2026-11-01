import { useEffect, useRef, useState } from "react";
import type { FilterInput } from "../domain/pick5";
import {
  defaultEvidence,
  validateEvidence,
  type EvidenceConfig,
} from "../domain/evidence/config";
import type { EvidenceResult } from "../domain/evidence/engine";
export default function EvidenceLab({
  input,
  onChange,
}: {
  input: FilterInput;
  onChange: (i: FilterInput) => void;
}) {
  const c = input.evidence ?? defaultEvidence,
    signature = JSON.stringify({ ...input, evidence: c });
  const [result, setResult] = useState<EvidenceResult | null>(null),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  const [undo, setUndo] = useState<{
    before: FilterInput;
    applied: string;
  } | null>(null);
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
  const patch = (p: Partial<EvidenceConfig>) =>
    onChange({ ...input, evidence: { ...c, ...p } });
  const numeric = (
    label: string,
    key: Exclude<keyof EvidenceConfig, "referenceIssue">,
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
  const run = () => {
    try {
      validateEvidence(c);
      if (!input.evidence) onChange({ ...input, evidence: { ...c } });
      worker.current?.terminate();
      const id = ++serial.current,
        w = new Worker(
          new URL("../workers/evidence.worker.ts", import.meta.url),
          { type: "module" },
        );
      worker.current = w;
      setResult(null);
      setBusy(true);
      setNotice("准备数据质量与证据体检");
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
          setNotice(e.data.result.notice);
        }
      };
      w.onerror = () => {
        if (id !== serial.current) return;
        finish();
        setNotice("证据体检线程失败，请重试");
      };
      w.postMessage({ id, input, config: c });
    } catch (e) {
      setNotice((e as Error).message);
    }
  };
  const pvalue = (p: number) => (p < 0.0001 ? "<0.0001" : p.toFixed(4)),
    pct = (n: number) => (100 * n).toFixed(3) + "%";
  const report = result && !result.blocked ? result : null;
  return (
    <section className="research-card" aria-labelledby="evidence-title">
      <header>
        <div>
          <span className="research-kicker">EVIDENCE BEFORE BIAS</span>
          <h2 id="evidence-title">随机性与稳健性体检</h2>
        </div>
      </header>
      <p className="research-context">
        数据质量 → 随机性/变点检验 → 调参/校准/最终时间外检验 → 模型分歧复核 →
        预算与多样性。来源：{input.historySource ?? "未标注"} ·{" "}
        {input.history?.length ?? 0}
        期。检验不证明公平或不公平，分歧不等于更容易开出。
      </p>
      <div className="research-fields">
        {numeric("证据训练窗口", "window", 40, 500)}
        {numeric("随机性观察窗口", "monitor", 40, 500)}
        {numeric("变点滚动检查数", "checks", 1, 5)}
        {numeric("零假设重采样次数", "resamples", 99, 999)}
        {numeric("证据显著性水平", "alpha", 0.001, 0.1, 0.001)}
        {numeric("模型调参期数", "tune", 20, 100)}
        {numeric("概率校准期数", "calibration", 20, 100)}
        {numeric("最终时间外期数", "test", 30, 200)}
        {numeric("审查组合注数预算", "budget", 1, 100)}
        {numeric("证据随机种子", "seed", 0, 4294967295)}
        <label>
          证据历史截止期
          <input
            aria-label="证据历史截止期"
            placeholder="留空为最新"
            value={c.referenceIssue ?? ""}
            onChange={(e) =>
              patch({ referenceIssue: e.target.value || undefined })
            }
          />
        </label>
      </div>
      <details>
        <summary>检验前提与预设回退门槛</summary>
        <p className="research-context">
          均匀频率与重复结构由独立均匀模拟检验；依赖和变点通过整期向量置换，前提是零假设下记录可交换。变点最大统计量涵盖所有候选切点，再对本次检验家族作Holm校正。最小模拟p值为1/(重采样次数+1)，不会显示为0；频繁改窗口或重复体检仍有额外试探风险。
        </p>
        <p className="research-context">
          固定起点Dirichlet混合似然比只对独立均匀零假设具有序贯解释；不称分布无关变点定位。数据源或起点更换后不能沿用原序贯保证。
        </p>
        <p className="research-context">
          调参段选均匀/IID/Markov及窗口和平滑，校准段选择与均匀混合权重；最终段锁定这些配置，逐期仅用此前记录更新计数。门槛：最终≥60期、配对增益近似95%区间为正、3段均为正、邻近窗口不退化、顶标签ECE≤0.05、删除单期仍为正、单期贡献≤20%，且本次校正检验有异常证据。门槛通过也只允许实验偏置，不能称预测优势。
        </p>
        <p className="research-context">
          结构评估使用逐位10分类，不等于10万组合概率已获校准。变点只建议复核和缩窗，不在看完最终段后偷偷更换策略。最终段已经被看过，改参数后不再是未见测试。
        </p>
      </details>
      <div className="research-actions">
        <button disabled={busy} onClick={run}>
          运行随机性与稳健性体检
        </button>
        {busy && (
          <button
            onClick={() => {
              serial.current++;
              worker.current?.terminate();
              worker.current = null;
              setBusy(false);
              setNotice("已取消证据体检；不采用部分结果");
            }}
          >
            取消证据体检
          </button>
        )}
      </div>
      {notice && <p role="status">{notice}</p>}
      {result && (
        <p className="research-context">
          数据质量：共{result.quality.count}条；错误
          {result.quality.errors.length}；日期间隔{result.quality.gaps}
          处；原顺序倒置{result.quality.outOfOrder}
          处。日期间隔可能为休市或未知缺期，不直接认定遗漏开奖。
          {result.quality.errors.join("；")}
        </p>
      )}
      {report && (
        <div aria-label="证据体检结果">
          <div className="tolerance-box">
            <strong>{report.recommendation.policy}</strong>
            <p>
              {report.recommendation.reasons.join("；") ||
                "预设门槛全部通过；仍需后续新数据复核"}
              。
            </p>
          </div>
          <p className="research-context">
            截止{report.cutoff}。本次变点检查告警
            {report.recommendation.changeCount}处，建议复核窗口
            {report.recommendation.recommendedWindow}期（未自动应用）。
            {report.recommendation.warning}
          </p>
          <div style={{ overflowX: "auto" }}>
            <table className="potential-table" aria-label="随机性检验表">
              <thead>
                <tr>
                  <th>检验</th>
                  <th>截止</th>
                  <th>原始p</th>
                  <th>Holm校正</th>
                  <th>最大统计切点</th>
                </tr>
              </thead>
              <tbody>
                {report.checks.map((t, i) => (
                  <tr key={i}>
                    <td>{t.label}</td>
                    <td>{t.end}</td>
                    <td>{pvalue(t.p)}</td>
                    <td>
                      {pvalue(t.adjusted)}
                      {t.adjusted <= c.alpha ? " · 复核" : ""}
                    </td>
                    <td>{t.split ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="research-context">
            未显著的最大统计切点不等于真实变点。序贯固定起点
            {report.martingale.origin}；最大log E=
            {report.martingale.maxLogE.toFixed(3)}
            。告警可以来自数据源变化、录入错误或模型假设不适用，不能归因于开奖机制。
          </p>
          <h3>锁定策略的时间外校准</h3>
          <p>
            调参{report.validation.ranges.tune.join("—")}；校准
            {report.validation.ranges.calibration.join("—")}；最终检验
            {report.validation.ranges.test.join("—")}。
          </p>
          <p>
            所选{report.validation.modelName}，混合权重
            {report.validation.calibration.weight}。最终逐位log loss{" "}
            {report.validation.metrics.logLoss.toFixed(5)}，均匀基线
            {Math.log(10).toFixed(5)}；Brier{" "}
            {report.validation.metrics.brier.toFixed(5)}，均匀基线0.9；顶标签ECE{" "}
            {pct(report.validation.metrics.ece)}。
          </p>
          <p className="research-context">
            按期平均log loss增益{report.validation.gain.mean.toFixed(5)}
            ，近似95%区间[{report.validation.gain.low.toFixed(5)}，
            {report.validation.gain.high.toFixed(5)}
            ]；正值表示低于均匀损失。Brier同时受校准与区分能力影响，不能单独证明校准。
          </p>
          <svg
            viewBox="0 0 280 230"
            role="img"
            aria-label="时间外顶标签可靠性图"
            style={{ width: "100%", maxWidth: 380 }}
          >
            <path d="M35 15V195H255" fill="none" stroke="#b3a79b" />
            <path d="M35 195L235 15" stroke="#c4b6a7" strokeDasharray="4 4" />
            <text x="100" y="225" fontSize="11">
              平均顶标签模型概率
            </text>
            <text x="35" y="10" fontSize="10">
              实际正确比例
            </text>
            <text x="25" y="210" fontSize="10">
              0
            </text>
            <text x="235" y="210" fontSize="10">
              1
            </text>
            {report.validation.metrics.reliability.map((b, i) => (
              <circle
                key={i}
                cx={35 + b.predicted * 200}
                cy={195 - b.observed * 180}
                r={Math.min(10, 4 + Math.sqrt(b.n) / 8)}
                fill="#ff792f"
              >
                <title>
                  {b.n}个位置预测：模型{pct(b.predicted)}，实际{pct(b.observed)}
                </title>
              </circle>
            ))}
          </svg>
          <div style={{ overflowX: "auto" }}>
            <table className="potential-table" aria-label="校准分箱明细">
              <thead>
                <tr>
                  <th>模型概率区间</th>
                  <th>位置样本数</th>
                  <th>平均概率</th>
                  <th>实际正确</th>
                </tr>
              </thead>
              <tbody>
                {report.validation.metrics.reliability.map((b, i) => (
                  <tr key={i}>
                    <td>
                      {b.lo.toFixed(1)}—{b.hi.toFixed(1)}
                    </td>
                    <td>{b.n}</td>
                    <td>{pct(b.predicted)}</td>
                    <td>{pct(b.observed)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h3>反过拟合压力检查</h3>
          <p className="research-context">
            锁定策略逐段对照；每段也仅用此前调参和校准记录重新选模型，报告胜者变化，不挑选最好一段冒充整体效果。相邻窗口和删除单期检查只用于揭露脆弱性，不再据此挑新冠军。
          </p>
          <div style={{ overflowX: "auto" }}>
            <table className="potential-table" aria-label="时间分段稳健性">
              <thead>
                <tr>
                  <th>最终分段</th>
                  <th>锁定增益</th>
                  <th>此前重选模型</th>
                  <th>重选增益</th>
                </tr>
              </thead>
              <tbody>
                {report.validation.blocks.map((b, i) => (
                  <tr key={i}>
                    <td>{b.range.join("—")}</td>
                    <td>{b.locked.mean.toFixed(5)}</td>
                    <td>
                      {b.reselected}，λ{b.weight}
                    </td>
                    <td>{b.reselectedGain.mean.toFixed(5)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="research-context">
            邻近窗口：
            {report.validation.variants
              .map((v) => `W${v.window}：${v.mean.toFixed(5)}`)
              .join("；")}
            。最大单期绝对贡献占比{pct(report.validation.gain.maxSingleShare)}
            ，删除单期最弱平均增益
            {report.validation.gain.leaveOneWorst.toFixed(5)}。
          </p>
          <details>
            <summary>三模型分歧复核清单</summary>
            <p className="research-context">
              全空间JS={report.disagreement.js.toFixed(6)}{" "}
              nats。高分仅表示假设分歧，不直接筛除或推荐。表内是各模型相对均匀概率的倍数，不是真实开奖概率。
            </p>
            <div style={{ overflowX: "auto" }}>
              <table className="potential-table" aria-label="模型分歧候选">
                <thead>
                  <tr>
                    <th>号码</th>
                    <th>均匀</th>
                    <th>IID</th>
                    <th>Markov</th>
                    <th>JS贡献</th>
                  </tr>
                </thead>
                <tbody>
                  {report.disagreement.top.map((r) => (
                    <tr key={r.number}>
                      <td>{r.number}</td>
                      {r.probabilities.map((p, i) => (
                        <td key={i}>{(p * 100000).toFixed(3)}</td>
                      ))}
                      <td>{r.contribution.toExponential(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
          <h3>预算内审查组合</h3>
          <p>
            当前规则通过{report.portfolio.base}组，搜索短名单
            {report.portfolio.pool}组，输出{report.portfolio.numbers.length}/
            {c.budget}注，最小汉明距离{report.portfolio.minDistance ?? "—"}
            ；理论精确覆盖{pct(report.portfolio.exactProbability)}。Guard通过。
          </p>
          <p className="research-context">
            {report.portfolio.policy}
            。最大最小距离是短名单贪心，不证明最优；无可行候选时不放松条件。
          </p>
          <p aria-label="证据审查号码" className="research-context">
            {report.portfolio.numbers.join("　") || "当前规则无可行候选"}
          </p>
          <details>
            <summary>完整检验假设、校准选择与决策记录</summary>
            <pre className="innovation-json">
              {JSON.stringify(report, null, 2)}
            </pre>
          </details>
          <div className="research-actions">
            <button
              disabled={!report.portfolio.numbers.length}
              onClick={() => {
                const next = {
                  ...input,
                  candidates: report.portfolio.numbers,
                  rules: input.rules.map((r) => ({ ...r, enabled: false })),
                  combination: { mode: "strict" as const, minimum: 0 },
                };
                setUndo({
                  before: input,
                  applied: JSON.stringify({
                    ...next,
                    evidence: next.evidence ?? defaultEvidence,
                  }),
                });
                onChange(next);
              }}
            >
              载入审查组合并停用原条件
            </button>
            <button
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(
                    JSON.stringify(
                      { version: "evidence-v1", input, result: report },
                      null,
                      2,
                    ),
                  );
                  setNotice("证据体检报告已复制");
                } catch {
                  setNotice("复制失败，仍可在页面查看记录");
                }
              }}
            >
              复制证据体检报告
            </button>
          </div>
        </div>
      )}
      {undo && (
        <button
          disabled={signature !== undo.applied}
          onClick={() => {
            onChange(undo.before);
            setUndo(null);
          }}
        >
          撤销审查载入
        </button>
      )}
    </section>
  );
}
