export function differenceSignature(number: string): string {
  return [...number]
    .slice(1)
    .map((d, i) => Number(d) - Number(number[i]))
    .join(",");
}
