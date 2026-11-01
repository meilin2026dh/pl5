export function structure(number: string, threshold: number) {
  const d = [...number].map(Number),
    sorted = [...d].sort((a, b) => a - b),
    diffs = new Set<number>();
  for (let i = 0; i < 5; i++)
    for (let j = i + 1; j < 5; j++)
      if (d[i] !== d[j]) diffs.add(Math.abs(d[i] - d[j]));
  const gaps = sorted.slice(1).map((n, i) => n - sorted[i]);
  return {
    ac: diffs.size - 4,
    gaps,
    large: gaps.filter((n) => n >= threshold).length,
  };
}
