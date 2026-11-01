import { numberAt } from "./sets";
export function patterns(n: number) {
  const d = [...numberAt(n)].map(Number),
    out: number[] = [];
  let g = 0;
  for (let a = 0; a < 5; a++)
    for (let b = a + 1; b < 5; b++) out.push(g++ * 100 + d[a] * 10 + d[b]);
  g = 0;
  for (let a = 0; a < 5; a++)
    for (let b = a + 1; b < 5; b++)
      for (let c = b + 1; c < 5; c++)
        out.push(1000 + g++ * 1000 + d[a] * 100 + d[b] * 10 + d[c]);
  return out;
}
export function hypergraphCoverage(indices: number[]) {
  const covered = new Uint8Array(11000);
  for (const n of indices) for (const t of patterns(n)) covered[t] = 1;
  const pairs = covered.slice(0, 1000).reduce((a, b) => a + b, 0),
    triples = covered.slice(1000).reduce((a, b) => a + b, 0),
    missing: number[] = [];
  for (let i = 0; i < covered.length && missing.length < 20; i++)
    if (!covered[i]) missing.push(i);
  return {
    pairs: { covered: pairs, total: 1000 },
    triples: { covered: triples, total: 10000 },
    missing,
  };
}
export function diversify(
  ranked: number[],
  budget: number,
  onPick?: (n: number, stage: "hypergraph" | "rank-fill") => void,
) {
  const pool = ranked.slice(0, 512),
    covered = new Uint8Array(11000),
    chosen: number[] = [],
    used = new Set<number>(),
    cached = pool.map(patterns);
  for (let k = 0; k < Math.min(budget, 100, pool.length); k++) {
    let best = -1,
      gain = -1;
    for (let i = 0; i < pool.length; i++) {
      if (used.has(pool[i])) continue;
      const g = cached[i].reduce((a, t) => a + 1 - covered[t], 0);
      if (g > gain) {
        gain = g;
        best = i;
      }
    }
    if (best < 0) break;
    const n = pool[best];
    chosen.push(n);
    onPick?.(n, "hypergraph");
    used.add(n);
    cached[best].forEach((t) => (covered[t] = 1));
  }
  for (const n of ranked) {
    if (chosen.length >= budget) break;
    if (!used.has(n)) {
      chosen.push(n);
      onPick?.(n, "rank-fill");
      used.add(n);
    }
  }
  return chosen;
}
