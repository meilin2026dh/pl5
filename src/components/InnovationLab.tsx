import { useEffect, useRef, useState } from "react";
import type { FilterInput } from "../domain/pick5";
import {
  defaultInnovation,
  validateInnovation,
  type InnovationConfig,
} from "../domain/innovation/config";
import {
  explainInnovation,
  type InnovationResult,
} from "../domain/innovation/engine";
const featureNames = [
  "条件通过比例",
  "局部形态残差",
  "历史最近距离",
  "候选图稀疏度",
];
export default function InnovationLab({
  input,
  onChange,
}: {
  input: FilterInput;
  onChange: (i: FilterInput) => void;
}) {
  const c = input.innovation ?? defaultInnovation,
    signature = JSON.stringify({ ...input, innovation: c });
  const [result, setResult] = useState<InnovationResult | null>(null),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState(""),
    [query, setQuery] = useState("00000"),
    [undo, setUndo] = useState<{ before: FilterInput; applied: string } | null>(
      null,
    );
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
  const patch = (p: Partial<InnovationConfig>) =>
    onChange({ ...input, innovation: { ...c, ...p } });
  const run = () => {
    try {
      validateInnovation(c);
      if (!input.innovation) onChange({ ...input, innovation: { ...c } });
      worker.current?.terminate();
      const id = ++serial.current,
        w = new Worker(
          new URL("../workers/innovation.worker.ts", import.meta.url),
          { type: "module" },
        );
      worker.current = w;
      setBusy(true);
      setResult(null);
      setNotice("准备覆盖与审计实验");
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
          setNotice("实验完成；覆盖认证仅针对所列目标域与定位匹配数。");
          setQuery(e.data.result.numbers[0] ?? "00000");
        }
      };
      w.onerror = () => {
        if (id !== serial.current) return;
        finish();
        setNotice("覆盖实验线程失败，请重试");
      };
      w.postMessage({ id, input, config: c });
    } catch (e) {
      setNotice((e as Error).message);
    }
  };
  let explanation: ReturnType<typeof explainInnovation> | null = null,
    error = "";
  if (result)
    try {
      explanation = explainInnovation(result, query);
    } catch (e) {
      error = (e as Error).message;
    }
  const numeric = (
    label: string,
    key: "budget" | "shortlist" | "matches" | "simulations" | "seed" | "window",
    min: number,
    max: number,
  ) => (
    <label key={key}>
      {label}
      <input
        aria-label={label}
        type="number"
        min={min}
        max={max}
        value={c[key]}
        onChange={(e) => patch({ [key]: Number(e.target.value) })}
      />
    </label>
  );
  const pct = (n: number) => (n * 100).toFixed(4) + "%";
  return (
    <section className="research-card" aria-labelledby="innovation-title">
      <header>
        <div>
          <span className="research-kicker">COVERAGE & AUDIT</span>
          <h2 id="innovation-title">覆盖与审计实验室</h2>
        </div>
      </header>
      <p className="research-context">
        预算内的覆盖设计与软排序。来源：{input.historySource ?? "未标注"} ·{" "}
        {input.history?.length ?? 0}
        期。独立均匀模型下N个不同号码的精确覆盖概率=N/100000；结构评分与回捞不改变这个等式。
      </p>
      <div className="research-fields">
        <label>
          覆盖求解器
          <select
            aria-label="覆盖求解器"
            value={c.solver}
            onChange={(e) =>
              patch({ solver: e.target.value as InnovationConfig["solver"] })
            }
          >
            <option value="cover">边际覆盖贪心</option>
            <option value="entropy">熵正则松弛＋覆盖离散化</option>
            <option value="rank">加权软分排序</option>
            <option value="sample">加权无放回抽样</option>
          </select>
        </label>
        <label>
          覆盖条件策略
          <select
            aria-label="覆盖条件策略"
            value={c.rules}
            onChange={(e) =>
              patch({ rules: e.target.value as InnovationConfig["rules"] })
            }
          >
            <option value="hard">原条件严格全部满足</option>
            <option value="soft">原条件仅计软支持分</option>
          </select>
        </label>
        {numeric("覆盖注数预算", "budget", 1, 100)}
        {numeric("覆盖候选短名单", "shortlist", 16, 256)}
        <label>
          覆盖目标数字池
          <input
            aria-label="覆盖目标数字池"
            value={c.digits}
            onChange={(e) => patch({ digits: e.target.value })}
          />
        </label>
        {numeric("覆盖定位匹配数", "matches", 3, 5)}
        {numeric("覆盖历史窗口", "window", 40, 500)}
        <label>
          覆盖历史截止期
          <input
            aria-label="覆盖历史截止期"
            placeholder="留空为最新"
            value={c.referenceIssue ?? ""}
            onChange={(e) =>
              patch({ referenceIssue: e.target.value || undefined })
            }
          />
        </label>
        {numeric("覆盖实验随机种子", "seed", 0, 4294967295)}
        {numeric("覆盖MC样本数", "simulations", 100, 100000)}
      </div>
      <p className="research-context">
        目标域为数字池的五位笛卡尔积（最多8⁵组）。匹配3/4位是几何覆盖实验，排列五没有对应奖级；匹配5位才是精确相同。预算不足会给出未覆盖反例，不承诺中奖、最少注数或全局最优。排序模式取高分短名单；其余模式一半取高分、一半固定种子抽取，再求解。
      </p>
      {c.rules === "soft" && (
        <p className="notice">
          软支持模式：原条件失败不再阻止入选。Guard仍强制原始定位/外部大底、去重、预算；条件失败会作为异议保留。
        </p>
      )}
      <details>
        <summary>软特征权重与研究方法说明</summary>
        <div className="research-fields">
          {featureNames.map((name, i) => (
            <label key={name}>
              {name}
              <input
                type="number"
                aria-label={name + "权重"}
                min={0}
                max={10}
                step={0.1}
                value={c.weights[i]}
                onChange={(e) =>
                  patch({
                    weights: c.weights.map((v, j) =>
                      j === i ? Number(e.target.value) : v,
                    ),
                  })
                }
              />
            </label>
          ))}
        </div>
        <p className="research-context">
          分数为四项加权平均，不是概率。局部残差=相邻跳变平方特征与45邻居均值之差的绝对值；完整汉明图每节点45度，候选图稀疏度=1−可行邻居数/45，不是销量或市场拥挤。历史距离只用于结构比较。
        </p>
        <p className="research-context">
          熵正则方案是CPU均值场教学实现，最多512个目标场景优化偏好，再对完整目标域离散化和核验；没有接入GPU
          FEM。图特征未使用AnomalyGFM/SpaceGNN权重；审计角色是确定性模块，没有调用LLM。GP-UCB只试验软权重，不冒称MACO或防过拟合保证。
        </p>
      </details>
      <label className="research-context">
        <input
          aria-label="启用GP-UCB权重实验"
          type="checkbox"
          checked={c.tune}
          onChange={(e) => patch({ tune: e.target.checked })}
        />{" "}
        启用GP-UCB权重实验（12次，结构场景训练/验证，不使用未来开奖答案）
      </label>
      <label className="research-context">
        <input
          aria-label="启用同预算覆盖回捞"
          type="checkbox"
          checked={c.rescue}
          onChange={(e) => patch({ rescue: e.target.checked })}
        />{" "}
        同预算局部交换回捞（最多128次比较，只接受精确覆盖增加）
      </label>
      <div className="research-actions">
        <button disabled={busy} onClick={run}>
          运行覆盖与审计
        </button>
        {busy && (
          <button
            onClick={() => {
              serial.current++;
              worker.current?.terminate();
              worker.current = null;
              setBusy(false);
              setNotice("已取消覆盖实验；不采用部分结果");
            }}
          >
            取消覆盖实验
          </button>
        )}
      </div>
      {notice && <p role="status">{notice}</p>}
      {result && (
        <div aria-label="覆盖审计结果">
          <p className="research-context">
            原始{result.audit.base} → 硬条件{result.audit.hard} → 可行
            {result.audit.eligible} → 短名单{result.audit.shortlist} → 输出
            {result.numbers.length}/{c.budget}。历史{result.audit.historyStart}—
            {result.audit.historyEnd}。Guard：通过。{result.audit.stopReason}。
          </p>
          <div className="tolerance-box">
            <strong>
              精确枚举覆盖：{result.coverage.covered}/{result.coverage.total}（
              {pct(result.coverage.covered / result.coverage.total)}）
            </strong>
            <p>
              {result.coverage.guaranteed
                ? "指定目标域内全部满足定位匹配目标；这是有限集合认证。"
                : "未达到全覆盖；反例：" + result.coverage.witness}{" "}
              目标匹配{c.matches}位，目标数字池{c.digits}。
            </p>
          </div>
          <p>
            实际精确覆盖概率 {pct(result.risk.exactHit)}；全集排除质量{" "}
            {pct(result.risk.exactMiss)}。目标域条件精确覆盖{" "}
            {pct(result.risk.conditionalExact)}。
          </p>
          <p className="research-context">
            独立均匀MC：{result.risk.hits}/{result.risk.simulations}，估计
            {pct(result.risk.estimate)}，Wilson95% [
            {result.risk.wilson95.map(pct).join("，")}]。几何覆盖MC{" "}
            {pct(result.risk.geometryEstimate)}，Wilson95% [
            {result.risk.geometryWilson95.map(pct).join("，")}]
            。有限10万全集优先使用精确计数；MC零命中不等于零概率。
          </p>
          <p>
            回捞前几何覆盖{result.audit.beforeRescue}，交换
            {result.audit.rescues.length}次；
            {result.audit.rescues.length
              ? result.audit.rescues
                  .map(
                    (r) => r.removed + " → " + r.added + "，新增覆盖" + r.gain,
                  )
                  .join("；")
              : "本轮没有发现正增益交换"}
            。回捞不突破预算与当前硬约束。
          </p>
          <p aria-label="覆盖输出号码" className="research-context">
            {result.numbers.join("　") || "未产生可覆盖目标的组合"}
          </p>
          <label>
            查询号码决策
            <input
              aria-label="查询号码决策"
              maxLength={5}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          {error && <p className="notice">{error}</p>}
          {explanation && (
            <>
              <p>
                {explanation.number}：{explanation.stage}；
                {explanation.disagreement}。
              </p>
              <details>
                <summary>该号码的可复核决策记录</summary>
                <pre className="innovation-json">
                  {JSON.stringify(explanation, null, 2)}
                </pre>
              </details>
            </>
          )}
          {result.audit.tuning && (
            <details open>
              <summary>GP-UCB结构目标试验</summary>
              <p className="research-context">
                32个候选权重中主动试验12次。训练场景为目标域索引非5的倍数，保留每第5个场景作未参与调权的验证；验证只评价回捞前完整可行域Top-K策略，不评价后续覆盖求解器。验证覆盖
                {result.audit.weightValidation?.covered}/
                {result.audit.weightValidation?.total}
                。代理标准差不是中奖不确定性。
              </p>
              <div style={{ overflowX: "auto" }}>
                <table className="potential-table" aria-label="GP-UCB试验记录">
                  <thead>
                    <tr>
                      <th>试验</th>
                      <th>训练覆盖</th>
                      <th>代理均值</th>
                      <th>代理标准差</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.audit.tuning.trials.map((t, i) => (
                      <tr key={i}>
                        <td>{i + 1}</td>
                        <td>{pct(t.reward)}</td>
                        <td>{t.mean.toFixed(4)}</td>
                        <td>{t.sd.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          )}
          <details>
            <summary>完整运行参数、求解步骤与权重实验</summary>
            <pre className="innovation-json">
              {JSON.stringify(result.audit, null, 2)}
            </pre>
          </details>
          <p className="research-context">
            角色记录：Assessor独立计算条件支持，Judge计算软分，Selector记录边际覆盖，Refiner记录交换，Guard校验来源/预算/去重，Explainer按号查询。保留分歧，不把规则模块叫作多LLM共识。
          </p>
          <div className="research-actions">
            <button
              disabled={!result.numbers.length}
              onClick={() => {
                const next = {
                  ...input,
                  candidates: result.numbers,
                  rules: input.rules.map((r) => ({ ...r, enabled: false })),
                  combination: { mode: "strict" as const, minimum: 0 },
                };
                setUndo({
                  before: input,
                  applied: JSON.stringify({
                    ...next,
                    innovation: next.innovation ?? defaultInnovation,
                  }),
                });
                onChange(next);
              }}
            >
              载入大底并停用原条件
            </button>
            <button
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(
                    JSON.stringify(
                      {
                        input,
                        numbers: result.numbers,
                        coverage: result.coverage,
                        risk: result.risk,
                        audit: result.audit,
                      },
                      null,
                      2,
                    ),
                  );
                  setNotice("覆盖审计报告已复制");
                } catch {
                  setNotice("复制失败；仍可在页面查看完整记录");
                }
              }}
            >
              复制覆盖审计报告
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
          撤销本次载入
        </button>
      )}
    </section>
  );
}
