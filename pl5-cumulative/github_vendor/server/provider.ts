export type Draw = { issue: string; date: string; number: string };
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value))
    throw new Error("开奖响应格式不正确");
  return value as Record<string, unknown>;
}
export function parseOfficial(data: unknown): Draw[] {
  const root = object(data);
  if (root.success !== true)
    throw new Error("官方数据服务未成功返回，请稍后重试");
  const value = object(root.value);
  if (!Array.isArray(value.list) || value.list.length === 0)
    throw new Error("官方数据为空");
  return mergeDraws(
    value.list.map((raw) => {
      const row = object(raw);
      if (String(row.lotteryGameNum) !== "350133")
        throw new Error("数据彩种不匹配");
      const issue = String(row.lotteryDrawNum),
        date = String(row.lotteryDrawTime).slice(0, 10),
        number = String(row.lotteryDrawResult).replace(/\s+/g, "");
      if (
        !/^\d{1,20}$/.test(issue) ||
        !/^\d{5}$/.test(number) ||
        !/^\d{4}-\d{2}-\d{2}$/.test(date) ||
        Number.isNaN(Date.parse(date)) ||
        new Date(`${date}T00:00:00Z`).toISOString().slice(0, 10) !== date
      )
        throw new Error("官方数据包含无效期号、日期或号码");
      return { issue, date, number };
    }),
  );
}
export function mergeDraws(draws: Draw[]): Draw[] {
  const map = new Map<string, Draw>();
  const dates = new Map<string, string>();
  for (const draw of draws) {
    const previous = map.get(draw.issue);
    if (
      previous &&
      (previous.date !== draw.date || previous.number !== draw.number)
    )
      throw new Error(`期号${draw.issue}存在冲突记录`);
    if (dates.has(draw.date) && dates.get(draw.date) !== draw.issue)
      throw new Error("同日出现不同期号");
    map.set(draw.issue, draw);
    dates.set(draw.date, draw.issue);
  }
  return [...map.values()].sort((a, b) => a.date.localeCompare(b.date));
}
export const officialUrl =
  "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry";
export async function officialHistory(pages = 2): Promise<Draw[]> {
  if (!Number.isInteger(pages) || pages < 1 || pages > 20)
    throw new Error("查询范围为1至20页，每页最多100期");
  const result: Draw[] = [];
  for (let page = 1; page <= pages; page++) {
    const url = new URL(officialUrl);
    for (const [key, value] of Object.entries({
      gameNo: "350133",
      provinceId: "0",
      pageSize: "100",
      isVerify: "1",
      pageNo: String(page),
    }))
      url.searchParams.set(key, value);
    const response = await fetch(url, {
      signal: AbortSignal.timeout(15000),
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error(`官方数据服务响应${response.status}`);
    const text = await response.text();
    if (text.length > 4 * 1024 * 1024) throw new Error("官方响应超过限制");
    const draws = parseOfficial(JSON.parse(text));
    result.push(...draws);
    if (draws.length < 100) break;
  }
  return mergeDraws(result);
}
