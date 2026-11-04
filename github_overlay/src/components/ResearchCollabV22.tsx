import { useEffect, useRef, useState } from 'react';
type Project = {project_id:string;family:string|null;generated:boolean;evaluated:boolean;
  report?:{engineering_pass:boolean;compared_score_values:number;checks?:{python_node:{mismatches:number}}} | null;
  automatic_release:boolean;prediction_advantage:string};
type Status = {version:string;status:string;projects:Project[];total_generated:number;total_evaluated:number;automatic_execution:boolean;automatic_release:boolean};
export default function ResearchCollabV22(){
  const [data,setData]=useState<Status|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const controller=useRef<AbortController|null>(null);
  const refresh=async()=>{
    controller.current?.abort();const c=new AbortController();controller.current=c;
    setError('');setBusy(true);
    try{
      const resp=await fetch('/api/esse/research-v22',{cache:'no-store',signal:c.signal});
      if(!resp.ok)throw Error(`HTTP ${resp.status}`);
      const result=await resp.json() as Status;
      if(!c.signal.aborted)setData(result);
    }catch(ex){if(!c.signal.aborted)setError((ex as Error).message);}
    finally{if(!c.signal.aborted)setBusy(false);}
  };
  useEffect(()=>{void refresh();return()=>controller.current?.abort();},[]);
  return <section className="card" id="research-v22" aria-label="自主代码创造与异构复核">
    <div className="section-head"><h2>自主算法工程与异构复核</h2><span className="muted small">V2.2 · 科研候选</span></div>
    <p className="muted small">受限模板自主生成两套Python实现与一套Node实现；反例覆盖前导零、历史边界、输入排列与可选10万注。运行需显式授权Docker，所有结果仅是工程一致性证据。</p>
    <button className="button secondary" disabled={busy} onClick={()=>void refresh()}>{busy?'刷新中…':'刷新研究结果'}</button>
    {error&&<p className="validation" role="alert">{error}</p>}
    {data&&<>
      <p className="muted small">已生成 {data.total_generated} 个算法项目 · 已完成异构检验 {data.total_evaluated} 个 · 自动正式发布：关闭{data.status==='not_initialized'?'（研究库尚未建立）':''}</p>
      <div style={{overflowX:'auto',maxHeight:340,overflowY:'auto'}}><table><thead><tr><th>算法类型</th><th>跨语言校验</th><th>比较数值</th><th>工程结论</th></tr></thead><tbody>
      {data.projects.map(p=><tr key={p.project_id}><td>{p.family||'未指定'}<div className="muted small">{p.project_id.slice(0,12)}</div></td>
        <td>{p.evaluated?(p.report?.engineering_pass?'一致':'存在差异'):'未运行Docker'}</td>
        <td>{p.report?.compared_score_values?.toLocaleString()||'—'}</td>
        <td className="muted small">{p.evaluated?(p.report?.engineering_pass?'工程实验通过，未验证预测':'需要复核或重建'):'研究提案'}</td></tr>)}
      </tbody></table></div>
      <p className="muted small">生成能力、论文忠实复现能力、未来号码预测能力是三项不同评价。任何结果均不会自动激活ESSE正式过滤。</p>
    </>}
  </section>;
}
