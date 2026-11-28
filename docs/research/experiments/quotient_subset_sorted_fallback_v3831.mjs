/* INTERNAL/AI_AUTHORED V3.8.31: allocation-free sorted-array subset fallback.
For canonical sorted distinct numeric resource IDs, the monotone two-pointer
scan returns true iff every member of the first array occurs in the second.
Keep V3.8.30 dispatch and witness order unchanged. Count avoided fallback Set
constructions and element insertions, plus new element comparisons; these are
not memory or timing measurements. Worst-case scan may be slower than hashing.
No new filtering rules, no historical data, no timing gate. */
import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import os from 'node:os';
const blob='d7d9a4209293f0aec993f08f9c4afa67692f164b';
const source=fs.readFileSync(new URL('./quotient_subset_index_v3828.js',import.meta.url),'utf8').replace(/\r\n/g,'\n');
const bytes=Buffer.from(source,'utf8');
assert.equal(crypto.createHash('sha1').update('blob '+bytes.length+'\0').update(bytes).digest('hex'),blob);
const marker='  const rows=[];for(const n of';
assert.equal(source.split(marker).length,2);
const {edges,profiles,reference}=vm.compileFunction(source.slice(0,source.indexOf(marker))+'return {edges,profiles,reference};\n}\nreturn audit();',[])();
function maskPrune(ids,r,reference) {
  const map=new Map(), masks=[];
  for(const a of r){
    let mask=0;
    for(const x of a){
      if(!map.has(x)){
        if(map.size===32)return {...reference(ids,r),mode:'fallback'};
        map.set(x,map.size);
      }
      mask|=1<<map.get(x);
    }
    masks.push(mask);
  }
  const retained=[];let tests=0,predicates=0;
  for(const k of ids){
    let w=0;
    for(const j of retained){
      tests++;
      if(r[j].length<=r[k].length){
        predicates++;
        if((masks[j]&masks[k])===masks[j])w++;
      }
      if(w===4)break;
    }
    if(w<4)retained.push(k);
  }
  return {retained,tests,predicates,mode:'mask32'};
}
function prepare(p,fn){
  const r=p.resources.map(a=>[...new Set(a)].sort((a,b)=>a-b));
  const ids=p.direct.map((_,i)=>i).sort((a,b)=>p.direct[a]-p.direct[b]||a-b);
  return fn(ids,r);
}
function boundaryCases(){
  const cases=[];
  for(const count of [0,1,31,32,33,64]){
    const universe=Array.from({length:count},(_,i)=>1009*i+71);
    const last=universe.slice(-1);
    cases.push({name:'boundary_'+count,
      direct:[0,0,0,0,0,0,0,0],
      resources:[universe,[...last,...last],last,last,last,last,universe.slice().reverse(),[]],
      expectedMode:count<=32?'mask32':'fallback'});
    cases.push({name:'sparse_'+count,
      direct:[3,1,2,0,4,2,1,0],
      resources:[[],universe,...Array.from({length:6},(_,i)=>universe.filter((_,j)=>(i+j)%3===0).reverse())],
      expectedMode:count<=32?'mask32':'fallback'});
  }
  return cases;
}
function exhaustiveCases(){
  const out=[];
  for(let code=0;code<4**5;code++){
    let t=code;const resources=[];
    for(let i=0;i<5;i++){
      const bits=t%4;t=Math.floor(t/4);const a=[];
      if(bits&1)a.push(0);if(bits&2)a.push(1009);
      if(i%2){a.reverse();if(a.length)a.push(a[0]);}
      resources.push(a);
    }
    out.push({name:'exhaustive_'+code,direct:[0,0,0,0,0],resources,expectedMode:'mask32'});
  }
  return out;
}

function sortedFallback(ids,r,stats){
  const retained=[];let tests=0,predicates=0;
  function subset(a,b){
    let i=0,j=0;
    while(i<a.length&&j<b.length){
      stats.comparisons++;
      if(a[i]===b[j]){i++;j++;}
      else if(a[i]>b[j])j++;
      else return false;
    }
    return i===a.length;
  }
  for(const k of ids){
    let w=0;
    for(const j of retained){
      tests++;
      if(r[j].length<=r[k].length){
        predicates++;
        if(subset(r[j],r[k]))w++;
      }
      if(w===4)break;
    }
    if(w<4)retained.push(k);
  }
  return {retained,tests,predicates};
}
function verify(p){
  const baseline=prepare(p,(ids,r)=>maskPrune(ids,r,reference));
  const stats={comparisons:0,sets_avoided:0,elements_avoided:0};
  const actual=prepare(p,(ids,r)=>maskPrune(ids,r,(ids,r)=>{
    stats.sets_avoided=r.length;
    stats.elements_avoided=r.reduce((s,a)=>s+a.length,0);
    return sortedFallback(ids,r,stats);
  }));
  assert.deepEqual(actual,baseline);
  assert.equal(actual.mode,new Set(p.resources.flat()).size<=32?'mask32':'fallback');
  const {mode,...plain}=actual;
  assert.deepEqual(plain,prepare(p,reference));
  if(mode==='mask32')assert.deepEqual(stats,{comparisons:0,sets_avoided:0,elements_avoided:0});
  return {profile:p.name,mode,retained:actual.retained.length,tests:actual.tests,predicates:actual.predicates,...stats};
}
const rows=[];
for(const n of [1,2,3,4,5,6,8,10])for(const p of profiles(n,edges(n)))rows.push({n,...verify(p)});
const sum=(a,k)=>a.reduce((s,x)=>s+x[k],0);
assert.deepEqual([rows.length,sum(rows,'tests'),sum(rows,'predicates')],[104,9857,7292]);
const extra=exhaustiveCases();
for(const p of extra){
  verify(p);
  // Force the new fallback on all small-domain cases, regardless of dispatch.
  const stats={comparisons:0};
  assert.deepEqual(prepare(p,(ids,r)=>sortedFallback(ids,r,stats)),prepare(p,reference));
}
assert.equal(extra.length,1024);
const boundary=boundaryCases().map(verify);
assert.equal(boundary.length,12);
const distributed=[33,64].flatMap(count=>{
  const u=Array.from({length:count},(_,i)=>1009*i-50000);
  return [
    {name:'distributed_'+count,direct:u.map((_,i)=>i%3),resources:u.map((x,i)=>[x,u[(i+1)%count],x])},
    {name:'distributed_empty_'+count,direct:[0,0,0,0,...u.map(()=>1)],resources:[[],[],[],[],...u.map(x=>[x])]}
  ];
}).map(verify);
assert.ok(distributed.every(x=>x.mode==='fallback'));
const fallback=rows.filter(x=>x.mode==='fallback');
assert.deepEqual(fallback.map(x=>[x.n,x.profile]),[[10,'nested_unique'],[10,'nested_reverse_cost']]);
assert.deepEqual(fallback.map(x=>x.sets_avoided),[45,45]);
assert.equal(fallback[1].comparisons,0);
console.log(JSON.stringify({source:'INTERNAL/AI_AUTHORED',source_blob:blob,baseline_blob:'d6a5638fa51a30ef00442238e223ebb80b7e9dde',node:process.version,platform:process.platform,cases:rows.length,tests:sum(rows,'tests'),predicates:sum(rows,'predicates'),exhaustive:extra.length,boundary,distributed,fallback},null,2));
