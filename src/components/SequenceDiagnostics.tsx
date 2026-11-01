import type { fitSequence } from "../domain/selection/sequence";
type D = ReturnType<typeof fitSequence>["diagnostics"];
export default function SequenceDiagnostics({
  value,
}: {
  value: Record<string, unknown>;
}) {
  const d = value as D;
  if (!["lstm", "transformer"].includes(d.kind)) return null;
  const hi = Math.max(
    Math.log(10),
    ...d.curves.flatMap((x) => [x.train, x.validation]),
  );
  return (
    <div aria-label="时序模型训练诊断">
      <h3>{d.model}</h3>
      <p className="research-context">
        {d.parameters}参数 · 上下文{d.context}期 · 实际{d.epochs}轮 · 最佳验证轮
        {d.bestEpoch}。训练{d.training.join("—")}；验证{d.validation.join("—")}
        ；诊断{d.diagnostic.join("—")}
        。样本{d.samples.train}/{d.samples.validation}/{d.samples.diagnostic}
        （训练/验证/诊断），种子{d.seed}
        。以下损失均为每位置平均，整注log损失为其5倍。
      </p>
      <svg
        viewBox="0 0 400 160"
        style={{ width: "100%", maxWidth: 500 }}
        role="img"
        aria-label="时序训练验证损失曲线"
      >
        <path d="M25 10V130H390" fill="none" stroke="#c7b8a9" />
        {["train", "validation"].map((k, i) => (
          <polyline
            key={k}
            fill="none"
            stroke={i ? "#4d9687" : "#f07831"}
            strokeWidth="2"
            points={d.curves
              .map(
                (r, j) =>
                  `${25 + (j / Math.max(1, d.curves.length - 1)) * 360},${130 - (r[k as "train" | "validation"] / hi) * 115}`,
              )
              .join(" ")}
          />
        ))}
        <text x="25" y="151" fontSize="11">
          橙：训练 · 绿：验证 · 横轴epoch，纵轴log loss
        </text>
      </svg>
      <p>
        锁定重拟合模型的时间外损失{d.diagnosticLoss.toFixed(5)}，均匀
        {d.uniformLoss.toFixed(5)}；Brier {d.diagnosticBrier.toFixed(5)}
        ，均匀0.9。验证锁定的均匀收缩权重{d.mixture.weight}，其诊断损失
        {d.mixture.diagnostic.loss.toFixed(5)}；不据最终结果选权重。
      </p>
      <p className="research-context">
        本次选号按原始模型评分，混合仅作研究对照。固定对照（不按诊断择优）：
        {d.mixture.comparisons
          .filter((x) => [0, 0.5, 1].includes(x.weight))
          .map(
            (x) =>
              `λ${x.weight}：loss ${x.loss.toFixed(5)} / Brier ${x.brier.toFixed(5)}`,
          )
          .join("；")}
      </p>
      <p className="research-context">
        嵌入/主体/输出层参数变动总量：{d.changed.embedding.toFixed(5)} /{" "}
        {d.changed.body.toFixed(5)} / {d.changed.head.toFixed(5)}。{d.identity}
      </p>
      {d.kind === "transformer" && (
        <details>
          <summary>最近上下文注意力（非因果解释）</summary>
          <p className="research-context">
            各位置最后已观察token对上下文的归一权重；不是开奖号概率或关键期次证据。
          </p>
          {d.attention.map((rows, p) => (
            <p key={p} className="research-context">
              {"万千百十个"[p]}位：
              {rows
                .at(-1)!
                .map((x) => (x * 100).toFixed(1) + "%")
                .join(" / ")}
            </p>
          ))}
        </details>
      )}
    </div>
  );
}
