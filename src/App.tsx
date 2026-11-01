import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowUpRight,
  CheckCircle2,
  FolderOpen,
  BookOpen,
  LayoutGrid,
  ChartNoAxesCombined,
  Plus,
  Trash2,
  Download,
  Upload,
  X,
  ArrowRight,
} from "lucide-react";
import Workbench from "./pages/Workbench";
import History from "./pages/History";
import { explanations } from "./components/AdvancedRules";
import { makeDemo } from "./lib/history";
import {
  defaultPositions,
  defaultRules,
  type FilterInput,
  type Rule,
  ruleLabels,
} from "./domain/pick5";
import {
  decodePlans,
  encodePlan,
  writePlans,
  plansKey,
  download,
  type Plan,
} from "./lib/plans";
const nav = [
  { path: "/workbench", name: "缩水工作台", Icon: LayoutGrid },
  { path: "/history", name: "历史走势", Icon: ChartNoAxesCombined },
  { path: "/plans", name: "我的方案", Icon: FolderOpen },
  { path: "/help", name: "使用指南", Icon: BookOpen },
];
export default function App() {
  const [path, setPath] = useState(
    location.pathname === "/" ? "/workbench" : location.pathname,
  );
  const [historyVisited, setHistoryVisited] = useState(
    location.pathname === "/history",
  );
  useEffect(() => {
    if (path === "/history") setHistoryVisited(true);
  }, [path]);
  const [workbenchVersion, setWorkbenchVersion] = useState(0);
  const [input, setInput] = useState<FilterInput>(() => ({
    positions: defaultPositions(),
    rules: defaultRules(),
    history: makeDemo(),
    historySource: "演示数据 · 非真实开奖",
  }));
  const [plans, setPlans] = useState<Plan[]>([]),
    [storageError, setStorageError] = useState(""),
    [toast, setToast] = useState(""),
    [saveOpen, setSaveOpen] = useState(false),
    [planName, setPlanName] = useState("我的筛选方案"),
    [saveError, setSaveError] = useState("");
  const plansRef = useRef(plans);
  plansRef.current = plans;
  const historyData = useCallback(
    (draws: import("./lib/history").Draw[], source: string) => {
      setInput((prev) =>
        JSON.stringify(prev.history) === JSON.stringify(draws) &&
        prev.historySource === source
          ? prev
          : { ...prev, history: draws, historySource: source },
      );
    },
    [],
  );
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const file = useRef<HTMLInputElement>(null);
  const nameField = useRef<HTMLInputElement>(null);
  const modal = useRef<HTMLElement>(null);
  const notify = (s: string) => {
    setToast(s);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setToast(""), 4000);
  };
  useEffect(() => {
    try {
      const raw = localStorage.getItem(plansKey);
      if (raw) setPlans(decodePlans(raw));
    } catch (e) {
      setStorageError(
        `本机方案未能读取：${(e as Error).message}。原数据已保留，可先下载备份。`,
      );
    }
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);
  useEffect(() => {
    const onPop = () =>
      setPath(location.pathname === "/" ? "/workbench" : location.pathname);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  useEffect(() => {
    if (!saveOpen) return;
    const previousFocus = document.activeElement as HTMLElement | null;
    nameField.current?.focus();
    const trap = (event: KeyboardEvent) => {
      if (event.key !== "Tab") return;
      const controls = modal.current?.querySelectorAll<HTMLElement>(
        'button:not(:disabled),input:not(:disabled),select:not(:disabled),[tabindex="0"]',
      );
      if (!controls?.length) return;
      const first = controls[0],
        last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", trap);
    return () => {
      document.removeEventListener("keydown", trap);
      previousFocus?.focus();
    };
  }, [saveOpen]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSaveOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const go = (p: string) => {
    history.pushState({}, "", p);
    setPath(p);
    window.scrollTo?.(0, 0);
  };
  const persist = (next: Plan[]) => {
    if (storageError) {
      notify("请先备份并重置损坏的本机方案数据");
      return false;
    }
    try {
      writePlans(next);
      plansRef.current = next;
      setPlans(next);
      return true;
    } catch (e) {
      notify(`保存失败：${(e as Error).message}`);
      return false;
    }
  };
  const save = () => {
    try {
      const p = encodePlan(planName, input);
      if (persist([p, ...plans])) {
        setSaveOpen(false);
        setSaveError("");
        notify("方案已保存到本机");
      }
    } catch (e) {
      setSaveError((e as Error).message);
    }
  };
  const restore = (p: Plan) => {
    const saved = p.input;
    const currentRules = [
      ...saved.rules,
      ...defaultRules().filter(
        (r) => !saved.rules.some((s) => s.kind === r.kind),
      ),
    ];
    setInput({
      ...saved,
      positions: saved.positions.map((p) => [...p]),
      rules: currentRules.map((r) => ({
        ...r,
        id: crypto.randomUUID(),
        values: [...r.values],
      })),
    });
    go("/workbench");
    notify(`已载入「${p.name}」`);
  };
  const apply = (rules: Rule[]) => {
    setInput((prev) => ({
      ...prev,
      rules: [
        ...prev.rules.filter(
          (r) => r.enabled || !rules.some((s) => s.kind === r.kind),
        ),
        ...rules,
      ],
    }));
    go("/workbench");
    notify("走势条件已加入，请核对后开始缩水");
  };
  return (
    <>
      <header className="site-header">
        <div className="header-inner">
          <a
            className="brand"
            href="/workbench"
            onClick={(e) => {
              e.preventDefault();
              go("/workbench");
            }}
            aria-label="五序首页"
          >
            <span className="brand-mark">
              <i />
              <i />
              <i />
              <i />
              <i />
            </span>
            <strong>五序</strong>
            <span className="brand-en">WUXU</span>
          </a>
          <nav aria-label="主导航">
            {nav.map(({ path: p, name, Icon }) => (
              <a
                key={p}
                href={p}
                className={path === p ? "active" : ""}
                aria-current={path === p ? "page" : undefined}
                onClick={(e) => {
                  if (e.ctrlKey || e.metaKey) return;
                  e.preventDefault();
                  go(p);
                }}
              >
                <Icon size={15} />
                {name}
              </a>
            ))}
          </nav>
          <span className="header-tag">
            <span className="green-dot" /> 浏览器本地计算
          </span>
          <div className="avatar">W</div>
        </div>
      </header>
      <main className="main-container">
        <div hidden={path !== "/workbench"}>
          <Workbench
            key={workbenchVersion}
            input={input}
            setInput={setInput}
            onSave={() => {
              setSaveError("");
              setSaveOpen(true);
            }}
            notify={notify}
          />
        </div>
        <div hidden={path !== "/history"}>
          {(historyVisited || path === "/history") && (
            <History onApply={apply} onDataChange={historyData} />
          )}
        </div>
        {path === "/plans" && (
          <>
            <div className="title-row">
              <div>
                <div className="eyebrow">把思路，好好收藏</div>
                <h1>
                  我的<span>方案库。</span>
                </h1>
                <p className="muted">
                  保存常用条件，下次从这里继续。方案仅保存在当前浏览器。
                </p>
              </div>
              <div className="head-actions">
                <button
                  className="button secondary"
                  onClick={() => file.current?.click()}
                >
                  <Upload size={16} />
                  导入 JSON
                </button>
                <button
                  className="button primary"
                  onClick={() => {
                    setInput((previous) => ({
                      positions: defaultPositions(),
                      rules: defaultRules(),
                      history: previous.history,
                      historySource: previous.historySource,
                    }));
                    setWorkbenchVersion((version) => version + 1);
                    setPlanName("我的筛选方案");
                    go("/workbench");
                  }}
                >
                  <Plus size={16} />
                  新建方案
                </button>
              </div>
            </div>
            <input
              type="file"
              ref={file}
              accept=".json,application/json"
              hidden
              onChange={async (e) => {
                const f = e.target.files?.[0];
                if (!f) return;
                try {
                  if (f.size > 10 * 1048576)
                    throw new Error("方案文件不可超过10MiB");
                  const incoming = decodePlans(await f.text());
                  const fresh = incoming.filter(
                    (p) => !plansRef.current.some((x) => x.id === p.id),
                  );
                  if (persist([...fresh, ...plansRef.current]))
                    notify(`已导入 ${fresh.length} 个方案`);
                } catch (err) {
                  notify(`导入失败：${(err as Error).message}`);
                } finally {
                  e.target.value = "";
                }
              }}
            />
            {storageError && (
              <div className="error-box" role="alert">
                {storageError}
                <div className="head-actions">
                  <button
                    onClick={() => {
                      try {
                        download(
                          "pl5-原始方案备份.json",
                          localStorage.getItem(plansKey) ?? "",
                        );
                      } catch {
                        notify("备份读取失败");
                      }
                    }}
                  >
                    下载原始备份
                  </button>
                  <button
                    onClick={() => {
                      if (confirm("请确认已备份。重置将清除本机方案存储。")) {
                        try {
                          localStorage.removeItem(plansKey);
                          setStorageError("");
                          setPlans([]);
                        } catch {
                          notify("重置失败");
                        }
                      }
                    }}
                  >
                    重置本机方案
                  </button>
                </div>
              </div>
            )}
            {plans.length ? (
              <div className="plans-grid">
                {plans.map((p) => (
                  <article className="card plan-card" key={p.id}>
                    <div className="plan-icon">
                      <FolderOpen size={24} />
                    </div>
                    <span className="plan-local">本机方案</span>
                    <h2>{p.name}</h2>
                    <p className="muted small">
                      {new Date(p.createdAt).toLocaleDateString("zh-CN")} ·{" "}
                      {p.input.rules.filter((r) => r.enabled).length} 项条件
                    </p>
                    <div className="plan-digits">
                      {p.input.positions.map((d, i) => (
                        <span key={i}>
                          {d.length}
                          <small>{["万", "千", "百", "十", "个"][i]}位</small>
                        </span>
                      ))}
                    </div>
                    <div className="plan-actions">
                      <button
                        className="button primary"
                        onClick={() => restore(p)}
                      >
                        使用方案 <ArrowRight size={14} />
                      </button>
                      <button
                        className="icon-button"
                        aria-label={`导出${p.name}`}
                        onClick={() =>
                          download(
                            "pl5-方案.json",
                            JSON.stringify(
                              { schemaVersion: 1, plans: [p] },
                              null,
                              2,
                            ),
                            "application/json",
                          )
                        }
                      >
                        <Download size={16} />
                      </button>
                      <button
                        className="icon-button"
                        aria-label={`删除${p.name}`}
                        onClick={() => {
                          if (confirm(`删除「${p.name}」？建议先导出备份。`))
                            persist(plans.filter((x) => x.id !== p.id));
                        }}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="card plans-empty">
                <FolderOpen size={42} />
                <h2>收藏你的第一套筛选思路</h2>
                <p className="muted">
                  在工作台选择号码和条件，再点击「保存方案」。
                </p>
                <button
                  className="button primary"
                  onClick={() => go("/workbench")}
                >
                  去工作台 <ArrowUpRight size={16} />
                </button>
              </div>
            )}
          </>
        )}
        {path === "/help" && (
          <>
            <div className="title-row">
              <div>
                <div className="eyebrow">简单开始，清楚使用</div>
                <h1>
                  每个条件，都有<span>依据。</span>
                </h1>
                <p className="muted">规则说明、数据口径和你的第一次筛选。</p>
              </div>
            </div>
            <div className="help-grid">
              <article className="card help-card">
                <h2>三步完成一次筛选</h2>
                <ol>
                  <li>选择万位至个位的候选数字，每位至少一个。</li>
                  <li>开启所需条件，并选择允许或排除的值。</li>
                  <li>点击开始缩水，核对每步移除数，再复制或导出。</li>
                </ol>
                <h3>结果是怎样计算的？</h3>
                <p>
                  不同条件同时满足，同一条件多选匹配任意一项。排除模式取该条件匹配集合的补集。位置不同即为不同号码，始终保留前导零。
                </p>
                <h3>历史数据从哪里来？</h3>
                <p>
                  历史页打开后自动获取官方最新已公布开奖；当天结果尚未返回时会明确提示。可点击「获取官方开奖」重新检查，也可导入
                  issue,date,number
                  三列CSV或手动恢复演示。来源和更新时间始终标明；演示走势不代表真实开奖。
                </p>
                <h3>数据保存在哪里？</h3>
                <p>
                  方案保存在当前浏览器本机，清理浏览器数据后可能丢失。请定期导出JSON备份。导出TXT每行一个五位号码，按升序排列。
                </p>
              </article>
              <article className="card help-card">
                <h2>基础规则速查</h2>
                <dl>
                  {Object.entries(ruleLabels).map(([kind, label]) => (
                    <div key={kind}>
                      <dt>{label}</dt>
                      <dd>
                        {
                          {
                            ...explanations,
                            geometry:
                              "按固定坐标判断直线、折线、V型、递推规律、凸包三角形/梯形及对称形。支持连续3—5位置或历史轨迹追加候选位，参数与参考期随方案保存。",
                            research:
                              "17类历史统计过滤、热度/BMA/D-S评分、滚动选参、贪心和组合包。按参考期以前的窗口拟合；评分以全量10万组为基准。参数、并列策略和种子随方案保存。模拟实验未证明预测优势，诊断可在计算后查看。",
                            sum: "五位相加，0–45。",
                            tail: "和值除以10的余数，0–9。",
                            span: "最大数字减最小数字，0–9。",
                            odd: "奇数13579，比例为奇:偶。",
                            big: "大数56789，比例为大:小。",
                            prime: "质类12357、合类04689，为彩票分类约定。",
                            distinct: "不同数字的种数，1–5。",
                            repeat:
                              "按各数字出现次数降序分类，例如00127为2111。",
                            consecutive:
                              "去重排序后相差1的相邻对数，9与0不相邻。",
                            sumMod3: "和值除以3的余数。",
                            dan: "所选数字至少出现一个，重复不增加种数。",
                            kill: "保留模式要求所选数字全部不出现。",
                          }[kind]
                        }
                      </dd>
                    </div>
                  ))}
                </dl>
              </article>
            </div>
          </>
        )}
        {!nav.some((n) => n.path === path) && (
          <div className="card plans-empty">
            <h1>这个页面还不存在</h1>
            <button className="button primary" onClick={() => go("/workbench")}>
              返回工作台
            </button>
          </div>
        )}
        <footer className="site-footer">
          <span>
            五序 WUXU <span className="footer-divider">/</span> 把选择变清晰
          </span>
          <span>缩水仅按条件筛选组合，不提高单注中奖概率。</span>
          <span>PL5 · v0.2</span>
        </footer>
      </main>
      {toast && (
        <div className="toast" role="status">
          <CheckCircle2 size={17} />
          {toast}
        </div>
      )}
      {saveOpen && (
        <div className="modal-overlay" onClick={() => setSaveOpen(false)}>
          <section
            ref={modal}
            className="modal card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="save-title"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              aria-label="关闭保存窗口"
              className="modal-close icon-button"
              onClick={() => setSaveOpen(false)}
            >
              <X size={20} />
            </button>
            <div className="plan-icon">
              <FolderOpen size={24} />
            </div>
            <h2 id="save-title">保存这次筛选思路</h2>
            <p className="muted small">
              保存号码和过滤条件，结果会在使用时重新计算。
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                save();
              }}
            >
              <label className="field-label" htmlFor="plan-name">
                方案名称
              </label>
              <input
                ref={nameField}
                id="plan-name"
                value={planName}
                onChange={(e) => setPlanName(e.target.value)}
                maxLength={60}
              />
              {saveError && (
                <p className="validation" role="alert">
                  {saveError}
                </p>
              )}
              <button className="button primary modal-submit" type="submit">
                确认保存 <ArrowRight size={16} />
              </button>
            </form>
          </section>
        </div>
      )}
    </>
  );
}
