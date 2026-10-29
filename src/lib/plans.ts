import { validateInput, type FilterInput } from "../domain/pick5";
export type Plan = {
  id: string;
  name: string;
  createdAt: string;
  input: FilterInput;
};
export function decodePlans(raw: string): Plan[] {
  const data: unknown = JSON.parse(raw);
  if (
    !data ||
    typeof data !== "object" ||
    !("schemaVersion" in data) ||
    data.schemaVersion !== 1 ||
    !("plans" in data) ||
    !Array.isArray(data.plans)
  )
    throw new Error("方案数据版本不兼容，请先导出备份或重置本机方案。");
  const plans = data.plans;
  if (plans.length > 100) throw new Error("最多保存100个方案");
  for (const p of plans) {
    if (
      !p ||
      typeof p !== "object" ||
      typeof p.id !== "string" ||
      typeof p.name !== "string" ||
      !p.name.trim() ||
      p.name.length > 60 ||
      typeof p.createdAt !== "string" ||
      Number.isNaN(Date.parse(p.createdAt))
    )
      throw new Error("方案数据损坏");
    validateInput(p.input);
  }
  if (new Set(plans.map((p) => p.id)).size !== plans.length)
    throw new Error("方案ID重复");
  return plans;
}
export function encodePlan(name: string, input: FilterInput): Plan {
  validateInput(input);
  name = name.trim();
  if (!name || name.length > 60) throw new Error("方案名称需为1–60个字符");
  return {
    id: crypto.randomUUID(),
    name,
    createdAt: new Date().toISOString(),
    input: JSON.parse(JSON.stringify(input)),
  };
}
export const plansKey = "pl5.plans.v1";
export function writePlans(plans: Plan[]) {
  const raw = JSON.stringify({ schemaVersion: 1, plans });
  decodePlans(raw);
  localStorage.setItem(plansKey, raw);
}
export function download(
  name: string,
  text: string,
  type = "text/plain;charset=utf-8",
) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
