import { useEffect, useRef, useState } from "react";

type EvidenceStatus = {
  state: string; ledger_verified: boolean|null; seals: number; settled: number;
  pending: number; last_issue: string|null; auditable_prefix?: number;
  hits_in_prefix: number; expected_fair_hits_in_prefix: number;
  knife_actuals_in_prefix: Record<string,{would_cut_actual:number;first_cut_actual:number}>;
};

export default function ForwardEvidence() {
  const [data,setData] = useState<EvidenceStatus|null>(null);
  const [error,setError] = useState("");
  const [loading,setLoading] = useState(false);
  const inFlight=useRef<AbortController|null>(null);
  const load=async () => {
    inFlight.current?.abort();
    const controller=new AbortController();inFlight.current=controller;
    setLoading(true);setError("");
    try {
      const res=await fetch("/api/esse/status",{cache:"no-store",signal:controller.signal});
      if(!res.ok) throw new Error(`HTTP ${res.status}`);
      const body=await res.json() as {forward_evidence?:EvidenceStatus};
      if(!body.forward_evidence) throw new Error("后端没有V1.5.2前向台账接口");
      if(!controller.signal.aborted)setData(body.forward_evidence);
    }catch(err){if(!controller.signal.aborted){setError((err as Error).message);setData(null);}}
    finally{if(!controller.signal.aborted)setLoading(false);}
  };
  useEffect(()=>{void load();return ()=>inFlight.current?.abort();},[]);
  const rows=Object.entries(data?.knife_actuals_in_prefix??{});
  return <section className="card" id="forward-evidence-v152" aria-label="前向封存与逐刀证据">
    <div className="section-head"><h2>开奖前封存 · 逐刀证据台账</h2><span className="muted small">V1.5.2 · 只读审计</span></div>
    <p className="muted small">封存前在ESSE面板导出规则位图请求JSON，随后在本机命令行登记目标期号。开奖后使用经过核对的官方快照结算。这里不自动封存、不自动购彩。</p>
    <button className="button secondary" disabled={loading} onClick={()=>void load()}>{loading?"正在刷新…":"刷新前向证据"}</button>
    {error&&<p role="alert" className="validation">{error}</p>}
    {data&&<>
      <div className="summary-stats" style={{marginTop:12}}>
        <div><span>证据账本</span><strong>{data.state==="ready"?"可读":data.state}</strong></div>
        <div><span>已封存</span><strong>{data.seals}</strong></div>
        <div><span>已结算</span><strong>{data.settled}</strong></div>
        <div><span>待开奖</span><strong>{data.pending}</strong></div>
        <div><span>连续可审计前缀命中</span><strong>{data.hits_in_prefix}</strong></div>
        <div><span>公平基线期望命中</span><strong>{data.expected_fair_hits_in_prefix.toFixed(4)}</strong></div>
      </div>
      <p className="muted small">最近登记期号：{data.last_issue??"暂无"}；本地哈希链：{data.ledger_verified===true?"校验通过":data.ledger_verified===false?"校验失败":"未配置"}。仅采用未被待核验期打断的连续登记前缀进行命中累计。</p>
      {rows.length>0&&<><h3>各把雕刻刀的开奖后核验</h3>
        <div style={{maxHeight:220,overflow:"auto"}}><table><thead><tr><th>规则ID</th><th>若单独使用会排除中奖号</th><th>实际第一刀排除</th></tr></thead>
        <tbody>{rows.map(([key,v])=><tr key={key}><td>{key}</td><td>{v.would_cut_actual}</td><td>{v.first_cut_actual}</td></tr>)}</tbody></table></div>
      </>}
      <p className="muted small">本地封存哈希不是可信第三方时间戳，也不独立证明官方数据来源；压缩和模型评分不能证明预测优势。首次运行请参考V1.5.2使用说明。</p>
    </>}
  </section>;
}
