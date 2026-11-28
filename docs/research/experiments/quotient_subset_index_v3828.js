/* V3.8.28: cardinality-indexed four-witness preprocessing. Exact retention identity with V3.8.26, no timing claim. Counts exclude sorting, key construction and element-level membership work. Worst-case quadratic remains. */
function audit(){
  // INTERNAL/AI_AUTHORED; fixed synthetic resource configurations.
  // Sorted earlier retained edges only. Equal-cardinality subset iff identical
  // canonical signature. Count these via a map; scan strictly smaller buckets.
  // Thus the keep/remove decision is identical to the four-witness reference.
  // Subset predicate calls and bucket visits are separate, not runtime metrics.
  const check=(b,msg)=>{if(!b)throw Error(msg)};
  const edges=n=>{const a=[];for(let i=0;i<n;i++)for(let j=i+1;j<n;j++)a.push([i,j]);return a};
  function profiles(n,e){
    const make=(name,direct,resources,weights)=>({name,direct,resources,weights});
    const out=[make('uniform',e.map(()=>1),e.map(()=>[]),[]),make('skew',e.map((_,i)=>1+(i*7)%13),e.map(()=>[]),[]),make('zero',e.map(()=>0),e.map(()=>[]),[]),make('endpoint',e.map((_,i)=>1+i%3),e.map(x=>x),Array.from({length:n},(_,i)=>20+i*3)),make('mixed',e.map((_,i)=>1+i%5),e.map(([a,b],i)=>[a%3,(b+i)%3]),[90,40,70]),make('setup_only',e.map(()=>0),e.map(([a,b])=>b<3?[]:[0]),[50]),make('triangle_first',e.map(([a,b])=>b<3?0:5),e.map(()=>[0,0]),[7])];
    for(let z=0;z<3;z++){let state=(3823+n*19+z*101)>>>0;const next=()=>state=(Math.imul(1664525,state)+1013904223)>>>0;const d=e.map(()=>next()%17),r=e.map(()=>Array.from({length:3},()=>next()%5)),w=Array.from({length:5},()=>next()%31);out.push(make('fixed_'+z,d,r,w));}
    out.push(make('nested_unique',e.map((_,i)=>i),e.map((_,i)=>Array.from({length:i+1},(_,j)=>j)),e.map(()=>1)),make('nested_reverse_cost',e.map((_,i)=>e.length-i),e.map((_,i)=>Array.from({length:i+1},(_,j)=>j)),e.map(()=>1)),make('forbidden_three',e.map(([a,b],i)=>b<3?0:i+1),e.map(()=>[0,0]),[0]));
    return out;
  }
  function reference(ids,r){
    const retained=[],sets=r.map(a=>new Set(a));let tests=0,predicates=0;
    for(const k of ids){let w=0;for(const j of retained){tests++;if(r[j].length<=r[k].length){predicates++;if(r[j].every(x=>sets[k].has(x)))w++;}if(w===4)break;}if(w<4)retained.push(k);}
    return {retained,tests,predicates};
  }
  function indexed(ids,r){
    const retained=[],sets=r.map(a=>new Set(a)),keys=r.map(a=>JSON.stringify(a)),same=new Map(),buckets=new Map();
    let predicates=0,bucketVisits=0,lookups=0;
    for(const k of ids){const size=r[k].length,key=keys[k],eq=same.get(key)||0;lookups++;let w=eq;
      if(w<4){for(const [len,js] of buckets){bucketVisits++;if(len>=size)continue;for(const j of js){predicates++;if(r[j].every(x=>sets[k].has(x)))w++;if(w===4)break;}if(w===4)break;}}
      if(w<4){retained.push(k);same.set(key,eq+1);if(!buckets.has(size))buckets.set(size,[]);buckets.get(size).push(k);}
    }
    return {retained,predicates,bucketVisits,lookups};
  }
  function test(p){
    const r=p.resources.map(a=>[...new Set(a)].sort((a,b)=>a-b)),ids=p.direct.map((_,i)=>i).sort((a,b)=>p.direct[a]-p.direct[b]||a-b);
    const a=reference(ids,r),b=indexed(ids,r);
    check(JSON.stringify(a.retained)===JSON.stringify(b.retained),'retention mismatch '+p.name);
    return {profile:p.name,rules:ids.length,retained:a.retained.length,reference_tests:a.tests,reference_predicates:a.predicates,indexed_predicates:b.predicates,bucket_visits:b.bucketVisits,signature_lookups:b.lookups};
  }
  const rows=[];for(const n of [1,2,3,4,5,6,8,10])for(const p of profiles(n,edges(n)))rows.push({n,...test(p)});
  const frozen=rows.filter(x=>x.n===10);
  check(rows.length===104&&rows.reduce((s,x)=>s+x.reference_tests,0)===9857,'reference work disagreement');
  check(JSON.stringify(frozen.map(x=>x.retained))===JSON.stringify([4,4,4,45,16,5,4,31,29,27,4,45,4]),'reference retention disagreement');
  check(frozen.filter(x=>['uniform','skew','zero','endpoint','triangle_first','forbidden_three'].includes(x.profile)).every(x=>x.indexed_predicates===0),'equal-cardinality control');
  // Exhaustive small-domain cross-check: ordered length-5 sequences of subsets
  // of 2 resources, all equal direct costs. Reordering and duplicates in raw
  // signatures included through alternate encodings; no historical data.
  let exhaustive=0;
  for(let code=0;code<4**5;code++){
    let t=code;const resources=[];for(let i=0;i<5;i++){let bits=t%4;t=Math.floor(t/4);const a=[];if(bits&1)a.push(0);if(bits&2)a.push(1);if(i%2){a.reverse();if(a.length)a.push(a[0]);}resources.push(a);}
    test({name:'exhaustive_'+code,direct:[0,0,0,0,0],resources});exhaustive++;
  }
  const sum=k=>rows.reduce((s,x)=>s+x[k],0);
  return {source:'INTERNAL/AI_AUTHORED',reference_blob:'e7fa32e221924a07f132ff720092d1928bca9a7e',exhaustive,totals:Object.fromEntries(['reference_tests','reference_predicates','indexed_predicates','bucket_visits','signature_lookups'].map(k=>[k,sum(k)])),rows};
}
console.log(JSON.stringify(audit(),null,2));
