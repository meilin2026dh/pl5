import { useEffect, useRef, useState } from "react";

type LastScan = {
  id: string; created_at: string; latest_issue: string; candidate_count: number;
  failure_count: number; entries: {
    id: string; title: string; state: string; removed_fraction: number;
    observed_removed_hits: number; holdout_periods: number; failure_signal: boolean;
  }[];
};
type ResearchStatus = {
  schema: string; generated_at: string;
  bridge: {state: string; read_only: boolean};
  registry: {state: string; ledger_verified: boolean | null;
    counts: Record<string,number>; paused: number; scans: number; last_scan: LastScan | null};
  official_cache: {state: string; record_count: number; latest_issue: string|null;
    latest_date: string|null; updated_at: string|null; origin_cryptographically_verified: false};
  safe_modes: {auto_purchase: false; auto_approval: false;
    research_scores_are_win_probabilities: false};
  notice: string;
};

export default function EvolutionStatus() {
  const [data, setData] = useState<ResearchStatus|null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const request = useRef(0);
  const abort = useRef<AbortController|null>(null);
  const load = async () => {
    abort.current?.abort();
    const controller=new AbortController(); abort.current=controller;
    const mine=++request.current;
    setLoading(true); setError("");
    try {
      const r=await fetch("/api/esse/status",{cache:"no-store",signal:controller.signal});
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const result=await r.json() as ResearchStatus;
      if(result.schema!=="pl5-live-status-v151") throw new Error("后端版本不匹配");
      if(mine===request.current) setData(result);
    } catch(e) {
      if(!controller.signal.aborted && mine===request.current) {
        setData(null); setError(`科研服务不可用或版本不匹配：${(e as Error).message}`);
      }
    } finally { if(mine===request.current) setLoading(false); }
  };
  useEffect(()=>{
    void load();
    return ()=>{request.current++;abort.current?.abort();};
  },[]);
  return <section className="card" id="esse-evolution-status" aria-label="PL5算法竞争状态">
    <div className="section-head"><h2>算法竞争与进化中心 · 运行状态</h2>
      <span className="muted small">V1.5.1 · 只读审计</span></div>
    <p className="muted small">这里展示已经执行并落盘的科研结果，不会自动创建、审批或运行新过滤规则。</p>
    <button type="button" className="button secondary" disabled={loading} onClick={()=>void load()}>
      {loading?"正在检查…":"刷新本机科研状态"}
    </button>
    {error && <p role="alert" className="validation">{error}。请先启动V1.5.1科研后端及五序Node服务。</p>}
    {data && <>
      <div className="summary-stats" style={{marginTop:12}}>
        <div><span>科研后端</span><strong>{data.bridge.state==="online"?"在线":"异常"}</strong></div>
        <div><span>算法注册账本</span><strong>{data.registry.state==="ready"?"正常":data.registry.state}</strong></div>
        <div><span>算法候选</span><strong>{data.registry.counts.candidate??0}</strong></div>
        <div><span>批准的实验规则</span><strong>{data.registry.counts.approved_experimental??0}</strong></div>
        <div><span>暂停规则</span><strong>{data.registry.paused}</strong></div>
        <div><span>累计竞争扫描</span><strong>{data.registry.scans}</strong></div>
      </div>
      <p className="muted small">官方接口缓存：{data.official_cache.state}；已记录 {data.official_cache.record_count} 期；最近期号 {data.official_cache.latest_issue??"—"}，日期 {data.official_cache.latest_date??"—"}。</p>
      <p className="muted small">来源独立密码学认证：否。注册账本完整性：{data.registry.ledger_verified===true?"校验通过":data.registry.ledger_verified===false?"校验失败":"尚未配置"}。</p>
      {data.registry.last_scan ? <>
        <h3>最近一次算法竞争</h3>
        <p className="muted small">运行：{data.registry.last_scan.created_at}；截止期：{data.registry.last_scan.latest_issue}；审查 {data.registry.last_scan.candidate_count} 条；风险信号 {data.registry.last_scan.failure_count} 条。</p>
        <div style={{maxHeight:240,overflow:"auto"}}><table><thead><tr>
          <th>算法</th><th>状态</th><th>剔除占比</th><th>历史误删</th><th>风险</th>
        </tr></thead><tbody>
          {data.registry.last_scan.entries.map(r=><tr key={r.id}>
            <td title={r.id}>{r.title}</td><td>{r.state}</td>
            <td>{(r.removed_fraction*100).toFixed(2)}%</td>
            <td>{r.observed_removed_hits}/{r.holdout_periods}</td>
            <td>{r.failure_signal?"待复审":"无明确告警"}</td>
          </tr>)}
        </tbody></table></div>
      </>:<p className="muted small">尚无已保存的竞争扫描报告。先由V1.5研究CLI运行扫描后再刷新。</p>}
      <p className="muted small">{data.notice}</p>
    </>}
  </section>;
}
