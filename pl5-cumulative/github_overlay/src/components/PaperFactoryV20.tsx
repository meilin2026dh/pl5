import { useEffect, useRef, useState } from 'react';

type Card = {
  id:string;name:string;status:string;
  source:{document_key:string;document_sha256:string;source_quote:string;locator:string};
  code_sha256:{primary?:string;reference?:string};
  study?:{engineering_cross_check:boolean;tested_periods:number;actual_historical_hits:number}|null;
};
type Payload={status:string;total_blueprints:number;total_studies:number;cards:Card[]};
export default function PaperFactoryV20(){
  const [state,setState]=useState<Payload|null>(null);
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const controller=useRef<AbortController|null>(null);
  const reload=async()=>{
    controller.current?.abort();
    const signal=new AbortController();controller.current=signal;setBusy(true);setError('');
    try{
      const resp=await fetch('/api/esse/paper-factory',{cache:'no-store',signal:signal.signal});
      if(!resp.ok)throw Error(`HTTP ${resp.status}`);
      const data=await resp.json() as Payload;
      if(!signal.signal.aborted)setState(data);
    }catch(ex){if(!signal.signal.aborted)setError((ex as Error).message);}
    finally{if(!signal.signal.aborted)setBusy(false);}
  };
  useEffect(()=>{void reload();return()=>controller.current?.abort();},[]);
  return <section className="card" id="paper-factory-v20" aria-label="论文方法与算法创造证据链">
    <div className="section-head"><h2>论文方法与能力创造中心</h2><span className="muted small">V2.0 · 仅供科研</span></div>
    <p className="muted small">自动收集原文研究线索；核验引用片段、代码指纹、配对实验和失败证据。代码执行必须显式批准Docker沙箱；算法不会自动参与正式过滤。</p>
    <div className="head-actions"><button className="button secondary" disabled={busy} onClick={()=>void reload()}>{busy?'读取中…':'刷新科研方法卡'}</button></div>
    {error&&<p role="alert" className="validation">{error}</p>}
    {state&&<>
      <p className="muted small">方法卡 {state.total_blueprints} 项 · 配对实验 {state.total_studies} 次。{state.status==='not_initialized'?'论文方法库尚未初始化。':''}</p>
      <div style={{maxHeight:420,overflowY:'auto'}}><table><thead><tr><th>方法/来源</th><th>原文依据</th><th>工程复核</th><th>状态</th></tr></thead><tbody>
      {state.cards.map(c=><tr key={c.id}>
        <td><strong>{c.name}</strong><div className="muted small">{c.source.document_key}</div></td>
        <td className="muted small" style={{maxWidth:300,overflowWrap:'anywhere'}}>
          <div>{c.source.locator}</div><div>“{c.source.source_quote}”</div>
        </td>
        <td>{c.study?.engineering_cross_check?'双实现Top-K一致':c.code_sha256.primary?'待第二实现/沙箱验证':'尚未执行'}
          <div className="muted small">{c.study?`探索性历史测试 ${c.study.tested_periods}期`:'无独立前向证据'}</div></td>
        <td><span className="muted small">{c.status}</span></td>
      </tr>)}
      </tbody></table></div>
      <p className="muted small">说明：科研方法卡的原文摘录不等于完整论文复现；评分和历史命中不等于未来中奖概率。</p>
    </>}
  </section>;
}
