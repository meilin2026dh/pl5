export function parseCandidates(text: string): string[] {
  if (new Blob([text]).size > 10 * 1024 * 1024)
    throw new Error("号码文件不可超过10MiB");
  const tokens = text
    .replace(/^\uFEFF/, "")
    .trim()
    .split(/[\s,，;；|]+/);
  if (!text.trim()) throw new Error("号码内容不能为空");
  if (tokens.length > 1000000) throw new Error("号码记录不可超过100万条");
  const invalid = tokens.findIndex((n) => !/^\d{5}$/.test(n));
  if (invalid >= 0)
    throw new Error(
      `第${invalid + 1}项不是五位号码：${tokens[invalid].slice(0, 20)}。请保留前导零。`,
    );
  return [...new Set(tokens)].sort();
}
export type SetOperation =
  "intersection" | "union" | "difference" | "symmetric";
export function setOperation(
  a: string[],
  b: string[],
  op: SetOperation,
): string[] {
  const A = new Set(a),
    B = new Set(b);
  let out: string[];
  switch (op) {
    case "intersection":
      out = [...A].filter((n) => B.has(n));
      break;
    case "union":
      out = [...new Set([...A, ...B])];
      break;
    case "difference":
      out = [...A].filter((n) => !B.has(n));
      break;
    case "symmetric":
      out = [...A]
        .filter((n) => !B.has(n))
        .concat([...B].filter((n) => !A.has(n)));
      break;
    default:
      throw new Error("未知集合操作");
  }
  return out.sort();
}
