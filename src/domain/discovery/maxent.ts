function indices(s: string) {
  const d = [...s].map(Number),
    out = d.map((x, p) => p * 10 + x);
  let pair = 0;
  for (let p = 0; p < 5; p++)
    for (let q = p + 1; q < 5; q++)
      out.push(50 + pair++ * 100 + d[p] * 10 + d[q]);
  return out;
}
export function fitMaxent(rows: string[]) {
  const features = Array.from({ length: 100000 }, (_, i) =>
      Uint16Array.from(indices(String(i).padStart(5, "0"))),
    ),
    empirical = new Float64Array(1050),
    w = new Float64Array(1050),
    pmf = new Float64Array(100000),
    trace: number[] = [];
  for (const s of rows)
    for (const i of indices(s)) empirical[i] += 1 / rows.length;
  const distribution = () => {
    let max = -Infinity;
    for (let i = 0; i < 100000; i++) {
      pmf[i] = features[i].reduce((v, k) => v + w[k], 0);
      max = Math.max(max, pmf[i]);
    }
    let z = 0;
    for (let i = 0; i < 100000; i++) {
      pmf[i] = Math.exp(pmf[i] - max);
      z += pmf[i];
    }
    for (let i = 0; i < 100000; i++) pmf[i] /= z;
    return max + Math.log(z);
  };
  for (let iter = 0; iter < 12; iter++) {
    const logZ = distribution(),
      expected = new Float64Array(1050);
    for (let i = 0; i < 100000; i++)
      for (const k of features[i]) expected[k] += pmf[i];
    trace.push(
      logZ -
        w.reduce((s, x, k) => s + x * empirical[k], 0) +
        0.005 * w.reduce((s, x) => s + x * x, 0),
    );
    for (let k = 0; k < w.length; k++)
      w[k] += 0.5 * (empirical[k] - expected[k] - 0.01 * w[k]);
  }
  const logZ = distribution();
  return {
    prob: (s: string) => pmf[Number(s)],
    weights: Array.from(w),
    parameterCount: w.length,
    trace,
    logZ,
    settings: {
      iterations: 12,
      rate: 0.5,
      l2: 0.01,
      features: "50位置指示+10对位置×100数字对指示",
      partition: "全100000精确枚举",
    },
    note: "有限特征对数线性最大熵/正则似然模型；自动学习权重，不自动发现任意新特征或证明预测优势。",
  };
}
