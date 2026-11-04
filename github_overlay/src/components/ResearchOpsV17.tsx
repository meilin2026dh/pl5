import { useEffect, useRef, useState } from 'react';

type Stage = {stage:string;status:string;attempts:number;error:string};
type Cycle = {cycle_key:string;state:string;updated_at:string;last_error:string;stages:Stage[]};
type Summary = {state:string;last_cycle:Cycle|null;completed_cycles:number;failed_cycles:number;
  official_archive:{state:string;count?:number;latest_issue?:string|null;version?:string|null};
  automatic_algorithm_approval:boolean;paid_calls_enabled:boolean};
export default function ResearchOpsV17() {
  const [data,setData]=useState<Summary|null>(null);
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const request=useRef<AbortController|null>(null);
  async function refresh() {
    request.current?.abort();const ctl=new AbortController();request.current=ctl;
    setBusy(true);setError('');
    try {
      const r=await fetch('/api/esse/status',{cache:'no-store',signal:ctl.signal});
      if(!r.ok)throw Error(`HTTP ${r.status}`);
      const json=await r.json() as {autonomous_research?:Summary};
      if(!json.autonomous_research)throw Error('V1.7科研状态接口尚未安装');
      if(!ctl.signal.aborted)setData(json.autonomous_research);
    } catch(e) {if(!ctl.signal.aborted){setError((e as Error).message);setData(null);}}
    finally {if(!ctl.signal.aborted)setBusy(false);}
  }
  useEffect(()=>{void refresh();return ()=>request.current?.abort();},[]);
  return <section className="card" id="research-ops-v17" aria-label="自主科研任务状态">
    <div className="section-head"><h2>自主科研运行中心</h2><span className="muted small">V1.7 · 只读状态</span></div>
    <p className="muted small">科研任务需要先在Windows注册定时调度。此处仅显示已有记录；无自动投注、无自动审批，科研分数不是实际中奖概率。</p>
    <button className="button secondary" disabled={busy} onClick={()=>void refresh()}>{busy?'读取中…':'刷新运行状态'}</button>
    {error && <p className="validation" role="alert">{error}</p>}
    {data && <>
      <div className="summary-stats" style={{marginTop:12}}>
        <div><span>科研状态</span><strong>{data.state}</strong></div>
        <div><span>完成周期</span><strong>{data.completed_cycles}</strong></div>
        <div><span>失败周期</span><strong>{data.failed_cycles}</strong></div>
        <div><span>官方归档</span><strong>{data.official_archive.count??0}期</strong></div>
      </div>
      <p className="muted small">最新已归档期号：{data.official_archive.latest_issue??'暂无'}；更新仅依据经校验的官方接口响应，本地URL记录不是第三方可信签名。</p>
      {data.last_cycle ? <>
        <p className="muted small">最近周期 {data.last_cycle.cycle_key} · {data.last_cycle.state} · {data.last_cycle.updated_at}</p>
        {data.last_cycle.last_error && <p className="validation" role="alert">{data.last_cycle.last_error}</p>}
        <div style={{overflowX:'auto'}}><table><thead><tr><th>任务阶段</th><th>状态</th><th>次数</th><th>异常</th></tr></thead><tbody>
          {data.last_cycle.stages.map(t=><tr key={t.stage}><td>{t.stage}</td><td>{t.status}</td><td>{t.attempts}</td><td>{t.error||'—'}</td></tr>)}
        </tbody></table></div>
      </> : <p className="muted small">尚无科研运行记录；需要在Windows首次执行或注册定时任务。</p>}
    </>}
  </section>;
}
