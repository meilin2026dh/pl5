export function haarPacket(x: number[], depth = 2): number[][] {
  let bands = [x];
  for (let level = 0; level < depth; level++) {
    bands = bands.flatMap((row) => {
      if (row.length % 2) throw Error("Haar小波包长度必须可被2的层数整除");
      const a: number[] = [],
        d: number[] = [];
      for (let i = 0; i < row.length; i += 2) {
        a.push((row[i] + row[i + 1]) / Math.SQRT2);
        d.push((row[i] - row[i + 1]) / Math.SQRT2);
      }
      return [a, d];
    });
  }
  return bands;
}
function energy(x: number[]) {
  const e = haarPacket(x).map((row) => row.reduce((s, v) => s + v * v, 0)),
    total = e.reduce((a, b) => a + b, 0);
  return e.map((v) => (total ? v / total : 0));
}
export function fitWavelet(rows: string[]) {
  const context = rows.slice(-15),
    profiles = Array.from({ length: 5 }, (_, p) => {
      const samples = Array.from({ length: rows.length - 15 }, (_, i) =>
        energy(rows.slice(i, i + 16).map((s) => Number(s[p]))),
      );
      const mean = Array.from(
          { length: 4 },
          (_, b) => samples.reduce((s, x) => s + x[b], 0) / samples.length,
        ),
        sd = mean.map((m, b) =>
          Math.sqrt(
            samples.reduce((s, x) => s + (x[b] - m) ** 2, 0) / samples.length,
          ),
        );
      return { mean, sd };
    }),
    penalties = profiles.map((f, p) =>
      Array.from({ length: 10 }, (_, d) => {
        const e = energy([...context.map((s) => Number(s[p])), d]),
          z = e.map((v, b) => (v - f.mean[b]) / Math.max(0.001, f.sd[b]));
        return {
          energy: e,
          z,
          penalty: z.reduce((s, v) => s + Math.min(25, v * v), 0) / 4,
          outside2Sigma: z.some((v) => Math.abs(v) > 2),
        };
      }),
    );
  return {
    score: (s: string) =>
      (-0.5 *
        [...s].reduce((v, d, p) => v + penalties[p][Number(d)].penalty, 0)) /
      5,
    context,
    profiles,
    penalties,
    parameterCount: 40,
    settings: {
      window: 16,
      depth: 2,
      wavelet: "orthonormal Haar",
      order: "natural aa/ad/da/dd",
      sdFloor: 0.001,
      z2Cap: 25,
    },
    note: "冻结训练末15条上下文，为候选末值计算4频带能量比例；所有留出段用同一上下文，不滚动偷用答案。不宣称2σ为多重校准风险，也不把数字当连续物理信号的假设视为已证实。",
  };
}
