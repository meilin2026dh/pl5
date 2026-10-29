export interface Draw {
  issue: string;
  date: string;
  number: string;
}
export function parseHistoryCsv(text: string): Draw[] {
  const lines = text
    .replace(/^\uFEFF/, "")
    .trim()
    .split(/\r?\n/);
  if (lines.length < 2) throw new Error("CSV 至少需要表头和一条记录");
  const split = (line: string) => {
    const out: string[] = [];
    let value = "",
      quoted = false;
    for (let i = 0; i < line.length; i++) {
      const c = line[i];
      if (c === '"') {
        if (quoted && line[i + 1] === '"') {
          value += '"';
          i++;
        } else quoted = !quoted;
      } else if (c === "," && !quoted) {
        out.push(value.trim());
        value = "";
      } else value += c;
    }
    if (quoted) throw new Error("CSV 引号不完整");
    out.push(value.trim());
    return out;
  };
  const header = split(lines[0]);
  if (header.join(",") !== "issue,date,number")
    throw new Error("表头必须是 issue,date,number");
  const seen = new Set<string>();
  const dates = new Set<string>();
  return lines
    .slice(1)
    .map((line, i) => {
      const row = split(line);
      if (row.length !== 3) throw new Error(`第 ${i + 2} 行列数不正确`);
      const [issue, date, number] = row;
      if (!/^\d{1,20}$/.test(issue))
        throw new Error(`第 ${i + 2} 行期号须为 1–20 位数字`);
      if (
        !/^\d{4}-\d{2}-\d{2}$/.test(date) ||
        date < "1900-01-01" ||
        date > "2100-12-31" ||
        Number.isNaN(Date.parse(date)) ||
        new Date(date + "T00:00:00Z").toISOString().slice(0, 10) !== date
      )
        throw new Error(`第 ${i + 2} 行日期无效`);
      if (!/^\d{5}$/.test(number))
        throw new Error(`第 ${i + 2} 行号码必须为五位数字，保留前导零`);
      if (seen.has(issue)) throw new Error(`第 ${i + 2} 行期号重复：${issue}`);
      if (dates.has(date)) throw new Error(`第 ${i + 2} 行开奖日期重复`);
      seen.add(issue);
      dates.add(date);
      return { issue, date, number };
    })
    .sort((a, b) => a.date.localeCompare(b.date));
}
export function makeDemo(count = 200): Draw[] {
  let seed = 82917;
  return Array.from({ length: count }, (_, i) => {
    seed = (seed * 16807) % 2147483647;
    return {
      issue: `2026${String(i + 1).padStart(3, "0")}`,
      date: new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10),
      number: String(seed % 100000).padStart(5, "0"),
    };
  });
}
export function omissions(
  draws: Draw[],
  position: number,
  limit = draws.length,
) {
  const since = Array(10).fill(0) as number[],
    known = Array(10).fill(false) as boolean[];
  const output: { value: number; lowerBound: boolean }[][] = [];
  draws.forEach((draw, index) => {
    if (index > 0 && !isAdjacent(draws[index - 1], draw)) {
      since.fill(0);
      known.fill(false);
    }
    for (let digit = 0; digit < 10; digit++) {
      if (Number(draw.number[position]) === digit) {
        since[digit] = 0;
        known[digit] = true;
      } else since[digit]++;
    }
    if (index >= draws.length - limit)
      output.push(
        since.map((value, digit) => ({ value, lowerBound: !known[digit] })),
      );
  });
  return output;
}
export function historyCsv(draws: Draw[]) {
  return (
    "\uFEFFissue,date,number\r\n" +
    draws.map((d) => `${d.issue},${d.date},${d.number}`).join("\r\n")
  );
}
export function isAdjacent(a: Draw, b: Draw) {
  return Date.parse(b.date) - Date.parse(a.date) === 86400000;
}

export interface HistorySnapshot {
  draws: Draw[];
  source: string;
  sourceUrl?: string;
  updatedAt?: string;
  version?: string;
  stale?: boolean;
  warning?: string;
}
export interface HistoryRange {
  fromDate: string;
  toDate: string;
  fromIssue: string;
  toIssue: string;
}
export const emptyHistoryRange: HistoryRange = {
  fromDate: "",
  toDate: "",
  fromIssue: "",
  toIssue: "",
};
export function filterHistory(draws: Draw[], range: HistoryRange) {
  const compare = (a: string, b: string) =>
    BigInt(a) < BigInt(b) ? -1 : BigInt(a) > BigInt(b) ? 1 : 0;
  return draws.filter(
    (d) =>
      (!range.fromDate || d.date >= range.fromDate) &&
      (!range.toDate || d.date <= range.toDate) &&
      (!range.fromIssue || compare(d.issue, range.fromIssue) >= 0) &&
      (!range.toIssue || compare(d.issue, range.toIssue) <= 0),
  );
}
export function officialHistoryUrl(count: number) {
  if (![200, 500, 1000, 2000].includes(count))
    throw new Error("不支持的查询期数");
  return `/api/history?pages=${count / 100}`;
}
export function validateSnapshot(input: unknown): HistorySnapshot {
  const value = input as HistorySnapshot;
  if (
    !value ||
    !Array.isArray(value.draws) ||
    !value.draws.length ||
    typeof value.source !== "string"
  )
    throw new Error("历史数据响应格式无效");
  const draws = parseHistoryCsv(historyCsv(value.draws));
  return { ...value, draws };
}
function historyDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open("pl5-history", 1);
    request.onupgradeneeded = () =>
      request.result.createObjectStore("snapshots");
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
export async function readHistoryCache(): Promise<HistorySnapshot | undefined> {
  const db = await historyDatabase();
  try {
    return await new Promise((resolve, reject) => {
      const request = db
        .transaction("snapshots")
        .objectStore("snapshots")
        .get("current");
      request.onsuccess = () =>
        resolve(request.result ? validateSnapshot(request.result) : undefined);
      request.onerror = () => reject(request.error);
    });
  } finally {
    db.close();
  }
}
let cacheWrites = Promise.resolve();
export function writeHistoryCache(snapshot: HistorySnapshot): Promise<void> {
  const pending = cacheWrites
    .catch(() => {})
    .then(() => persistHistoryCache(snapshot));
  cacheWrites = pending;
  return pending;
}
async function persistHistoryCache(snapshot: HistorySnapshot): Promise<void> {
  const db = await historyDatabase();
  try {
    await new Promise<void>((resolve, reject) => {
      const transaction = db.transaction("snapshots", "readwrite");
      transaction.objectStore("snapshots").put(snapshot, "current");
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);
      transaction.onabort = () => reject(transaction.error);
    });
  } finally {
    db.close();
  }
}
