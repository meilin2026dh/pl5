/* INTERNAL/AI_AUTHORED V3.8.35: paired timing of exact lower-bound pruning.
One hypothesis: fewer full cost evaluations can reduce complete solve time.
Frozen V3.8.27 profiles and V3.8.34 evaluator/counters; no tuning.
Both timed paths include all normalization, grouping, subset tests, search,
lower-bound setup where applicable, counters and result allocation.
Compilation, input preparation and verification are outside timing.
Two warm pairs and five alternating measured pairs per profile, 65 measured
pairs per platform. Every invocation checked against the frozen equality oracle.
No speed gate; retain every unfavorable observation. Not a production pipeline. */
import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import os from 'node:os';
const source_blob='c0492072047a10cc2e56a5fa61f45ea8bb322ba2';
const audit_blob='4febd2b09abc3e95d40efb38dde40cdc983eb572';
function frozen(path,blob){
  const s=fs.readFileSync(new URL(path,import.meta.url),'utf8').replace(/\r\n/g,'\n');
  const b=Buffer.from(s,'utf8');
  assert.equal(crypto.createHash('sha1').update('blob '+b.length+'\0').update(b).digest('hex'),blob);
  return s;
}
const source=frozen('./quotient_subset_benchmark_v3827.js',source_blob);
const prior=frozen('./quotient_cost_lower_bound_v3834.mjs',audit_blob);
const median=a=>[...a].sort((x,y)=>x-y)[Math.floor(a.length/2)];
function measure(i,p,grouped,ref,got,reference,candidate){
  const orderFor=j=>(i+j)%2===0?['reference','bounded']:['bounded','reference'];
  function run(method){
    const fn=method==='reference'?reference:candidate;
    const start=process.hrtime.bigint();
    const value=fn(p,true);
    const ns=Number(process.hrtime.bigint()-start);
    assert.ok(Number.isSafeInteger(ns)&&ns>0);
    assert.deepEqual(value,method==='reference'?ref:got);
    assert.deepEqual(value.values,grouped.values);
    return ns;
  }
  for(let j=0;j<2;j++)for(const method of orderFor(j))run(method);
  const trials=[];
  for(let j=0;j<5;j++){
    const order=orderFor(j),t={order};
    for(const method of order)t[method+'_ns']=run(method);
    trials.push(t);
  }
  return {trials,median_paired_ratio:median(trials.map(t=>t.reference_ns/t.bounded_ns))};
}
const begin='function audit(',end='const result=audit(',marker='  }\n  const sum=k=>';
assert.equal(prior.split(begin).length,2);
assert.equal(prior.split(end).length,2);
let code=prior.slice(prior.indexOf(begin),prior.indexOf(end));
assert.equal(code.split(marker).length,2);
code=code.replace(marker,'    Object.assign(rows[rows.length-1],measure(i,p,grouped,ref,got,baseline.solve,candidate));\n'+marker);
const audit=vm.compileFunction(code+'\nreturn audit;',['measure'])(measure);
const result=audit(source,s=>vm.compileFunction(s,[]),assert.deepEqual,assert.ok);
assert.deepEqual(result.totals,{pairs:25740,grouped_checks:397130,reference_checks:302070,bounded_checks:52130,subset_tests:5557,group_visits:69910,tail_skips:260700,individual_skips:198});
assert.deepEqual(result.rows.map(x=>x.bounded_checks),[1980,1980,1980,21886,3578,1980,1980,3456,2556,3364,1980,3430,1980]);
assert.equal(result.rows.reduce((s,x)=>s+x.trials.length,0),65);
console.log(JSON.stringify({...result,audit_blob,node:process.version,platform:process.platform,arch:process.arch,cpu:os.cpus()[0]?.model,warm_pairs:2,measured_pairs:5},null,2));
