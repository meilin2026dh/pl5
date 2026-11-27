/* V3.8.26 subset-dominance certificate for exact ordered combination optimization.
   Reference V3.8.23 frozen blob fea49f50bd55e72cc37c4535a9da66b52a3e232b.
   Independent exhaustive per-pair oracle; no timing or historical coverage claim.
   Resource-subset preprocessing is O(m^2) subset tests, not constant-time.
   Complete objective evaluation counts exclude preprocessing and memory costs. */
function audit(){
  // INTERNAL/AI_AUTHORED. Fixed abstract cost profiles, no historical data.
  // Given fixed first and second rules, at most 3 third edges are forbidden.
  // Sort edges by (direct cost,index). If 4 ALREADY RETAINED earlier edges
  // have resource sets contained in R_k, at least one is admissible and
  // has no greater direct cost or incremental nonnegative setup charge.
  // Thus removing k preserves the exact optimum for every ordered pair.
  // Using retained witnesses avoids any reliance on a removed edge.
  const check=(condition,message)=>{if(!condition)throw Error(message)};
  const edges=n=>{const e=[];for(let a=0;a<n;a++)for(let b=a+1;b<n;b++)e.push([a,b]);return e};
  const profiles=(n,e)=>{
    const make=(name,direct,resources,weights)=>({name,direct,resources,weights});
    const out=[make('uniform',e.map(()=>1),e.map(()=>[]),[]),
    make('skew',e.map((_,i)=>1+(i*7)%13),e.map(()=>[]),[]),
    make('zero',e.map(()=>0),e.map(()=>[]),[]),
    make('endpoint',e.map((_,i)=>1+i%3),e.map(x=>x),Array.from({length:n},(_,i)=>20+i*3)),
    make('mixed',e.map((_,i)=>1+i%5),e.map(([a,b],i)=>[a%3,(b+i)%3]),[90,40,70]),
    make('setup_only',e.map(()=>0),e.map(([a,b])=>b<3?[]:[0]),[50]),
    make('triangle_first',e.map(([a,b])=>b<3?0:5),e.map(()=>[0,0]),[7])];
    for(let z=0;z<3;z++){let state=(3823+n*19+z*101)>>>0;const next=()=>state=(Math.imul(1664525,state)+1013904223)>>>0;const direct=e.map(()=>next()%17),resources=e.map(()=>Array.from({length:3},()=>next()%5)),weights=Array.from({length:5},()=>next()%31);out.push(make('fixed_'+z,direct,resources,weights))}
    out.push(make('nested_unique',e.map((_,i)=>i),e.map((_,i)=>Array.from({length:i+1},(_,j)=>j)),e.map(()=>1)));
    out.push(make('nested_reverse_cost',e.map((_,i)=>e.length-i),e.map((_,i)=>Array.from({length:i+1},(_,j)=>j)),e.map(()=>1)));
    out.push(make('forbidden_three',e.map(([a,b],i)=>b<3?0:i+1),e.map(()=>[0,0]),[0]));
    return out;
  };
  const canon=p=>p.resources.map(r=>Array.from(new Set(r)).sort((a,b)=>a-b));
  const order=p=>p.direct.map((_,i)=>i).sort((a,b)=>p.direct[a]-p.direct[b]||a-b);
  function group(ids,r){
    const g=new Map();
    for(const i of ids){const k=JSON.stringify(r[i]);if(!g.has(k))g.set(k,[]);if(g.get(k).length<4)g.get(k).push(i)}
    return Array.from(g.values());
  }
  function prune(ids,r){
    const retained=[],certificates=[];
    const sets=r.map(a=>new Set(a));let subsetTests=0;
    for(const k of ids){
      const witness=[];
      for(const j of retained){subsetTests++;if(r[j].length<=r[k].length&&r[j].every(x=>sets[k].has(x)))witness.push(j);if(witness.length===4)break}
      if(witness.length===4)certificates.push({k,witness});else retained.push(k);
    }
    return {retained,certificates,subsetTests};
  }
  function test(n,p){
    const e=edges(n),m=e.length,r=canon(p),ids=order(p),groups=group(ids,r);
    check(p.direct.every(d=>Number.isSafeInteger(d)&&d>=0)&&p.weights.every(w=>Number.isSafeInteger(w)&&w>=0),'cost domain');
    const pr=prune(ids,r),g2=group(pr.retained,r);
    for(const {k,witness} of pr.certificates){check(new Set(witness).size===4,'witness distinct');for(const j of witness){check(pr.retained.includes(j)&&ids.indexOf(j)<ids.indexOf(k)&&p.direct[j]<=p.direct[k]&&r[j].every(x=>r[k].includes(x)),'witness invalid')}}
    check(pr.retained.length+pr.certificates.length===m,'partition');
    const A=3*n**4-11*n**3+12*n*n-4*n,B=(n-2)*(12*n+6)+4*(n-2)*(n-3),T=12*n+6;
    const vm=e.map(([a,b])=>(1<<a)|(1<<b));
    const triangle=(v)=>(v&(v-1))!==0&&(()=>{let s=v,count=0;while(s){s&=s-1;count++}return count===3})();
    let cubic=0,grouped=0,pruned=0,pairs=0,optimum=Infinity;
    if(n>=4)for(let i=0;i<m;i++)for(let j=0;j<m;j++){
      if(i===j)continue;
      pairs++;
      const v=vm[i]|vm[j],coeff=triangle(v)?T:8,base=A*p.direct[i]+B*p.direct[j];
      const forbidden=k=>k===i||k===j||triangle(v|vm[k]);
      const cost=k=>{let c=base+coeff*p.direct[k];for(const x of new Set([...r[i],...r[j],...r[k]]))c+=p.weights[x];check(Number.isSafeInteger(c),'unsafe cost');return c};
      let a=Infinity,b=Infinity,c=Infinity;
      for(let k=0;k<m;k++)if(!forbidden(k)){cubic++;a=Math.min(a,cost(k))}
      for(const g of groups){const k=g.find(k=>!forbidden(k));if(k!==undefined){grouped++;b=Math.min(b,cost(k))}}
      for(const g of g2){const k=g.find(k=>!forbidden(k));if(k!==undefined){pruned++;c=Math.min(c,cost(k))}}
      check(a===b&&b===c,`pair mismatch ${n}/${p.name}/${i}/${j}`);optimum=Math.min(optimum,a);
    }
    check(pruned<=grouped&&grouped<=cubic,'objective count');
    if(n>=4&&p.name==='nested_unique'){check(pr.retained.length===4&&g2.length===4,'nested chain retention');check(pruned<grouped,'nested work reduction')}
    if(n>=4&&p.name==='nested_reverse_cost')check(pr.retained.length===m,'reverse cost negative control');
    if(n>=4&&p.name==='forbidden_three'){
      const first=e.findIndex(([a,b])=>a===0&&b===1),second=e.findIndex(([a,b])=>a===0&&b===2),close=e.findIndex(([a,b])=>a===1&&b===2);
      check([first,second,close].every(k=>pr.retained.slice(0,3).includes(k))&&pr.retained.length===4,'four witness necessity');
    }
    return {n,profile:p.name,rules:m,pairs,optimum:n<3?0:n===3?null:optimum,groups:groups.length,retained:pr.retained.length,remaining_groups:g2.length,subset_tests:pr.subsetTests,cubic_checks:cubic,grouped_checks:grouped,pruned_checks:pruned};
  }
  const rows=[];
  for(const n of [1,2,3,4,5,6,8,10])for(const p of profiles(n,edges(n)))rows.push(test(n,p));
  check(rows.length===104,'panel count');
  const frozen=[[21400,1980],[21400,1980],[0,1980],[21501,84420],[21498,11880],[50,3954],[637,1980],[1278,38858],[67,40526],[58,38752]];
  const n10=rows.filter(x=>x.n===10);
  frozen.forEach(([v,g],i)=>check(n10[i].optimum===v&&n10[i].cubic_checks===84420&&n10[i].grouped_checks===g,'frozen V3.8.23 disagreement'));
  return {source:'INTERNAL/AI_AUTHORED',reference_blob:'fea49f50bd55e72cc37c4535a9da66b52a3e232b',rows};
}
console.log(JSON.stringify(audit(),null,2));
