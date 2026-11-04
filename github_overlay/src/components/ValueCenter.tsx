import { useEffect, useRef, useState } from 'react';

type KnifeValue = {
  id: string; periods: number; observed_wrong_cuts: number;
  expected_fair_wrong_cuts: number; first_cut_actual: number;
  unique_wrong_cuts: number; latest_geometric_novelty: number;
  latest_removed: number; latest_overlap: number;
  evidence_category: string; proposed_research_weight: number;
  ready_for_manual_review: boolean;
};
type ValueReport = {
  schema: string; state: string; integrity_verified: boolean|null;
  used_settled_prefix: number; minimum_periods?: number; latest_settled_issue?: string|null;
  knife_count?: number; knives: KnifeValue[]; limitations?: string;
  automatic_activation: boolean; research_only: boolean;
};
const category: Record<string,string> = {
  insufficient_evidence:'未发现可靠差异',
  fewer_wrong_cuts:'观察到较少误删（待独立复核）',
  more_wrong_cuts:'观察到较多误删（待复核）',
};
export default function ValueCenter() {
  const [report,setReport]=useState<ValueReport|null>(null);
  const [error,setError]=useState('');
  const [loading,setLoading]=useState(false);
  const current=useRef<AbortController|null>(null);
  async function load() {
    current.current?.abort();const ctrl=new AbortController();current.current=ctrl;
    setLoading(true);setError('');
    try {
      const res=await fetch('/api/esse/status',{cache:'no-store',signal:ctrl.signal});
      if(!res.ok)throw new Error(`HTTP ${res.status}`);
      const body=await res.json() as {value_center?:ValueReport};
      if(!body.value_center)throw new Error('尚未部署V1.6科研价值接口');
      if(!ctrl.signal.aborted)setReport(body.value_center);
    }catch(e){if(!ctrl.signal.aborted){setError((e as Error).message);setReport(null);}}
    finally{if(!ctrl.signal.aborted)setLoading(false);}
  }
  useEffect(()=>{void load();return ()=>current.current?.abort();},[]);
  return <section className="card" id="value-center-v16" aria-label="逐刀价值和动态研究权重">
    <div className="section-head"><h2>算法价值 · 动态研究权重中心</h2><span className="muted small">V1.6 · 只读科研审计</span></div>
    <p className="muted small">仅评估已封存、已结算的连续登记记录；权重只作下一轮研究提案，不自动调整正式过滤、修改旧记录或声称中奖优势。</p>
    <button className="button secondary" disabled={loading} onClick={()=>void load()}>{loading?'正在核验…':'刷新刀具价值'}</button>
    {error&&<p className="validation" role="alert">{error}</p>}
    {report&&<>
      <div className="summary-stats" style={{marginTop:12}}>
        <div><span>证据状态</span><strong>{report.state==='ready'?'可审计':report.state}</strong></div>
        <div><span>已结算有效前缀</span><strong>{report.used_settled_prefix}期</strong></div>
        <div><span>参与分析的刀具</span><strong>{report.knife_count??0}把</strong></div>
        <div><span>最小观察门槛</span><strong>{report.minimum_periods??100}期</strong></div>
      </div>
      {report.state==='ready'&&<>
        <p className="muted small">最近已结算期号：{report.latest_settled_issue??'暂无'}。公平独立假设下，每期误删数量的期望由当期预先封存的完整掩码精确计算。</p>
        <div style={{overflowX:'auto',maxHeight:360,marginTop:10}}><table>
          <thead><tr><th>刀具ID</th><th>审计期数</th><th>实际误删</th><th>随机期望</th><th>独有误删</th><th>最新几何独立度</th><th>实验权重</th><th>评估</th></tr></thead>
          <tbody>{report.knives.map(k=><tr key={k.id}>
            <td style={{maxWidth:180,overflowWrap:'anywhere'}}>{k.id}</td>
            <td>{k.periods}</td><td>{k.observed_wrong_cuts}</td>
            <td>{k.expected_fair_wrong_cuts.toFixed(3)}</td><td>{k.unique_wrong_cuts}</td>
            <td>{(k.latest_geometric_novelty*100).toFixed(1)}%</td>
            <td>{k.proposed_research_weight.toFixed(3)}</td>
            <td>{category[k.evidence_category]??k.evidence_category}</td>
          </tr>)}</tbody>
        </table></div>
        {!report.knives.length&&<p className="muted small">尚无可审计的刀具记录。</p>}
      </>}
      <p className="muted small">{report.limitations??'尚无证据。'} 本地封存不是第三方可信时间戳。动态权重不会自动投产。</p>
    </>}
  </section>;
}
