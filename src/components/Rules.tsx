import { useState } from "react";
import { Info, SlidersHorizontal } from "lucide-react";
import { ruleLabels, type Rule, type RuleKind } from "../domain/pick5";
const options: Partial<Record<RuleKind, (number | string)[]>> = {
  sum: Array.from({ length: 46 }, (_, i) => i),
  tail: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  span: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  odd: [0, 1, 2, 3, 4, 5],
  big: [0, 1, 2, 3, 4, 5],
  prime: [0, 1, 2, 3, 4, 5],
  distinct: [1, 2, 3, 4, 5],
  repeat: ["11111", "2111", "221", "311", "32", "41", "5"],
  consecutive: [0, 1, 2, 3, 4],
  sumMod3: [0, 1, 2],
  dan: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  kill: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
};
const hints: Partial<Record<RuleKind, string>> = {
  sum: "五位数字相加，范围0–45；可选择多个和值。",
  tail: "和值除以10的余数。例如00127的和值10，和尾0。",
  span: "最大数字减最小数字。例如00127的跨度为7。",
  odd: "奇数为1、3、5、7、9。比例按奇:偶。",
  big: "大数为5–9，小数为0–4。比例按大:小。",
  prime: "彩票分类约定：质类12357，合类04689；并非数学素数定义。",
  distinct: "五位中不同数字的种数，重复出现只计一次。",
  repeat: "数字出现次数降序。例如00127是2111，00112是221。",
  consecutive: "去重排序后差1的相邻对数；34579为2，9与0不相邻。",
  sumMod3: "五位和值除以3的余数，与每个数字的012路不同。",
  dan: "所选数字至少出现一个；重复出现仍只算一种。",
  kill: "保留模式要求所有所选数字均不出现；排除模式取相反集合。",
};
const groups = [
  { name: "基础数值", kinds: ["sum", "tail", "span", "sumMod3"] },
  {
    name: "号码形态",
    kinds: ["odd", "big", "prime", "repeat", "distinct", "consecutive"],
  },
  { name: "胆码与杀号", kinds: ["dan", "kill"] },
] as const;
export default function Rules({
  rules,
  onChange,
}: {
  rules: Rule[];
  onChange: (rules: Rule[]) => void;
}) {
  const [tab, setTab] = useState(0);
  const [help, setHelp] = useState<RuleKind | null>(null);
  const patch = (id: string, change: Partial<Rule>) =>
    onChange(rules.map((r) => (r.id === id ? { ...r, ...change } : r)));
  return (
    <section className="card rules-card">
      <div className="section-head">
        <h2>
          <SlidersHorizontal size={18} />
          过滤条件{" "}
          <span className="count-badge">
            {rules.filter((r) => r.enabled).length}
          </span>
        </h2>
        <button
          className="text-button"
          onClick={() =>
            onChange(rules.map((r) => ({ ...r, enabled: false, values: [] })))
          }
        >
          清空条件
        </button>
      </div>
      <div className="rule-tabs" role="tablist" aria-label="规则类别">
        {groups.map((g, i) => (
          <button
            key={g.name}
            role="tab"
            aria-selected={tab === i}
            onClick={() => setTab(i)}
          >
            {g.name}
          </button>
        ))}
      </div>
      <div className="rule-list">
        {rules
          .filter((r) =>
            (groups[tab].kinds as readonly string[]).includes(r.kind),
          )
          .map((r) => (
            <div
              className={"rule-item " + (r.enabled ? "enabled" : "")}
              key={r.id}
            >
              <div className="rule-top">
                <label className="check-label">
                  <input
                    type="checkbox"
                    checked={r.enabled}
                    onChange={(e) => patch(r.id, { enabled: e.target.checked })}
                  />
                  {ruleLabels[r.kind]}
                </label>
                <button
                  aria-label={`${ruleLabels[r.kind]}说明`}
                  className="info-button"
                  onClick={() => setHelp(help === r.kind ? null : r.kind)}
                >
                  <Info size={14} />
                </button>
                <input
                  className="group-input"
                  aria-label={`${ruleLabels[r.kind]}规则组`}
                  placeholder="独立条件"
                  value={r.group ?? ""}
                  onChange={(e) =>
                    patch(r.id, { group: e.target.value.trim() || undefined })
                  }
                />
                <select
                  aria-label={`${ruleLabels[r.kind]}筛选模式`}
                  value={r.mode}
                  onChange={(e) =>
                    patch(r.id, { mode: e.target.value as Rule["mode"] })
                  }
                >
                  <option value="include">保留选中</option>
                  <option value="exclude">排除选中</option>
                </select>
              </div>
              {help === r.kind && <p className="rule-help">{hints[r.kind]}</p>}
              <div className="rule-values">
                {options[r.kind]!.map((v) => (
                  <button
                    key={v}
                    className={r.values.includes(v) ? "active" : ""}
                    aria-pressed={r.values.includes(v)}
                    aria-label={`${ruleLabels[r.kind]} ${v}`}
                    onClick={() =>
                      patch(r.id, {
                        enabled: true,
                        values: r.values.includes(v)
                          ? r.values.filter((x) => x !== v)
                          : [...r.values, v],
                      })
                    }
                  >
                    {["odd", "big", "prime"].includes(r.kind)
                      ? `${v}:${5 - Number(v)}`
                      : v}
                  </button>
                ))}
              </div>
              {r.kind === "dan" && (
                <div className="dan-range">
                  <label>
                    最少命中种数
                    <select
                      aria-label="胆码最少命中种数"
                      value={r.params?.countMin ?? 1}
                      onChange={(e) =>
                        patch(r.id, {
                          params: {
                            ...r.params,
                            countMin: Number(e.target.value),
                          },
                        })
                      }
                    >
                      {[0, 1, 2, 3, 4, 5].map((n) => (
                        <option value={n} key={n}>
                          {n}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    最多命中种数
                    <select
                      aria-label="胆码最多命中种数"
                      value={r.params?.countMax ?? 5}
                      onChange={(e) =>
                        patch(r.id, {
                          params: {
                            ...r.params,
                            countMax: Number(e.target.value),
                          },
                        })
                      }
                    >
                      {[0, 1, 2, 3, 4, 5].map((n) => (
                        <option value={n} key={n}>
                          {n}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              )}
              {r.enabled && r.values.length === 0 && (
                <small className="validation">
                  请选择至少一项，或关闭此条件
                </small>
              )}
            </div>
          ))}
      </div>
      <p className="panel-note">不同条件同时满足 · 同一条件多选匹配任意一项</p>
    </section>
  );
}
