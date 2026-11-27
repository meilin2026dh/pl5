/* INTERNAL/AI_AUTHORED V3.8.27: paired timing of V3.8.26 subset dominance.
Independent common evaluator, all 13 frozen n=10 profiles. Both paths include
canonicalization, sorting, grouping, search and pair-result allocation; the
pruned path also includes all subset tests. Input generation/verification
are outside timing. Fixed 2 warmups and 5 alternating-order pairs; no speed gate.
Reference: V3.8.26 blob e7fa32e221924a07f132ff720092d1928bca9a7e.
This measures this implementation, not the old interleaved audit or full workflow. */
const assert=require('node:assert/strict');
const os=require('node:os');
const n=10,e=[];for(let a=0;a<n;a++)for(let b=a+1;b<n;b++)e.push([a,b]);
const m=e.length,vm=e.map(([a,b])=>(1<<a)|(1<<b));
const make=(name,direct,resources,weights)=>({name,direct,resources,weights});
const profiles=[make('uniform',e.map(()=>1),e.map(()=>[]),[]),make('skew',e.map((_,i)=>1+(i*7)%13),e.map(()=>[]),[]),make('zero',e.map(()=>0),e.map(()=>[]),[]),make('endpoint',e.map((_,i)=>1+i%3),e.map(x=>x),Array.from({length:n},(_,i)=>20+i*3)),make('mixed',e.map((_,i)=>1+i%5),e.map(([a,b],i)=>[a%3,(b+i)%3]),[90,40,70]),make('setup_only',e.map(()=>0),e.map(([a,b])=>b<3?[]:[0]),[50]),make('triangle_first',e.map(([a,b])=>b<3?0:5),e.map(()=>[0,0]),[7])];
for(let z=0;z<3;z++){let state=(3823+n*19+z*101)>>>0;const next=()=>state=(Math.imul(1664525,state)+1013904223)>>>0;const direct=e.map(()=>next()%17),resources=e.map(()=>Array.from({length:3},()=>next()%5)),weights=Array.from({length:5},()=>next()%31);profiles.push(make('fixed_'+z,direct,resources,weights));}
profiles.push(make('nested_unique',e.map((_,i)=>i),e.map((_,i)=>Array.from({length:i+1},(_,j)=>j)),e.map(()=>1)),make('nested_reverse_cost',e.map((_,i)=>e.length-i),e.map((_,i)=>Array.from({length:i+1},(_,j)=>j)),e.map(()=>1)),make('forbidden_three',e.map(([a,b],i)=>b<3?0:i+1),e.map(()=>[0,0]),[0]));
const expected=[[21400,1980,1980],[21400,1980,1980],[0,1980,1980],[21501,84420,84420],[21498,11880,11670],[50,3954,3948],[637,1980,1980],[1278,38858,32814],[67,40526,36460],[58,38752,30934],[1487,84420,7504],[23173,84420,84420],[378,1980,1980]];
const triangle=v=>{let c=0;while(v){v&=v-1;c++;}return c===3;};
function solve(p,pruned){
  const r=p.resources.map(a=>[...new Set(a)].sort((a,b)=>a-b)),ids=p.direct.map((_,i)=>i).sort((a,b)=>p.direct[a]-p.direct[b]||a-b);
  let retained=ids,subset_tests=0;
  if(pruned){retained=[];const sets=r.map(a=>new Set(a));for(const k of ids){let witnesses=0;for(const j of retained){subset_tests++;if(r[j].length<=r[k].length&&r[j].every(x=>sets[k].has(x)))witnesses++;if(witnesses===4)break;}if(witnesses<4)retained.push(k);}}
  const groups=new Map();for(const k of retained){const key=JSON.stringify(r[k]);if(!groups.has(key))groups.set(key,[]);if(groups.get(key).length<4)groups.get(key).push(k);}
  const A=3*n**4-11*n**3+12*n*n-4*n,B=(n-2)*(12*n+6)+4*(n-2)*(n-3),T=12*n+6;
  let checks=0,optimum=Infinity;const values=[];
  for(let i=0;i<m;i++)for(let j=0;j<m;j++){if(i===j)continue;const v=vm[i]|vm[j],coeff=triangle(v)?T:8,base=A*p.direct[i]+B*p.direct[j];let best=Infinity;
    for(const g of groups.values()){const k=g.find(k=>k!==i&&k!==j&&!triangle(v|vm[k]));if(k===undefined)continue;let c=base+coeff*p.direct[k];for(const x of new Set([...r[i],...r[j],...r[k]]))c+=p.weights[x];checks++;best=Math.min(best,c);}
    values.push(best);optimum=Math.min(optimum,best);
  }
  return {optimum,checks,subset_tests,values};
}
const median=a=>[...a].sort((x,y)=>x-y)[Math.floor(a.length/2)];
const rows=[];
for(const [i,p] of profiles.entries()){
  const [optimum,grouped_checks,pruned_checks]=expected[i],baseline=solve(p,false),pruned=solve(p,true);
  assert.equal(baseline.values.length,1980);assert.ok(baseline.values.every(Number.isSafeInteger));assert.deepEqual(pruned.values,baseline.values);
  function verify(r,method){assert.equal(r.optimum,optimum);assert.equal(r.checks,method==='grouped'?grouped_checks:pruned_checks);assert.equal(r.subset_tests,method==='grouped'?0:pruned.subset_tests);assert.deepEqual(r.values,baseline.values);}
  verify(baseline,'grouped');verify(pruned,'pruned');
  for(let j=0;j<2;j++)for(const method of ['grouped','pruned'])verify(solve(p,method==='pruned'),method);
  const trials=[];
  for(let j=0;j<5;j++){const order=(i+j)%2===0?['grouped','pruned']:['pruned','grouped'],t={order};for(const method of order){const begin=process.hrtime.bigint(),r=solve(p,method==='pruned');t[method+'_ns']=Number(process.hrtime.bigint()-begin);verify(r,method);}trials.push(t);}
  rows.push({profile:p.name,optimum,grouped_checks,pruned_checks,subset_tests:pruned.subset_tests,pairs:baseline.values.length,trials,median_paired_ratio:median(trials.map(t=>t.grouped_ns/t.pruned_ns))});
}
console.log(JSON.stringify({source:'INTERNAL/AI_AUTHORED',reference_blob:'e7fa32e221924a07f132ff720092d1928bca9a7e',node:process.version,platform:process.platform,arch:process.arch,cpu:os.cpus()[0]?.model,n,rows},null,2));
