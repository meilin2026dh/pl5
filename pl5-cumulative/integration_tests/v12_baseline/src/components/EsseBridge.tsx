import { useEffect, useRef, useState } from "react";
import type { FilterInput } from "../domain/pick5";

type Stage = { key: string; label: string; before: number; after: number; newly_removed: number; already_removed: number };
type BridgeResult = {
  engine: string; base_count: number; strict_keep_count: number; selected_count: number;
  expected_strict_keep: number; parity_count_verified: boolean; top_numbers: string[];
  restored_for_quota: number; source_guard: boolean; steps: Stage[];
  fair_random_single_draw_coverage: number; statistical_status: string;
  request_sha256: string; history_source_verified_by_backend: boolean;
};

export default function EsseBridge({ input, onChange }: { input: FilterInput; onChange: (next: FilterInput) => void }) {
  const [k, setK] = useState(100), [seed, setSeed] = useState(20261101);
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
  }, [serial]);
  useEffect(() => () => {
    workerRef.current?.terminate(); abortRef.current?.abort();
  }, []);
  const run = () => {
    cancel(); setResult(null); setError(""); setBusy(true);
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
        setResult(body as BridgeResult);
        resultInput.current = snapshot;
      } catch (e) {
        if (mine === requestId.current && !abort.signal.aborted)
          setError((e as Error).message);
      } finally {
        if (mine === requestId.current) { abortRef.current=null;setBusy(false); }
      }
    };
    w.postMessage({requestId: mine, input, k, seed});
  };
  return (
    <section className="card" id="esse-v12-title" aria-label="ESSE融合雕塑工作台">
      <div className="section-head"><h2>ESSE · V1.2 融合雕塑</h2><span className="muted small">跨语言审计 · 实验功能</span></div>
      <p className="muted small">继续使用五序现有规则计算过滤掩码，再交给Python ESSE计算每刀边际贡献、可逆评分与100注以内的候选集合。</p>
      <div className="head-actions">
        <label>目标注数 <input aria-label="ESSE目标注数" type="number" min={1} max={100} value={k} onChange={(e)=>setK(Number(e.target.value))}/></label>
        <label>种子 <input aria-label="ESSE随机种子" type="number" min={0} max={4294967295} value={seed} onChange={(e)=>setSeed(Number(e.target.value))}/></label>
        <button className="button primary" disabled={busy || !(k>=1 && k<=100)} onClick={run}>运行跨语言雕塑</button>
        {busy && <button className="button secondary" onClick={cancel}>取消</button>}
      </div>
      {busy && <p role="status">正在生成原生规则位图或执行Python雕塑…</p>}
      {error && <p role="alert" className="validation">{error}。请确认本机Python桥接服务已启动。</p>}
      {result && !stale && <>
        <p><strong>来源 {result.base_count.toLocaleString()} 注 → 严格交集 {result.strict_keep_count.toLocaleString()} 注 → 输出 {result.selected_count} 注</strong></p>
        <p className="muted small">交集计数一致：{result.parity_count_verified?"是":"否"}；来源域保护：{result.source_guard?"通过":"失败"}；为满足数量恢复 {result.restored_for_quota} 注。此处没有独立证明全部TypeScript指标在Python中等价。</p>
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
            const url=URL.createObjectURL(data);const a=document.createElement("a");a.href=url;a.download="PL5_ESSE_V12_top.txt";a.click();URL.revokeObjectURL(url);
          }}>导出候选 TXT</button>
        </div>
        <p className="muted small">数据来源只在浏览器标记，Python桥接尚未独立核验官方数据签名。结果输入SHA256：{result.request_sha256.slice(0,16)}…</p>
      </>}
    </section>
  );
}
