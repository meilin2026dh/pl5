/* INTERNAL/AI_AUTHORED V3.8.30: exact 32-bit subset predicate.
Hypothesis: avoid signature indexing overhead by replacing Set membership
with a single bitwise subset operation when the resource universe fits.
Both paths preserve canonicalization, sort order, retained witnesses and
exact subset decisions; sparse IDs map injectively, 33+ IDs fall back.
Signed bit 31 is intentional; masks are consistently signed int32.
Compare with frozen V3.8.28 reference, not the slower cardinality index.
Five alternating pairs, batch 100, all 13 existing n=10 profiles, no speed
gate or full-flow speed claim. No fitted dispatch threshold. */
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
const masked=(ids,r)=>maskPrune(ids,r,reference);
function verify(p){
  const a=prepare(p,reference),b=prepare(p,masked);
  const {mode,...v}=b;
  assert.deepEqual(v,a);
  const distinct=new Set(p.resources.flat()).size;
  assert.equal(mode,distinct<=32?'mask32':'fallback');
  if(p.expectedMode)assert.equal(mode,p.expectedMode);
  return {a,b};
}
let cases=0,tests=0,predicates=0;
for(const n of [1,2,3,4,5,6,8,10])for(const p of profiles(n,edges(n))){
  const {a}=verify(p);cases++;tests+=a.tests;predicates+=a.predicates;
}
assert.deepEqual([cases,tests,predicates],[104,9857,7292]);
const extra=exhaustiveCases();for(const p of extra)verify(p);
assert.equal(extra.length,1024);
const boundary=boundaryCases().map(p=>{const {a,b}=verify(p);return {profile:p.name,mode:b.mode,retained:a.retained.length,tests:a.tests};});
assert.equal(boundary.length,12);
const n=10,batch_size=100,rows=[],f={reference,masked};
const expected=[[4,170,170],[4,170,170],[4,170,170],[45,990,990],[16,393,325],[5,170,168],[4,170,170],[31,692,548],[29,696,505],[27,606,481],[4,170,170],[45,990,0],[4,170,170]];
const median=a=>[...a].sort((a,b)=>a-b)[Math.floor(a.length/2)];
for(const [i,p] of profiles(n,edges(n)).entries()){
  const {a,b}=verify(p);
  assert.deepEqual([a.retained.length,a.tests,a.predicates],expected[i]);
  function batch(method){
    const results=new Array(batch_size),start=process.hrtime.bigint();
    for(let j=0;j<batch_size;j++)results[j]=prepare(p,f[method]);
    const ns=Number(process.hrtime.bigint()-start);
    for(const result of results)assert.deepEqual(result,method==='reference'?a:b);
    assert.ok(Number.isSafeInteger(ns)&&ns>0);
    return ns;
  }
  for(let j=0;j<2;j++)for(const method of ['reference','masked'])batch(method);
  const trials=[];
  for(let j=0;j<5;j++){
    const order=(i+j)%2===0?['reference','masked']:['masked','reference'],t={order};
    for(const method of order)t[method+'_ns']=batch(method);
    trials.push(t);
  }
  rows.push({profile:p.name,mode:b.mode,retained:a.retained.length,tests:a.tests,predicates:a.predicates,trials,median_paired_ratio:median(trials.map(t=>t.reference_ns/t.masked_ns))});
}
assert.equal(rows.length,13);
console.log(JSON.stringify({source:'INTERNAL/AI_AUTHORED',source_blob:blob,node:process.version,platform:process.platform,arch:process.arch,cpu:os.cpus()[0]?.model,cases,tests,predicates,exhaustive:extra.length,boundary,n,batch_size,rows},null,2));
