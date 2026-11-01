import { logGamma } from "../research/models";
function fraction(a: number, b: number, x: number) {
  const tiny = 1e-300;
  let c = 1,
    d = 1 - ((a + b) * x) / (a + 1);
  if (Math.abs(d) < tiny) d = tiny;
  d = 1 / d;
  let h = d;
  for (let m = 1; m <= 200; m++) {
    for (const aa of [
      (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m)),
      (-(a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1)),
    ]) {
      d = 1 + aa * d;
      if (Math.abs(d) < tiny) d = tiny;
      c = 1 + aa / c;
      if (Math.abs(c) < tiny) c = tiny;
      d = 1 / d;
      const delta = d * c;
      h *= delta;
      if (aa < 0 && Math.abs(delta - 1) < 1e-12) return h;
    }
  }
  throw Error("Beta计算未收敛");
}
export function betaCDF(x: number, a: number, b: number) {
  if (![x, a, b].every(Number.isFinite) || a <= 0 || b <= 0 || x < 0 || x > 1)
    throw Error("Beta参数错误");
  if (x === 0 || x === 1) return x;
  const bt = Math.exp(
    logGamma(a + b) -
      logGamma(a) -
      logGamma(b) +
      a * Math.log(x) +
      b * Math.log1p(-x),
  );
  return Math.max(
    0,
    Math.min(
      1,
      x < (a + 1) / (a + b + 2)
        ? (bt * fraction(a, b, x)) / a
        : 1 - (bt * fraction(b, a, 1 - x)) / b,
    ),
  );
}
export function betaQuantile(p: number, a: number, b: number) {
  if (
    !Number.isFinite(p) ||
    p < 0 ||
    p > 1 ||
    !Number.isFinite(a) ||
    !Number.isFinite(b) ||
    a <= 0 ||
    b <= 0
  )
    throw Error("Beta分位参数错误");
  if (p === 0 || p === 1) return p;
  let lo = 0,
    hi = 1;
  for (let i = 0; i < 120; i++) {
    const mid = (lo + hi) / 2,
      v = betaCDF(mid, a, b);
    if (Math.abs(v - p) < 1e-10) return mid;
    if (v < p) lo = mid;
    else hi = mid;
  }
  throw Error("Beta逆CDF精度未达到要求");
}
