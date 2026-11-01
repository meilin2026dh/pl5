export type TransportProfile = {
  inside: number[][];
  outside: number[][];
  mass: number[];
  size: number;
  total: number;
};
export function distancesTo(mask: Uint8Array, target: number, dimensions = 5) {
  const dist = new Uint8Array(mask.length).fill(255),
    queue = new Uint32Array(mask.length);
  let head = 0,
    tail = 0;
  for (let i = 0; i < mask.length; i++)
    if (mask[i] === target) {
      dist[i] = 0;
      queue[tail++] = i;
    }
  while (head < tail) {
    const x = queue[head++];
    for (let p = 1; p < 10 ** dimensions; p *= 10) {
      const old = Math.floor(x / p) % 10;
      for (let d = 0; d < 10; d++) {
        if (d === old) continue;
        const y = x + (d - old) * p;
        if (dist[y] === 255) {
          dist[y] = dist[x] + 1;
          queue[tail++] = y;
        }
      }
    }
  }
  return dist;
}
export function transportProfile(
  mask: Uint8Array,
  pmfs: Float64Array[],
  dimensions = 5,
): TransportProfile {
  const size = mask.reduce((a, b) => a + b, 0),
    di = distancesTo(mask, 0, dimensions),
    do_ = distancesTo(mask, 1, dimensions),
    inside = pmfs.map(() => Array(dimensions + 1).fill(0) as number[]),
    outside = pmfs.map(() => Array(dimensions + 1).fill(0) as number[]),
    mass = pmfs.map(() => 0);
  for (let x = 0; x < mask.length; x++)
    for (let m = 0; m < pmfs.length; m++) {
      if (mask[x]) {
        mass[m] += pmfs[m][x];
        if (di[x] !== 255) inside[m][di[x]] += pmfs[m][x];
      } else if (do_[x] !== 255) outside[m][do_[x]] += pmfs[m][x];
    }
  return {
    size,
    total: mask.length,
    mass: mass.map((x) => Math.min(1, x)),
    inside,
    outside,
  };
}
function movable(layers: number[], epsilon: number) {
  let moved = 0;
  for (let d = 1; d < layers.length; d++) {
    const v = Math.min(layers[d], epsilon / d);
    moved += v;
    epsilon = Math.max(0, epsilon - v * d);
  }
  return moved;
}
export function transportBounds(p: TransportProfile, epsilon: number) {
  return p.mass.map((mass, m) =>
    p.size === 0
      ? { nominal: 0, lower: 0, upper: 0 }
      : p.size === p.total
        ? { nominal: 1, lower: 1, upper: 1 }
        : {
            nominal: mass,
            lower: Math.max(0, mass - movable(p.inside[m], epsilon)),
            upper: Math.min(1, mass + movable(p.outside[m], epsilon)),
          },
  );
}
