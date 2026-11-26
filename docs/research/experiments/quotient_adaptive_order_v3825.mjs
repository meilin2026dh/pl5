/* INTERNAL/AI_AUTHORED: fixed structural dispatch, no fitted threshold.
If all canonical resource signatures differ, grouping cannot reduce complete
cost evaluations. Use cubic directly; otherwise keep the exact grouped search.
Dispatch scan is included in adaptive timing. No general runtime guarantee. */
import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import os from 'node:os';
const blob='fea49f50bd55e72cc37c4535a9da66b52a3e232b';
const source=fs.readFileSync(new URL('./quotient_grouped_order_v3823.js',import.meta.url),'utf8').replace(/\r\n/g,'\n');
const bytes=Buffer.from(source,'utf8');
assert.equal(crypto.createHash('sha1').update('blob '+bytes.length+'\0').update(bytes).digest('hex'),blob);
const suffix="console.log(JSON.stringify({source:'INTERNAL/AI_AUTHORED',audit:audit()}));\n";
assert.ok(source.endsWith(suffix));
const {edges,profiles,cubic,grouped}=vm.compileFunction(source.slice(0,-suffix.length)+'\nreturn {edges,profiles,cubic,grouped};',[])();
function select(n,p){
  if(n<=3)return 'cubic';
  const seen=new Set();
  for(const resources of p.resources){
    const key=JSON.stringify([...new Set(resources)].sort((a,b)=>a-b));
    if(seen.has(key))return 'grouped';
    seen.add(key);
  }
  return 'cubic';
}
function adaptive(n,e,p){const method=select(n,p);return {...(method==='cubic'?cubic:grouped)(n,e,p),method};}
const median=a=>[...a].sort((x,y)=>x-y)[Math.floor(a.length/2)];
const correctness=[];
for(const n of [1,2,3,4,5,6,8,10]){
  const e=edges(n),ps=profiles(n,e);
  if(n===4){const p={name:'canonical_collision',direct:e.map((_,i)=>i),resources:e.map((_,i)=>[i]),weights:e.map(()=>1)};p.resources[0]=[0,1,0];p.resources[1]=[1,0];ps.push(p);ps.push({...p,name:'canonical_distinct',resources:e.map((_,i)=>[i,i])});}
  for(const p of ps){const a=cubic(n,e,p),g=grouped(n,e,p),r=adaptive(n,e,p);const want=n<=3||g.groups===e.length?'cubic':'grouped';assert.equal(r.method,want);assert.equal(r.value,a.value);assert.equal(r.value,g.value);assert.equal(r.checks,g.checks);correctness.push({n,profile:p.name,method:r.method,optimum:r.value,checks:r.checks});}
}
assert.equal(correctness.length,82);
const n=10,e=edges(n),rows=[];
for(const p of profiles(n,e)){
  const baseline=grouped(n,e,p),method=select(n,p),f={grouped,adaptive};
  function check(name,r){assert.equal(r.value,baseline.value);assert.equal(r.checks,baseline.checks);if(name==='adaptive')assert.equal(r.method,method);}
  for(let i=0;i<3;i++)for(const name of ['grouped','adaptive'])check(name,f[name](n,e,p));
  const trials=[];
  for(let i=0;i<7;i++){const order=(i+rows.length)%2===0?['grouped','adaptive']:['adaptive','grouped'];const t={order};for(const name of order){const start=process.hrtime.bigint();const r=f[name](n,e,p);t[name+'_ns']=Number(process.hrtime.bigint()-start);check(name,r);}trials.push(t);}
  rows.push({profile:p.name,method,optimum:baseline.value,checks:baseline.checks,trials,median_paired_ratio:median(trials.map(t=>t.grouped_ns/t.adaptive_ns))});
}
console.log(JSON.stringify({source:'INTERNAL/AI_AUTHORED',source_blob:blob,node:process.version,platform:process.platform,arch:process.arch,cpu:os.cpus()[0]?.model,correctness,rows},null,2));
