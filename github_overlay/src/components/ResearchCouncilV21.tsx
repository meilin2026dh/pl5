import { useEffect, useRef, useState } from 'react';

type Project={project_id:string;goal:string;completed:string[];next_stage:string|null;state:string;event_count:number;experimental_only:boolean;prediction_advantage:string};
type Status={status:string;total:number;projects:Project[];auto_publish:boolean};
const stepNames:Record<string,string>={literature:'论文证据',hypothesis:'研究假设',ability_gap:'能力缺口',engineer_primary:'主算法实现',engineer_reference:'独立参考实现',adversarial_review:'反例审查',sandbox_audit:'沙箱配对实验',decision:'科学审议'};
export default function ResearchCouncilV21(){
  const [state,setState]=useState<Status|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const active=useRef<AbortController|null>(null);
  const refresh=async()=>{
    active.current?.abort();const c=new AbortController();active.current=c;
    setBusy(true);setError('');
    try{
      const response=await fetch('/api/esse/research-council',{signal:c.signal,cache:'no-store'});
      if(!response.ok)throw Error(`HTTP ${response.status}`);
      const payload=await response.json() as Status;
      if(!c.signal.aborted)setState(payload);
    }catch(ex){if(!c.signal.aborted)setError((ex as Error).message);}
    finally{if(!c.signal.aborted)setBusy(false);}
  };
  useEffect(()=>{void refresh();return()=>active.current?.abort();},[]);
  return <section className="card" id="research-council-v21" aria-label="多角色科研协同委员会">
    <div className="section-head"><h2>多角色科研协同委员会</h2><span className="muted small">V2.1 · 受控研究</span></div>
    <p className="muted small">从论文证据到独立两路工程、反例审查和沙箱对照，所有角色交接留痕。需要人工提交代码和明确Docker授权；平台不会自动运行外部代码或发布预测算法。</p>
    <button className="button secondary" disabled={busy} onClick={()=>void refresh()}>{busy?'正在读取…':'刷新科研任务'}</button>
    {error&&<p className="validation" role="alert">{error}</p>}
    {state&&<><p className="muted small">科研任务 {state.total} 个 · 只读状态{state.status==='not_initialized'?'（研究库尚未创建）':''} · 自动发布：关闭</p>
      <div style={{overflowX:'auto',maxHeight:380,overflowY:'auto'}}><table><thead><tr><th>研究目标</th><th>已完成</th><th>下一环节</th><th>状态</th></tr></thead><tbody>
        {state.projects.map(p=><tr key={p.project_id}>
          <td style={{maxWidth:280,overflowWrap:'anywhere'}}><strong>{p.goal}</strong><div className="muted small">{p.project_id.slice(0,12)}</div></td>
          <td className="muted small">{p.completed.map(s=>stepNames[s]||s).join('、')||'未启动'}</td>
          <td>{p.next_stage?(stepNames[p.next_stage]||p.next_stage):'等待人工审议'}</td>
          <td className="muted small">{p.state==='research_review_pending'?'研究待审':'研究进行中'}</td>
        </tr>)}
      </tbody></table></div>
      <p className="muted small">请在V2.1命令行提交两份独立实现并执行隔离审计；历史命中不构成预测有效性证明。</p></>}
  </section>;
}
