/* INTERNAL/AI_AUTHORED V3.8.32: paired preprocessing cost audit.
Hypothesis: the exact sorted-array wide-resource fallback reduces actual
preprocessing time versus the frozen Set-based fallback. Fixed ten wide
profiles from V3.8.31, including zero-predicate and empty-resource controls.
Both paths include normalization, sorting, attempted mask construction,
dispatch and retained-witness search. Remove only the diagnostic comparison
counter from the sorted kernel before timing; no fitted threshold.
Five measured alternating pairs and two warm pairs, batch 100, all results
checked outside timing. No speed gate, no full-flow or cross-machine claim. */
import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import os from 'node:os';
function frozen(name,blob){
  const s=fs.readFileSync(new URL(name,import.meta.url),'utf8').replace(/\r\n/g,'\n');
  const b=Buffer.from(s,'utf8');
  assert.equal(crypto.createHash('sha1').update('blob '+b.length+'\0').update(b).digest('hex'),blob);
  return s;
}
const source_blob='d7d9a4209293f0aec993f08f9c4afa67692f164b';
const fallback_blob='92c23dde66a3779ee792ad4830e9f2868f7765d4';
const source=frozen('./quotient_subset_index_v3828.js',source_blob);
const s=frozen('./quotient_subset_sorted_fallback_v3831.mjs',fallback_blob);
const marker='  const rows=[];for(const n of';
assert.equal(source.split(marker).length,2);
const {edges,profiles,reference}=vm.compileFunction(source.slice(0,source.indexOf(marker))+'return {edges,profiles,reference};\n}\nreturn audit();',[])();
function extract(start,end){
  assert.equal(s.split(start).length,2);
  const a=s.indexOf(start), b=s.indexOf(end,a);
  assert.ok(b>a);
  return s.slice(a,b);
}
let kernel=extract('function maskPrune','function verify(');
const signature='function sortedFallback(ids,r,stats)',counter='      stats.comparisons++;\n';
assert.equal(kernel.split(signature).length,2);
assert.equal(kernel.split(counter).length,2);
kernel=kernel.replace(signature,'function sortedFallback(ids,r)').replace(counter,'');
const {maskPrune,prepare,boundaryCases,sortedFallback}=vm.compileFunction(kernel+'\nreturn {maskPrune,prepare,boundaryCases,sortedFallback};',['reference'])(reference);
const distributed=vm.compileFunction(extract('const distributed=[33,64]','}).map(verify);')+'});return distributed;',[])();
const cases=[
  ...profiles(10,edges(10)).filter(p=>['nested_unique','nested_reverse_cost'].includes(p.name)),
  ...boundaryCases().filter(p=>p.expectedMode==='fallback'),
  ...distributed
];
const expected=[
  ['nested_unique',4,170,170],['nested_reverse_cost',45,990,0],
  ['boundary_33',6,24,14],['sparse_33',8,28,18],
  ['boundary_64',6,24,14],['sparse_64',8,28,16],
  ['distributed_33',33,528,528],['distributed_empty_33',4,138,138],
  ['distributed_64',64,2016,2016],['distributed_empty_64',4,262,262]
];
assert.equal(cases.length,expected.length);
const methods={set:(ids,r)=>maskPrune(ids,r,reference),sorted:(ids,r)=>maskPrune(ids,r,sortedFallback)};
const batch_size=100,rows=[];
const median=a=>[...a].sort((a,b)=>a-b)[Math.floor(a.length/2)];
for(const [i,p] of cases.entries()){
  const a=prepare(p,methods.set),b=prepare(p,methods.sorted);
  assert.deepEqual(a,b);
  assert.equal(a.mode,'fallback');
  assert.deepEqual([p.name,a.retained.length,a.tests,a.predicates],expected[i]);
  function batch(method){
    const results=new Array(batch_size),start=process.hrtime.bigint();
    for(let j=0;j<batch_size;j++)results[j]=prepare(p,methods[method]);
    const ns=Number(process.hrtime.bigint()-start);
    for(const result of results)assert.deepEqual(result,a);
    assert.ok(Number.isSafeInteger(ns)&&ns>0);
    return ns;
  }
  for(let j=0;j<2;j++)for(const method of (i+j)%2===0?['set','sorted']:['sorted','set'])batch(method);
  const trials=[];
  for(let j=0;j<5;j++){
    const order=(i+j)%2===0?['set','sorted']:['sorted','set'],t={order};
    for(const method of order)t[method+'_ns']=batch(method);
    trials.push(t);
  }
  rows.push({profile:p.name,mode:a.mode,retained:a.retained.length,tests:a.tests,predicates:a.predicates,trials,median_paired_ratio:median(trials.map(t=>t.set_ns/t.sorted_ns))});
}
console.log(JSON.stringify({source:'INTERNAL/AI_AUTHORED',source_blob,fallback_blob,node:process.version,platform:process.platform,arch:process.arch,cpu:os.cpus()[0]?.model,batch_size,warm_pairs:2,measured_pairs:5,rows},null,2));
