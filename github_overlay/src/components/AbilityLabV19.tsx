import { useEffect, useRef, useState } from 'react';

type Research = {
  id:string; goal:string; status:string;
  report: {filter_id:string;distinct_values:number; full_space_parity:boolean;
           historical_exploration?:{status:string;active_periods?:number;observed_exclusions?:number};
           predictive_advantage:string;source:string;};
};
type State = {status:string;total:number;proposals:Research[];prediction_advantage:string};
const goalNames:Record<string,string>={cross_position:'跨位置交互',modular_structure:'模运算结构',
  sequential_geometry:'序列几何',hybrid_features:'混合特征'};
export default function AbilityLabV19() {
  const [state,setState]=useState<State|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const ongoing=useRef<AbortController|null>(null);
  async function refresh(){
    ongoing.current?.abort();const controller=new AbortController();ongoing.current=controller;
    setBusy(true);setError('');
    try{
      const res=await fetch('/api/esse/ability-lab',{signal:controller.signal,cache:'no-store'});
      if(!res.ok)throw Error(`HTTP ${res.status}`);
      const body=await res.json() as State;
      if(!controller.signal.aborted)setState(body);
    }catch(e){if(!controller.signal.aborted){setError((e as Error).message);setState(null);}}
    finally{if(!controller.signal.aborted)setBusy(false);}
  }
  useEffect(()=>{void refresh();return ()=>ongoing.current?.abort();},[]);
  return <section className="card" id="ability-lab-v19" aria-label="算法创造实验室">
    <div className="section-head"><h2>自主能力创造实验室</h2><span className="muted small">V1.9 · 只读研究状态</span></div>
    <p className="muted small">目标驱动发现能力缺口，生成受约束的新数学指标，执行十万号双实现复核，再登记为实验能力。未证明预测优势；无自动下注和算法审批。</p>
    <div className="head-actions"><button className="button secondary" disabled={busy} onClick={()=>void refresh()}>{busy?'正在读取…':'刷新研究成果'}</button></div>
    {error&&<p role="alert" className="validation">{error}</p>}
    {state&&<>
      <p className="muted small">累计研究成果 {state.total} 项。{state.status==='not_initialized'?'请先初始化能力库并运行一次研究。':'新成果只自动进入研究目录，不代表更可能命中。'}</p>
      <div style={{maxHeight:380,overflow:'auto'}}><table><thead><tr><th>目标/指标</th><th>输出能力</th><th>验证</th><th>阶段</th></tr></thead>
        <tbody>{state.proposals.map(p=><tr key={p.id}>
          <td><strong>{goalNames[p.goal]??p.goal}</strong><div className="muted small">{p.id}</div></td>
          <td className="muted small">{p.report.filter_id}</td>
          <td>{p.report.full_space_parity?'双实现一致':'待复核'}<div className="muted small">不同指标值：{p.report.distinct_values}</div></td>
          <td>{p.status}<div className="muted small">仅供实验</div></td>
        </tr>)}</tbody>
      </table></div>
    </>}
  </section>;
}
