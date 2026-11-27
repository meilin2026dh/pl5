/* INTERNAL/AI_AUTHORED V3.8.33: integrated combination-optimization cost.
Hypothesis: substituting the exact mask32/sorted fallback for the Set
witness search lowers total solve cost, not just preprocessing time.
The frozen V3.8.27 common evaluator, grouping, pair order, profiles and
objective remain unchanged. Both timed paths include normalization,
sorting, witness search, grouping, objective evaluations and result
allocation. Original unpruned grouping is an untimed equality oracle.
Two warm pairs, five alternating measured pairs per profile; same
13-profile/65-pair budget as V3.8.27. No fitted threshold or speed gate.
Not a production filtering pipeline or a new candidate compression rule. */
import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import os from 'node:os';
const source_blob='c0492072047a10cc2e56a5fa61f45ea8bb322ba2';
const fallback_blob='92c23dde66a3779ee792ad4830e9f2868f7765d4';
function frozen(name,blob){
  const s=fs.readFileSync(new URL(name,import.meta.url),'utf8').replace(/\r\n/g,'\n');
  const b=Buffer.from(s,'utf8');
  assert.equal(crypto.createHash('sha1').update('blob '+b.length+'\0').update(b).digest('hex'),blob);
  return s;
}
function build(source,fallback,compile){
  function extract(s,start,end){
    assert.equal(s.split(start).length,2);
    const a=s.indexOf(start),b=s.indexOf(end,a);
    assert.ok(b>a);return s.slice(a,b);
  }
  let kernel=extract(fallback,'function maskPrune','function verify(');
  const signature='function sortedFallback(ids,r,stats)',counter='      stats.comparisons++;\n';
  assert.equal(kernel.split(signature).length,2);
  assert.equal(kernel.split(counter).length,2);
  kernel=kernel.replace(signature,'function sortedFallback(ids,r)').replace(counter,'');
  const {maskPrune,sortedFallback}=compile(kernel+'\nreturn {maskPrune,sortedFallback};',[])();
  let solver=extract(source,'const n=10,e=[];','const median=');
  const marker='  if(pruned){';
  assert.equal(solver.split(marker).length,2);
  solver=solver.replace(marker,'  if(pruned==="hybrid"){const result=maskPrune(ids,r,sortedFallback);retained=result.retained;subset_tests=result.tests;}else if(pruned){');
  return compile(solver+'\nreturn {profiles,expected,solve};',['maskPrune','sortedFallback'])(maskPrune,sortedFallback);
}
function checkInputs(profiles,expected,solve){
  assert.equal(profiles.length,13);assert.equal(expected.length,13);
  const result=[];
  for(const [i,p] of profiles.entries()){
    const [optimum,grouped_checks,pruned_checks]=expected[i];
    const grouped=solve(p,false),reference=solve(p,true),hybrid=solve(p,'hybrid');
    assert.equal(grouped.values.length,1980);
    assert.ok(grouped.values.every(Number.isSafeInteger));
    assert.equal(grouped.optimum,optimum);assert.equal(grouped.checks,grouped_checks);
    assert.equal(reference.checks,pruned_checks);assert.equal(reference.optimum,optimum);
    assert.deepEqual(reference.values,grouped.values);
    assert.deepEqual(hybrid,reference);
    result.push({profile:p.name,optimum,grouped_checks,pruned_checks,subset_tests:reference.subset_tests,pairs:grouped.values.length,mode:new Set(p.resources.flat()).size<=32?'mask32':'fallback'});
  }
  assert.deepEqual(result.filter(x=>x.mode==='fallback').map(x=>x.profile),['nested_unique','nested_reverse_cost']);
  assert.equal(result.reduce((s,x)=>s+x.pairs,0),25740);
  assert.equal(result.reduce((s,x)=>s+x.grouped_checks,0),397130);
  assert.equal(result.reduce((s,x)=>s+x.pruned_checks,0),302070);
  assert.equal(result.reduce((s,x)=>s+x.subset_tests,0),5557);
  return result;
}
const source=frozen('./quotient_subset_benchmark_v3827.js',source_blob);
const fallback=frozen('./quotient_subset_sorted_fallback_v3831.mjs',fallback_blob);
const {profiles,expected,solve}=build(source,fallback,vm.compileFunction);
const fixed=checkInputs(profiles,expected,solve);
const median=a=>[...a].sort((x,y)=>x-y)[Math.floor(a.length/2)];
const rows=[];
for(const [i,p] of profiles.entries()){
  const oracle=solve(p,false),info=fixed[i];
  const orderFor=j=>(i+j)%2===0?['reference','hybrid']:['hybrid','reference'];
  function verify(r){
    assert.equal(r.optimum,info.optimum);
    assert.equal(r.checks,info.pruned_checks);
    assert.equal(r.subset_tests,info.subset_tests);
    assert.deepEqual(r.values,oracle.values);
  }
  function run(method){
    const start=process.hrtime.bigint();
    const r=solve(p,method==='reference'?true:'hybrid');
    const ns=Number(process.hrtime.bigint()-start);
    verify(r);assert.ok(Number.isSafeInteger(ns)&&ns>0);return ns;
  }
  for(let j=0;j<2;j++)for(const method of orderFor(j))run(method);
  const trials=[];
  for(let j=0;j<5;j++){
    const order=orderFor(j),t={order};
    for(const method of order)t[method+'_ns']=run(method);
    trials.push(t);
  }
  rows.push({...info,trials,median_paired_ratio:median(trials.map(t=>t.reference_ns/t.hybrid_ns))});
}
console.log(JSON.stringify({source:'INTERNAL/AI_AUTHORED',source_blob,fallback_blob,node:process.version,platform:process.platform,arch:process.arch,cpu:os.cpus()[0]?.model,warm_pairs:2,measured_pairs:5,rows},null,2));
