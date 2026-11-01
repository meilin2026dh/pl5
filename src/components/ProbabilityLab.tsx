import { numberAt } from "../domain/probability/sets";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { FilterInput } from "../domain/pick5";
import {
  defaultProbability,
  validateProbability,
  type ProbabilityConfig,
} from "../domain/probability/config";
import {
  inspectNumber,
  type ProbabilityResult,
} from "../domain/probability/engine";
import type { OnlineState } from "../domain/probability/online";
import { names, kinds } from "../domain/probability/models";
const stateKey = "pl5-probability-online-v1",
  seenKey = "pl5-probability-seen-v1";
type Exposure = { start: string; end: string };
function storedState(): OnlineState | undefined {
  try {
    const s = JSON.parse(localStorage.getItem(stateKey) ?? "null");
    if (
      s?.version === "probability-online-v1" &&
      Array.isArray(s.training) &&
      Array.isArray(s.consumed)
    )
      return s;
  } catch {}
  return undefined;
}
function recordExposure(start: string, end: string) {
  const raw = JSON.parse(localStorage.getItem(seenKey) ?? "[]");
  if (
    !Array.isArray(raw) ||
    raw.some((x) => typeof x.start !== "string" || typeof x.end !== "string")
  )
    throw Error("试验登记损坏");
  const seen = (raw as Exposure[]).some(
      (x) => x.start <= end && x.end >= start,
    ),
    ranges = [...raw, { start, end }].sort((a, b) =>
      a.start.localeCompare(b.start),
    ),
    merged: Exposure[] = [];
  for (const r of ranges) {
    const last = merged.at(-1);
    if (last && r.start <= last.end)
      last.end = last.end > r.end ? last.end : r.end;
    else merged.push({ ...r });
  }
  localStorage.setItem(seenKey, JSON.stringify(merged));
  return seen;
}
const pct = (n: number) => (n * 100).toFixed(3) + "%";
function Table({
  label,
  heads,
  rows,
}: {
  label: string;
  heads: string[];
  rows: ReactNode[][];
}) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table className="potential-table" aria-label={label}>
        <thead>
          <tr>
            {heads.map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {r.map((v, j) => (
                <td key={j}>{v}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function LazyDetails({
  title,
  children,
}: {
  title: string;
  children: () => ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <details onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary>{title}</summary>
      {open && children()}
    </details>
  );
}
function Lines({ label, values }: { label: string; values: number[][] }) {
  const all = values.flat(),
    lo = Math.min(0, ...all),
    hi = Math.max(1, ...all),
    colors = ["#f07530", "#488d82", "#9860b1", "#cc9b22"];
  return (
    <svg
      viewBox="0 0 420 150"
      style={{ width: "100%", maxWidth: 520 }}
      role="img"
      aria-label={label}
    >
      <path d="M20 10V130H410" stroke="#c9baaa" fill="none" />
      {values.map((line, i) => (
        <polyline
          key={i}
          fill="none"
          stroke={colors[i]}
          strokeWidth="1.5"
          points={line
            .map(
              (y, j) =>
                `${20 + (j / Math.max(1, line.length - 1)) * 385},${130 - ((y - lo) / (hi - lo)) * 115}`,
            )
            .join(" ")}
        />
      ))}
      <text x="20" y="148" fontSize="10">
        按时间顺序 · U橙 / I绿 / J1紫 / J2金
      </text>
    </svg>
  );
}
export default function ProbabilityLab({
  input,
  onChange,
}: {
  input: FilterInput;
  onChange: (i: FilterInput) => void;
}) {
  const c = input.probability ?? defaultProbability,
    signature = useMemo(
      () =>
        JSON.stringify({
          ...input,
          probability: input.probability ?? defaultProbability,
        }),
      [input],
    ),
    serial = useRef(0),
    worker = useRef<Worker | null>(null);
  const [result, setResult] = useState<ProbabilityResult | null>(null),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState(""),
    [seen, setSeen] = useState<boolean | null>(null),
    [showSet, setShowSet] = useState(false),
    [page, setPage] = useState(0),
    [query, setQuery] = useState("00000"),
    [audit, setAudit] = useState<ReturnType<typeof inspectNumber> | null>(null),
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
    setAudit(null);
    setShowSet(false);
    setPage(0);
  }, [signature]);
  useEffect(() => () => worker.current?.terminate(), []);
  const patch = (p: Partial<ProbabilityConfig>) =>
    onChange({ ...input, probability: { ...c, ...p } });
  const numeric = (
    label: string,
    key: Exclude<keyof ProbabilityConfig, "referenceIssue" | "uniformOnly">,
    min: number,
    max: number,
    step = 1,
  ) => (
    <label key={key}>
      {label}
      <input
        type="number"
        aria-label={label}
        value={c[key]}
        min={min}
        max={max}
        step={step}
        onChange={(e) => patch({ [key]: Number(e.target.value) })}
      />
    </label>
  );
  const run = () => {
    try {
      validateProbability(c);
      if (!input.probability) onChange({ ...input, probability: { ...c } });
      worker.current?.terminate();
      const id = ++serial.current,
        w = new Worker(
          new URL("../workers/probability.worker.ts", import.meta.url),
          { type: "module" },
        );
      worker.current = w;
      setBusy(true);
      setResult(null);
      setAudit(null);
      setNotice("准备自适应概率实验");
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
        const r = e.data.result as ProbabilityResult;
        let storage = "";
        try {
          const start = input.history!.find(
              (x) => x.issue === r.ranges.test[0],
            )!.date,
            end = input.history!.find(
              (x) => x.issue === r.ranges.test[1],
            )!.date;
          setSeen(recordExposure(start, end));
          localStorage.setItem(stateKey, JSON.stringify(r.online.state));
        } catch {
          setSeen(null);
          storage = "；本机登记不可用，不能确认测试未被看过";
        }
        setResult(r);
        setShowSet(false);
        setPage(0);
        setNotice(r.notice + storage);
      };
      w.onerror = () => {
        if (id !== serial.current) return;
        finish();
        setNotice("概率计算线程失败，请重试");
      };
      w.postMessage({ id, input, config: c, previous: storedState() });
    } catch (e) {
      setNotice((e as Error).message);
    }
  };
  const load = (numbers: string[]) => {
    const next = {
      ...input,
      candidates: numbers,
      rules: input.rules.map((r) => ({ ...r, enabled: false })),
      combination: { mode: "strict" as const, minimum: 0 },
    };
    setUndo({
      before: input,
      applied: JSON.stringify({
        ...next,
        probability: next.probability ?? defaultProbability,
      }),
    });
    onChange(next);
  };
  return (
    <section className="research-card" aria-labelledby="probability-title">
      <header>
        <div>
          <span className="research-kicker">TEST THE ASSUMPTION</span>
          <h2 id="probability-title">自适应概率实验室</h2>
        </div>
      </header>
      <p className="research-context">
        贝叶斯门控 · 联合图模型 · MDL · 保形集合 · 最优传输 · 在线专家。来源：
        {input.historySource ?? "未标注"} · {input.history?.length ?? 0}
        期。公平独立时，任意在开奖前确定的n个不同号码，精确命中概率仍为n/100000。
      </p>
      <p className="research-context">
        本配置至少需要{c.train + c.calibration + c.test}
        期历史。若当前为演示数据或数量不足，请到“历史走势”载入官方历史后再运行。
      </p>
      <div className="research-fields">
        {numeric("概率训练期数", "train", 100, 1000)}
        {numeric("保形校准期数", "calibration", 20, 500)}
        {numeric("概率最终检验期数", "test", 30, 500)}
        {numeric("目标集合覆盖率", "target", 0.5, 0.99, 0.01)}
        {numeric("概率预算注数", "budget", 1, 100000)}
        {numeric("Dirichlet总强度", "strength", 0.1, 100, 0.1)}
        {numeric("汉明W1扰动半径", "radius", 0, 5, 0.005)}
        {numeric("概率随机种子", "seed", 0, 4294967295)}
        <label>
          概率历史截止期
          <input
            aria-label="概率历史截止期"
            placeholder="留空为最新"
            value={c.referenceIssue ?? ""}
            onChange={(e) =>
              patch({ referenceIssue: e.target.value || undefined })
            }
          />
        </label>
      </div>
      <label>
        <input
          type="checkbox"
          aria-label="只用均匀基线对照"
          checked={c.uniformOnly ?? false}
          onChange={(e) => patch({ uniformOnly: e.target.checked })}
        />
        只用均匀基线对照（仍计算研究诊断，关闭模型偏置）
      </label>
      <details>
        <summary>算法与覆盖声明的前提</summary>
        <p>
          四模型为均匀U、独立位置I、万→个单父链J1和双父链J2。J2只表达局部三元条件关系，不代表任意五阶规律。先验U=1/2，其余各1/6；训练前部算BF、后验与含模型成本的MDL，二者同源。训练尾部60期门控，校准与最终测试不参与模型选择。
        </p>
        <p>
          完整五位号码使用冻结模型的负log概率作分数。k=ceil((校准数+1)×覆盖目标)，越界取无限阈值，同分全部保留。可交换性等前提下才有边际覆盖解释；不是每期、给定历史或时序漂移下的保证。均匀LAC会保留十万号；90%均匀精确覆盖至少需要九万注。
        </p>
        <p>
          预算组合另守当前来源及规则（规则历史截至校准结束）。规则相交或预算截断不能继承完整校准集合声明。W1半径是人为压力情景；下界只针对给定模型及球，不是真实开奖概率保证。Wilson区间以独立同分布伯努利解释为前提，否则仅描述性参考。
        </p>
        <p>
          在线轨道独立于冻结校准模型；先预测后更新。原始混合相对最佳固定专家遗憾≤−log其初始权重，统一上界log6；门控输出损失单独报告，不继承该界。完整历史前缀变更重建；本机已看测试登记不代表外部从未看过。
        </p>
      </details>
      <div className="research-actions">
        <button onClick={run} disabled={busy}>
          运行自适应概率实验
        </button>
        {busy && (
          <button
            onClick={() => {
              serial.current++;
              worker.current?.terminate();
              worker.current = null;
              setBusy(false);
              setNotice("已取消概率实验，不采用部分结果");
            }}
          >
            取消概率实验
          </button>
        )}
      </div>
      {notice && <p role="status">{notice}</p>}
      {result && (
        <div aria-label="自适应概率结果">
          <div className="tolerance-box">
            <strong>
              {result.gate.useBias
                ? "研究偏置门控通过"
                : "证据不足，均匀基线回退"}
            </strong>
            <p>
              {result.gate.reasons.join("；") ||
                "仅通过预设研究门槛，不证明预测优势"}
            </p>
            {seen === true ? (
              <p>本测试区间此前已查看；改参数或重跑不能恢复未见测试身份。</p>
            ) : (
              <p>
                {seen === false
                  ? "已登记本次查看；只是本机登记中首次出现，不代表外部未看过。"
                  : "本机登记不可用；测试污染状态未知。"}
              </p>
            )}
          </div>
          <p className="research-context">
            截止{result.cutoff}。拟合{result.ranges.fit.join("—")}；门控
            {result.ranges.gate.join("—")}；冻结训练
            {result.ranges.train.join("—")}；校准
            {result.ranges.calibration.join("—")}；最终
            {result.ranges.test.join("—")}。质量错误
            {result.quality.errors.length}，日期间隔{result.quality.gaps}
            处（不直接判缺期）。
          </p>
          <h3>证据与码长</h3>
          <Table
            label="贝叶斯证据与MDL"
            heads={[
              "模型",
              "参数",
              "先验",
              "后验",
              "log BF",
              "总码长bits",
              "较U节省bits",
            ]}
            rows={result.evidence.map((e) => [
              e.kind + " " + e.name,
              e.parameters,
              pct(e.prior),
              pct(e.posterior),
              e.logBF.toFixed(3),
              e.bits.toFixed(2),
              e.savedBits.toFixed(2),
            ])}
          />
          <Lines
            label="预序贯MDL累计码长"
            values={kinds.map((_, i) => result.codeCurve.map((x) => x.bits[i]))}
          />
          <p className="research-context">
            MDL含模型标识成本，与贝叶斯后验同源。门控平均log增益
            {result.gate.gain.mean.toFixed(4)}，近似95%下界
            {result.gate.gain.low.toFixed(4)}；三块
            {result.gate.gain.blocks.map((x) => x.toFixed(4)).join(" / ")}
            。正态近似不是严格序贯保证。
          </p>
          <details>
            <summary>先验强度敏感性（不据测试择优）</summary>
            <Table
              label="先验强度敏感性"
              heads={["总强度", "U后验", "I后验", "J1后验", "J2后验"]}
              rows={result.sensitivityPrior.map((s) => [
                s.strength,
                ...s.evidence.map((e) => pct(e.posterior)),
              ])}
            />
          </details>
          <h3>完整保形集合与预算冲突</h3>
          <p>
            主模型：{names[result.gate.kind]}；目标{pct(c.target)}；k=
            {result.conformal.k}；阈值
            {result.conformal.threshold?.toFixed(5) ?? "无限"}；完整保留
            <strong>{result.conformal.indices.length.toLocaleString()}</strong>
            注。最终历史覆盖{result.validation.hits}/{result.validation.n}（
            {pct(result.validation.coverage)}），Wilson参考[
            {result.validation.wilson.map(pct).join("，")}]；同大小均匀基线
            {pct(result.validation.uniformSetCoverage)}。
          </p>
          <p>
            整注最终log loss {result.validation.testLoss.toFixed(5)}，均匀
            {result.validation.uniformLoss.toFixed(5)}{" "}
            nats/期。该最终段只评估，未参与本次门控。
          </p>
          <p className="tolerance-box">
            {result.conflict
              ? "预算不足以容纳校准集合；预算结果不继承校准覆盖。"
              : result.portfolio.inheritsCoverage
                ? "预算组合包含完整校准集合；覆盖解释仍依赖可交换性等前提。"
                : "来源/规则限制改变集合；预算结果不继承校准覆盖。"}
          </p>
          <div className="research-actions">
            <button onClick={() => setShowSet(!showSet)}>
              {showSet ? "收起校准集合" : "查看完整校准集合"}
            </button>
          </div>
          {showSet && (
            <div aria-label="校准集合分页">
              <p>
                第{page + 1}/
                {Math.max(1, Math.ceil(result.conformal.indices.length / 100))}
                页 · 每页100号 · 共{result.conformal.indices.length}号
              </p>
              <p className="research-context">
                {result.conformal.indices
                  .slice(page * 100, (page + 1) * 100)
                  .map((n) => numberAt(n))
                  .join("　")}
              </p>
              <button disabled={page === 0} onClick={() => setPage(page - 1)}>
                校准集合上一页
              </button>
              <button
                disabled={(page + 1) * 100 >= result.conformal.indices.length}
                onClick={() => setPage(page + 1)}
              >
                校准集合下一页
              </button>
            </div>
          )}
          <h3>预算组合与超图覆盖</h3>
          <p>
            固定预算集合在最终留出期命中{result.validation.budgetHits}/
            {result.validation.n}；同注数随机基线
            {pct(result.portfolio.exactProbability)}
            。样本量小，不能由少数命中判定优势。
          </p>
          <p>
            来源域{result.portfolio.base.toLocaleString()}组；实际
            {result.portfolio.numbers.length.toLocaleString()}注；理论精确覆盖
            {pct(result.portfolio.exactProbability)}，理论漏失
            {pct(result.portfolio.missProbability)}。{result.portfolio.policy}。
          </p>
          <p>
            二位置赋值覆盖{result.hypergraph.pairs.covered}/1000；三位置赋值覆盖
            {result.hypergraph.triples.covered}
            /10000。这是结构覆盖，不是奖级或精确中奖概率。
            {result.sourceRestricted
              ? "来源域受当前大底/定位/规则限制。"
              : "来源域为十万全集。"}{" "}
            Guard：
            {Object.values(result.guard).every(Boolean) ? "通过" : "失败"}
          </p>
          <LazyDetails title="预算号码与未覆盖模式编号">
            {() => (
              <pre className="innovation-json">
                {result.portfolio.numbers.join(" ")}
                {"\n"}未覆盖模式示例：{result.hypergraph.missing.join("，")}
              </pre>
            )}
          </LazyDetails>
          <h3>汉明Wasserstein压力情景</h3>
          <Table
            label="Wasserstein压力情景"
            heads={[
              "半径",
              "四模型最弱下界",
              "U下界",
              "I下界",
              "J1下界",
              "J2下界",
            ]}
            rows={result.robustness.map((r) => [
              r.radius,
              pct(r.worstLower),
              ...r.bounds.map((b) => pct(b.lower)),
            ])}
          />
          <p className="research-context">
            认证对象为当前预算集合，汉明代价0—5；允许质量搬到任意补集节点、无容量限制。半径未经置信校准，不是实际中奖下界，也未求全局最优鲁棒集合。
          </p>
          <details>
            <summary>四模型分歧与撤销敏感性</summary>
            <p>
              全空间JS {result.disagreement.js.toFixed(6)}{" "}
              nats；等权混合研究集合{result.disagreement.mixtureSize}
              注。以下只作复核，不改变主门控或预算。
            </p>
            <Table
              label="撤销模型敏感性"
              heads={["去掉模型", "集合大小", "改变号码数"]}
              rows={result.disagreement.sensitivity.map((x) => [
                x.removed,
                x.size,
                x.changed,
              ])}
            />
            <Table
              label="联合模型分歧"
              heads={["号码", "U倍数", "I倍数", "J1倍数", "J2倍数"]}
              rows={result.disagreement.top.map((x) => [
                x.number,
                ...x.probabilities.map((p) => (p * 100000).toFixed(2)),
              ])}
            />
          </details>
          <h3>在线专家轨迹</h3>
          <Lines
            label="在线专家先验更新轨迹"
            values={kinds.map((_, i) =>
              result.online.trace.map((x) => x.weights[i]),
            )}
          />
          <p>
            门控输出累计损失{result.online.outputLoss.toFixed(3)}（冻结
            {result.online.outputPolicy}）；原始混合累计损失
            {result.online.state.mixtureLoss.toFixed(3)}
            ；相对最佳固定专家遗憾{result.online.regret.toFixed(5)} ≤{" "}
            {result.online.bound.toFixed(5)}。
            {result.online.rebuilt
              ? "完整历史/来源或配置变化，已重建状态。"
              : "已按规范历史重放，无重复累计。"}{" "}
            门控输出轨道与该混合分开，不能继承遗憾界。
          </p>
          <LazyDetails title="逐期权重和损失">
            {() => (
              <Table
                label="在线逐期记录"
                heads={[
                  "期号",
                  "U权重",
                  "I权重",
                  "J1权重",
                  "J2权重",
                  "本期损失",
                  "累计遗憾",
                ]}
                rows={result.online.trace.map((x) => [
                  x.issue,
                  ...x.weights.map(pct),
                  x.loss.toFixed(4),
                  x.regret.toFixed(4),
                ])}
              />
            )}
          </LazyDetails>
          <h3>任意号码决策查询</h3>
          <div className="research-fields">
            <label>
              概率审计号码
              <input
                aria-label="概率审计号码"
                value={query}
                maxLength={5}
                onChange={(e) => setQuery(e.target.value)}
              />
            </label>
          </div>
          <button
            onClick={() => {
              try {
                setAudit(inspectNumber(result, query));
              } catch (e) {
                setNotice((e as Error).message);
              }
            }}
          >
            查询概率决策
          </button>
          {audit && (
            <pre aria-label="号码概率决策" className="innovation-json">
              {JSON.stringify(audit, null, 2)}
            </pre>
          )}
          <div className="research-actions">
            <button
              disabled={
                !result.portfolio.numbers.length ||
                !Object.values(result.guard).every(Boolean)
              }
              onClick={() => load(result.portfolio.numbers)}
            >
              载入概率预算组合并停用原条件
            </button>
            <button
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(
                    JSON.stringify(
                      {
                        version: "probability-v1",
                        input,
                        result,
                        exposure: { previouslyViewed: seen },
                      },
                      null,
                      2,
                    ),
                  );
                  setNotice("完整概率实验报告已复制，含输入快照和校准集合");
                } catch {
                  setNotice("复制失败，页面结果保留");
                }
              }}
            >
              复制概率实验报告
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
          撤销概率载入
        </button>
      )}
    </section>
  );
}
