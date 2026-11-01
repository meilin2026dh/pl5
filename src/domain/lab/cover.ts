export type CoverConfig = {
  mode: "min" | "max";
  budget: number;
  radius: number;
  nodes: number;
  milliseconds: number;
};
const pop = (v: bigint) => {
  let n = 0;
  while (v) {
    v &= v - 1n;
    n++;
  }
  return n;
};
const hamming = (a: string, b: string) =>
  [...a].filter((d, i) => d !== b[i]).length;
export function solveCover(
  candidateInput: string[],
  targetInput: string[],
  c: CoverConfig,
  clock: () => number = () => performance.now(),
) {
  const candidates = [...new Set(candidateInput)].sort(),
    targets = [...new Set(targetInput)].sort();
  if (
    candidates.some((n) => !/^\d{5}$/.test(n)) ||
    targets.some((n) => !/^\d{5}$/.test(n)) ||
    candidates.length > 32 ||
    targets.length > 256 ||
    !["min", "max"].includes(c.mode) ||
    !Number.isInteger(c.budget) ||
    c.budget < 0 ||
    c.budget > 32 ||
    !Number.isInteger(c.radius) ||
    c.radius < 0 ||
    c.radius > 5 ||
    !Number.isInteger(c.nodes) ||
    c.nodes < 1 ||
    c.nodes > 1000000 ||
    !Number.isFinite(c.milliseconds) ||
    c.milliseconds < 1 ||
    c.milliseconds > 5000
  )
    throw Error("有限覆盖配置或规模错误（最多32候选/256目标）");
  const start = clock(),
    full = (1n << BigInt(targets.length)) - 1n,
    allMasks = candidates.map((n) =>
      targets.reduce(
        (s, t, j) => (hamming(n, t) <= c.radius ? s | (1n << BigInt(j)) : s),
        0n,
      ),
    );
  // Equal-cost subset columns can be replaced by a superset without losing a cover.
  const indices = candidates
      .map((_, i) => i)
      .filter(
        (i) =>
          allMasks[i] !== 0n &&
          !allMasks.some(
            (m, j) =>
              i !== j &&
              (allMasks[i] | m) === m &&
              (allMasks[i] !== m || j < i),
          ),
      ),
    masks = indices.map((i) => allMasks[i]),
    suffix = Array<bigint>(masks.length + 1).fill(0n);
  for (let i = masks.length - 1; i >= 0; i--)
    suffix[i] = suffix[i + 1] | masks[i];
  let greedy: number[] = [],
    covered = 0n;
  while (greedy.length < c.budget && covered !== full) {
    let best = -1,
      gain = 0;
    for (let i = 0; i < masks.length; i++)
      if (!greedy.includes(i)) {
        const g = pop(masks[i] & ~covered);
        if (g > gain) {
          gain = g;
          best = i;
        }
      }
    if (best < 0) break;
    greedy.push(best);
    covered |= masks[best];
  }
  let incumbent: number[] | null =
      c.mode === "max" || covered === full ? greedy : null,
    best = c.mode === "max" ? pop(covered) : (incumbent?.length ?? Infinity);
  type Node = { i: number; covered: bigint; selected: number[]; bound: number };
  const bound = (i: number, v: bigint, s: number) => {
    const left = c.budget - s,
      uncovered = full & ~v;
    if (c.mode === "max") {
      let mg = 0;
      for (let j = i; j < masks.length; j++)
        mg = Math.max(mg, pop(masks[j] & uncovered));
      return pop(v) + Math.min(pop(suffix[i] & uncovered), left * mg);
    }
    if ((v | suffix[i]) !== full) return Infinity;
    let max = 0;
    for (let j = i; j < masks.length; j++)
      max = Math.max(max, pop(masks[j] & uncovered));
    return uncovered === 0n
      ? s
      : max
        ? s + Math.ceil(pop(uncovered) / max)
        : Infinity;
  };
  const stack: Node[] = [
    { i: 0, covered: 0n, selected: [], bound: bound(0, 0n, 0) },
  ];
  let nodes = 0,
    stop = "complete";
  while (stack.length) {
    if (nodes >= c.nodes) {
      stop = "node-limit";
      break;
    }
    if (clock() - start >= c.milliseconds) {
      stop = "time-limit";
      break;
    }
    const n = stack.pop()!;
    nodes++;
    if (
      c.mode === "min" ? n.bound >= best || n.bound > c.budget : n.bound <= best
    )
      continue;
    const value = c.mode === "min" ? n.selected.length : pop(n.covered);
    if (
      (c.mode === "max" && value > best) ||
      (c.mode === "min" && n.covered === full && value < best)
    ) {
      best = value;
      incumbent = n.selected;
    }
    if (
      n.i >= masks.length ||
      n.selected.length >= c.budget ||
      (c.mode === "min" && n.covered === full)
    )
      continue;
    for (const take of [false, true]) {
      const selected = take ? n.selected.concat(n.i) : n.selected,
        v = take ? n.covered | masks[n.i] : n.covered,
        b = bound(n.i + 1, v, selected.length);
      if (c.mode === "min" ? b < best && b <= c.budget : b > best)
        stack.push({ i: n.i + 1, covered: v, selected, bound: b });
    }
  }
  const relevant = stack.filter((n) =>
      c.mode === "min" ? n.bound < best && n.bound <= c.budget : n.bound > best,
    ),
    proven = !relevant.length,
    objective = Number.isFinite(best) ? best : null,
    globalBound = proven
      ? objective
      : c.mode === "min"
        ? Math.min(best, ...relevant.map((n) => n.bound))
        : Math.max(best, ...relevant.map((n) => n.bound)),
    status = proven
      ? incumbent
        ? "OPTIMAL"
        : "INFEASIBLE"
      : incumbent
        ? "FEASIBLE_LIMIT"
        : "UNKNOWN_LIMIT",
    numbers = (incumbent ?? []).map((i) => candidates[indices[i]]),
    uncovered = targets.filter(
      (t) => !numbers.some((n) => hamming(n, t) <= c.radius),
    ),
    coveredCount = targets.length - uncovered.length;
  return {
    solver: "TypeScript有限域分支定界-v1",
    status,
    candidates,
    targets,
    config: c,
    numbers,
    objective,
    bound: globalBound,
    gap:
      objective === null || globalBound === null
        ? null
        : Math.abs(objective - globalBound),
    nodes,
    elapsed: clock() - start,
    stop: proven ? "complete" : stop,
    covered: coveredCount,
    uncovered,
    exactProbability: numbers.length / 100000,
    columnsAfterDominance: indices.length,
    certified: c.mode === "max" || uncovered.length === 0,
  };
}
