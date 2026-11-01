import { betaQuantile } from "../lab/beta";
export function uncertainty(rows: string[], delta: number, risk: number) {
  if (
    !Number.isFinite(delta) ||
    delta < 0 ||
    delta > 0.09 ||
    !Number.isFinite(risk) ||
    risk < 0.001 ||
    risk > 0.2
  )
    throw Error("不确定性参数超限");
  const counts = Array.from({ length: 5 }, () => Array(10).fill(0) as number[]);
  for (const s of rows) for (let p = 0; p < 5; p++) counts[p][Number(s[p])]++;
  const cells = counts.flatMap((r, p) =>
    r.map((n, d) => {
      const a = n + 1,
        b = rows.length - n + 9,
        low = betaQuantile(risk / 100, a, b),
        high = betaQuantile(1 - risk / 100, a, b),
        state =
          low > 0.1 + delta
            ? "high"
            : high < 0.1 - delta
              ? "low"
              : "insufficient";
      return {
        position: p,
        digit: d,
        count: n,
        mean: a / (a + b),
        low,
        high,
        state,
      };
    }),
  );
  return {
    cells,
    delta,
    risk,
    prior: 1,
    score: (s: string) =>
      [...s].reduce((v, d, p) => {
        const c = cells[p * 10 + Number(d)];
        return v + (c.state === "insufficient" ? 0 : Math.log(c.mean / 0.1));
      }, 0),
    policy:
      "50个边缘区间用联合界分配后验尾风险；给定IID和Dirichlet先验，非频率学FDR。证据不足软分为0，绝不硬删除。",
  };
}
