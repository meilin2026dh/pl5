/** Mathematical classification: 0 and 1 are neither prime nor composite. */
export function digitClass(d: number): "P" | "C" | "N" {
  return [2, 3, 5, 7].includes(d) ? "P" : [4, 6, 8, 9].includes(d) ? "C" : "N";
}
export function gcd(a: number, b: number): number {
  while (b !== 0) [a, b] = [b, a % b];
  return a;
}
/** Explicit convention: any zero operand gives lcm 0, including lcm(0,0). */
export function lcm(a: number, b: number): number {
  return a === 0 || b === 0 ? 0 : (a / gcd(a, b)) * b;
}
export function inversionCount(d: number[]): number {
  let count = 0;
  for (let i = 0; i < d.length; i++)
    for (let j = i + 1; j < d.length; j++) if (d[i] > d[j]) count++;
  return count;
}
export function mathClassCounts(d: number[]): string {
  const counts = { P: 0, C: 0, N: 0 };
  for (const n of d) counts[digitClass(n)]++;
  return `${counts.P}:${counts.C}:${counts.N}`;
}
export function mathFeatures(number: string) {
  if (!/^\d{5}$/.test(number))
    throw new Error("请输入恰好五位数字，保留前导零");
  const d = [...number].map(Number),
    pattern = d.map(digitClass).join("");
  return {
    pattern,
    counts: mathClassCounts(d),
    sum: d.reduce((a, b) => a + b, 0),
    productTail: d.reduce((a, b) => (a * b) % 10, 1),
    inversions: inversionCount(d),
    gcd: d.reduce(gcd, 0),
    lcm: d.reduce(lcm, 1),
  };
}
