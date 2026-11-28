/* INTERNAL/AI_AUTHORED V3.8.29: paired preprocessing-only runtime audit.
Frozen V3.8.28 source; all 13 n=10 profiles, 2 warmups and 5 alternating
timed pairs of 100 invocations. Both paths include canonicalization, sorting,
all indexing/allocation, and storage of returned results. Inputs, source
loading and validation are outside timing. No timing gate or full-flow
speed claim. Same retained list and frozen counts checked on every call. */
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
const {edges,profiles,reference,indexed}=vm.compileFunction(source.slice(0,source.indexOf(marker))+'return {edges,profiles,reference,indexed};\n}\nreturn audit();',[])();
const expected=[['uniform',4,170,170,0,3,45],['skew',4,170,170,0,3,45],['zero',4,170,170,0,3,45],['endpoint',45,990,990,0,44,45],['mixed',16,393,325,90,74,45],['setup_only',5,170,168,84,46,45],['triangle_first',4,170,170,0,3,45],['fixed_0',31,692,548,187,86,45],['fixed_1',29,696,505,165,106,45],['fixed_2',27,606,481,205,107,45],['nested_unique',4,170,170,170,170,45],['nested_reverse_cost',45,990,0,0,990,45],['forbidden_three',4,170,170,0,3,45]];
const n=10,e=edges(n),batch_size=100,rows=[];
function prepare(p,fn){
  const r=p.resources.map(a=>[...new Set(a)].sort((a,b)=>a-b)),ids=p.direct.map((_,i)=>i).sort((a,b)=>p.direct[a]-p.direct[b]||a-b);
  return fn(ids,r);
}
const f={reference,indexed};
const median=a=>[...a].sort((a,b)=>a-b)[Math.floor(a.length/2)];
for(const [i,p] of profiles(n,e).entries()){
  const a=prepare(p,reference),b=prepare(p,indexed);
  assert.deepEqual(a.retained,b.retained);
  const counts=[p.name,a.retained.length,a.tests,a.predicates,b.predicates,b.bucketVisits,b.lookups];
  assert.deepEqual(counts,expected[i]);
  function batch(method,timed){
    const results=new Array(batch_size);
    const start=process.hrtime.bigint();
    for(let j=0;j<batch_size;j++)results[j]=prepare(p,f[method]);
    const ns=Number(process.hrtime.bigint()-start);
    for(const r of results)assert.deepEqual(r,method==='reference'?a:b);
    assert.ok(Number.isSafeInteger(ns)&&ns>0);
    return timed?ns:undefined;
  }
  for(let j=0;j<2;j++)for(const method of ['reference','indexed'])batch(method,false);
  const trials=[];
  for(let j=0;j<5;j++){
    const order=(i+j)%2===0?['reference','indexed']:['indexed','reference'],t={order};
    for(const method of order)t[method+'_ns']=batch(method,true);
    trials.push(t);
  }
  rows.push({profile:p.name,retained:a.retained.length,reference_tests:a.tests,reference_predicates:a.predicates,indexed_predicates:b.predicates,bucket_visits:b.bucketVisits,signature_lookups:b.lookups,trials,median_paired_ratio:median(trials.map(t=>t.reference_ns/t.indexed_ns))});
}
assert.equal(rows.length,13);
console.log(JSON.stringify({source:'INTERNAL/AI_AUTHORED',source_blob:blob,node:process.version,platform:process.platform,arch:process.arch,cpu:os.cpus()[0]?.model,n,batch_size,rows},null,2));
