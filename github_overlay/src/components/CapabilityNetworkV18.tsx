import { useEffect, useRef, useState } from 'react';

type Card = {
  id:string; name:string; op:string; requires:string[]; status:string;
  output_type:string;origin:string;limitations:string;predictive_status:string;
};
type Result = {status:string;count:number;nodes:Card[];truncated?:boolean;message?:string};
export default function CapabilityNetworkV18() {
  const [result,setResult]=useState<Result|null>(null);
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const [filter,setFilter]=useState('all');
  const pending=useRef<AbortController|null>(null);
  async function refresh() {
    pending.current?.abort(); const controller=new AbortController();pending.current=controller;
    setBusy(true);setError('');
    try {
      const response=await fetch('/api/esse/capabilities',{cache:'no-store',signal:controller.signal});
      if(!response.ok) throw Error(`HTTP ${response.status}`);
      const body=await response.json() as Result;
      if(!controller.signal.aborted)setResult(body);
    }catch(err){if(!controller.signal.aborted){setError((err as Error).message);setResult(null);}}
    finally{if(!controller.signal.aborted)setBusy(false);}
  }
  useEffect(()=>{void refresh();return ()=>pending.current?.abort();},[]);
  const items=(result?.nodes??[]).filter(c=>filter==='all'||c.op===filter);
  return <section className="card" id="capability-network-v18" aria-label="算法能力网络">
    <div className="section-head"><h2>算法能力网络 AAN</h2><span className="muted small">V1.8 · 研究目录</span></div>
    <p className="muted small">算法说明书、输入输出、依赖和协同关系。新能力自动进入研究库，未经审计不能声明预测优势或自动进入正式过滤。</p>
    <div className="head-actions">
      <button className="button secondary" disabled={busy} onClick={()=>void refresh()}>{busy?'读取中…':'刷新能力目录'}</button>
      <label className="muted small">能力类型{' '}
        <select value={filter} aria-label="按能力类型筛选" onChange={e=>setFilter(e.target.value)}>
          <option value="all">全部</option><option value="metric">指标计算</option>
          <option value="pattern">模式识别</option><option value="anti_filter">反延续过滤</option>
          <option value="merge_masks">组合过滤</option>
        </select>
      </label>
    </div>
    {error && <p className="validation" role="alert">{error}</p>}
    {result && <>
      <p className="muted small">已登记 {result.count} 项能力；{result.message??'所有条目仅属于研究记录，不是可靠预测规则。'} {result.truncated?'（仅显示前100项）':''}</p>
      <div style={{overflowX:'auto',maxHeight:380,overflowY:'auto'}}>
        <table><thead><tr><th>能力</th><th>类别</th><th>输入依赖</th><th>输出</th><th>阶段</th></tr></thead>
          <tbody>{items.map(c=><tr key={c.id}>
            <td title={c.id}><strong>{c.name}</strong><div className="muted small">{c.id}</div></td>
            <td>{c.op}</td><td className="muted small">{c.requires.join(' / ')||'原子能力'}</td>
            <td>{c.output_type}</td><td>{c.status}</td>
          </tr>)}</tbody>
        </table>
      </div>
    </>}
  </section>;
}
