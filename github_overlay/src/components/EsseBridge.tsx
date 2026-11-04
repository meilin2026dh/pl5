import { useEffect, useRef, useState } from "react";
import type { FilterInput } from "../domain/pick5";

type Stage = { key: string; label: string; before: number; after: number; newly_removed: number; already_removed: number };
type BridgeResult = {
  engine: string; base_count: number; strict_keep_count: number; selected_count: number;
  expected_strict_keep: number; parity_count_verified: boolean; full_mask_parity_verified: boolean; independent_rule_count: number; unverified_rule_types: string[]; top_numbers: string[];
  restored_for_quota: number; source_guard: boolean; steps: Stage[];
  fair_random_single_draw_coverage: number; statistical_status: string;
  request_sha256: string; history_source_verified_by_backend: boolean;
  registered_rule_count?: number; typescript_strict_keep_count?: number;
  registered_experimental_rules?: {id: string; mask_sha256: string; experimental_only: boolean}[];
};

export default function EsseBridge({ input, onChange }: { input: FilterInput; onChange: (next: FilterInput) => void }) {
  const [k, setK] = useState(100), [seed, setSeed] = useState(20261101);
  const [registeredIds, setRegisteredIds] = useState("");
  const rawRequest = useRef<unknown>(null);
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  const [result, setResult] = useState<BridgeResult | null>(null);
  const workerRef = useRef<Worker | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const serial = JSON.stringify(input);
  const serialRef = useRef(serial);
  serialRef.current = serial;
  const requestId = useRef(0);
  const resultInput = useRef("");
  const stale = !!result && resultInput.current !== serial;
  const cancel = () => {
    workerRef.current?.terminate(); workerRef.current = null;
    abortRef.current?.abort(); abortRef.current = null;
    requestId.current++;
    setBusy(false);
  };
  useEffect(() => {
    // Input edits invalidate both pending computation and visible results.
    workerRef.current?.terminate(); workerRef.current = null;
    abortRef.current?.abort(); abortRef.current = null;
    requestId.current++;
    setBusy(false);
    setResult(null);
    rawRequest.current = null;
  }, [serial]);
  useEffect(() => () => {
    workerRef.current?.terminate(); abortRef.current?.abort();
  }, []);
  const run = () => {
    cancel(); setResult(null); rawRequest.current = null; setError("");
    const registeredRuleIds = registeredIds.split(/[\s,;，；]+/).filter(Boolean);
    if (registeredRuleIds.length>10 || new Set(registeredRuleIds).size !== registeredRuleIds.length ||
        registeredRuleIds.some(id=>!/^[0-9a-f]{64}$/.test(id))) {
      setError("注册规则ID必须为最多10个不重复的64位小写SHA256"); return;
    }
    setBusy(true);
    const mine = ++requestId.current;
    const snapshot = serial;
    const w = new Worker(new URL("../workers/esse.worker.ts", import.meta.url), {type:"module"});
    workerRef.current = w;
    w.onerror = () => {
      if (mine !== requestId.current) return;
      w.terminate(); workerRef.current=null; setBusy(false);
      setError("本地ESSE位图线程出错");
    };
    w.onmessage = async (event: MessageEvent<{requestId:number;payload?:unknown;error?:string}>) => {
      if (mine !== requestId.current || snapshot !== serialRef.current) return;
      w.terminate(); workerRef.current = null;
      if (event.data.error) { setError(event.data.error); setBusy(false); return; }
      const abort = new AbortController(); abortRef.current = abort;
      try {
        const response = await fetch("/api/esse/sculpt", {
          method:"POST", headers:{"Content-Type":"application/json"},
          body:JSON.stringify(event.data.payload), signal:abort.signal,
        });
        const body = await response.json();
        if (!response.ok) throw new Error(body.message ?? body.error ?? "Python ESSE服务不可用");
        if (mine !== requestId.current || snapshot !== serialRef.current) return;
        rawRequest.current = event.data.payload;
        setResult(body as BridgeResult);
        resultInput.current = snapshot;
      } catch (e) {
        if (mine === requestId.current && !abort.signal.aborted)
          setError((e as Error).message);
      } finally {
        if (mine === requestId.current) { abortRef.current=null;setBusy(false); }
      }
    };
    w.postMessage({requestId: mine, input, k, seed, registeredRuleIds});
  };
  return (
    <section className="card" id="esse-v12-title" aria-label="ESSE融合雕塑工作台">
      <div className="section-head"><h2>ESSE · V1.4 算法准入与雕塑</h2><span className="muted small">跨语言审计 · 实验功能</span></div>
      <p className="muted small">继续使用五序现有规则计算过滤掩码，再交给Python ESSE计算每刀边际贡献、可逆评分与100注以内的候选集合。</p>
      <p className="muted small">可选：填写已由本地科研注册库批准的实验刀ID（最多10个；逗号分隔）。注册规则只能由本机命令行审批，不能在网页中自我批准；每次运行必须与规则原历史截止期、来源大底完全一致。</p>
      <label>科研实验刀ID（可留空）<input aria-label="实验刀ID" style={{width:"100%"}} value={registeredIds} placeholder="填写已批准的64位SHA256 ID" onChange={e=>{cancel();setRegisteredIds(e.target.value);setResult(null);rawRequest.current=null;}} /></label>
      <div className="head-actions">
        <label>目标注数 <input aria-label="ESSE目标注数" type="number" min={1} max={100} value={k} onChange={(e)=>setK(Number(e.target.value))}/></label>
        <label>种子 <input aria-label="ESSE随机种子" type="number" min={0} max={4294967295} value={seed} onChange={(e)=>setSeed(Number(e.target.value))}/></label>
        <button className="button primary" disabled={busy || !(k>=1 && k<=100)} onClick={run}>运行跨语言雕塑</button>
        {busy && <button className="button secondary" onClick={cancel}>取消</button>}
      </div>
      {busy && <p role="status">正在生成原生规则位图或执行Python雕塑…</p>}
      {error && <p role="alert" className="validation">{error}。请确认本机Python桥接服务已启动。</p>}
      {result && !stale && <>
        <p><strong>来源 {result.base_count.toLocaleString()} 注 → 原生严格交集 {(result.typescript_strict_keep_count ?? result.strict_keep_count).toLocaleString()} 注 → 研究刀后 {result.strict_keep_count.toLocaleString()} 注 → 输出 {result.selected_count} 注</strong></p>
        <p className="muted small">研究库批准的实验规则：{result.registered_rule_count ?? 0} 条。仅表示可研究使用，不代表预测概率提升。</p>
        <p className="muted small">交集计数一致：{result.parity_count_verified?"是":"否"}；完整交集位图一致：{result.full_mask_parity_verified?"是":"否"}；基础规则独立复算：{result.independent_rule_count}条；来源域保护：{result.source_guard?"通过":"失败"}；为满足数量恢复 {result.restored_for_quota} 注。未独立复算的高级规则种类：{result.unverified_rule_types.join("、") || "无"}。</p>
        <p className="muted small">公平开奖下单期精确覆盖率：{(result.fair_random_single_draw_coverage*100).toFixed(3)}%。以下分数不是经校准的中奖概率。</p>
        <div style={{maxHeight:"240px",overflowY:"auto"}}>
          <table><thead><tr><th>雕刻刀</th><th>过滤前</th><th>过滤后</th><th>新增移除</th><th>重复移除</th></tr></thead>
          <tbody>{result.steps.map(s=><tr key={s.key}><td>{s.label}</td><td>{s.before}</td><td>{s.after}</td><td>{s.newly_removed}</td><td>{s.already_removed}</td></tr>)}</tbody></table>
        </div>
        <details><summary>查看 {result.selected_count} 注候选</summary><p style={{wordBreak:"break-word"}}>{result.top_numbers.join("、")}</p></details>
        <div className="head-actions">
          <button className="button secondary" onClick={()=>{
            // Existing GitHub semantics: external base overrides positional selection.
            // Disable all old rules so results are not silently filtered twice.
            onChange({...input,candidates:result.top_numbers,rules:input.rules.map(r=>({...r,enabled:false}))});
            setResult(null);
          }}>将结果载入大底（停用原规则）</button>
          <button className="button secondary" onClick={()=>{
            const data = new Blob([result.top_numbers.join("\r\n")+"\r\n"],{type:"text/plain;charset=utf-8"});
            const url=URL.createObjectURL(data);const a=document.createElement("a");a.href=url;a.download="PL5_ESSE_V14_top.txt";a.click();URL.revokeObjectURL(url);
          }}>导出候选 TXT</button>
        </div>
        <button className="button secondary" onClick={()=>{
          if(!rawRequest.current) return;
          const blob=new Blob([JSON.stringify(rawRequest.current,null,2)],{type:"application/json"});
          const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download="PL5_V14_research_mask_request.json";a.click();URL.revokeObjectURL(url);
        }}>导出规则位图研究请求JSON</button>
        <p className="muted small">数据来源只在浏览器标记，Python桥接尚未独立核验官方数据签名。结果输入SHA256：{result.request_sha256.slice(0,16)}…</p>
      </>}
    </section>
  );
}
