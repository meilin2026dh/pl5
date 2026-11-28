/* INTERNAL/AI_AUTHORED V3.8.37: paired complete solve time for frozen
V3.8.36 structural dispatch versus V3.8.34 always-bounded combination optimization.
Hypothesis: skipping redundant singleton setup reduces complete solve time;
multi-group dispatch may incur overhead. Report both strata and all unfavorable
measurements. No tuning or speed gate. Reuse all V3.8.36 structural assertions.
Two warm pairs and five alternating measured pairs/profile; 65 measured pairs/OS.
Both paths include normalization, grouping, dominance, search, counters and result
allocation. Compilation, input preparation and verification outside timing.
Fixed development configurations; no independent or historical coverage evidence. */
import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import os from 'node:os';
const gate_blob='3a263dc8b943a4d02033f7ef8efd81bf4a98560e';
function frozen(path,blob){
  const s=fs.readFileSync(new URL(path,import.meta.url),'utf8').replace(/\r\n/g,'\n');
  const b=Buffer.from(s,'utf8');
  assert.equal(crypto.createHash('sha1').update('blob '+b.length+'\0').update(b).digest('hex'),blob);
  return s;
}
const source=frozen('./quotient_subset_benchmark_v3827.js','c0492072047a10cc2e56a5fa61f45ea8bb322ba2');
const prior=frozen('./quotient_cost_lower_bound_v3834.mjs','4febd2b09abc3e95d40efb38dde40cdc983eb572');
const gate=frozen('./quotient_cost_structural_gate_v3836.mjs',gate_blob);
const median=a=>[...a].sort((x,y)=>x-y)[Math.floor(a.length/2)];
function instrument(gate,eq){
  function replace(s,a,b){eq(s.split(a).length,2);return s.replace(a,b);}
  const begin='function gate(',end='const result=gate(';
  eq(gate.split(begin).length,2);eq(gate.split(end).length,2);
  let code=gate.slice(gate.indexOf(begin),gate.indexOf(end));
  code=replace(code,'check(i,p,grouped,ref,got,adaptive)','check(i,p,grouped,ref,got,adaptive,candidate)');
  code=replace(code,'function check(i,p,grouped,ref,old,adaptive){','function check(i,p,grouped,ref,old,adaptive,candidate){');
  code=replace(code,'paid_builds_avoided:got.values.length-got.paid_builds});','paid_builds_avoided:got.values.length-got.paid_builds});\n    Object.assign(rows[rows.length-1],measure(i,p,grouped,old,got,candidate,adaptive));');
  return code;
}
function measure(i,p,grouped,old,got,bounded,adaptive){
  const orderFor=j=>(i+j)%2===0?['bounded','adaptive']:['adaptive','bounded'];
  function run(method){
    const fn=method==='bounded'?bounded:adaptive;
    const start=process.hrtime.bigint();
    const value=fn(p,true);
    const ns=Number(process.hrtime.bigint()-start);
    assert.ok(Number.isSafeInteger(ns)&&ns>0);
    assert.deepEqual(value,method==='bounded'?old:got);
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
  return {trials,median_paired_ratio:median(trials.map(t=>t.bounded_ns/t.adaptive_ns))};
}
const run=vm.compileFunction(instrument(gate,assert.deepEqual)+'\nreturn gate;',['measure'])(measure);
const result=run(source,prior,(s,args=[])=>vm.compileFunction(s,args),assert.deepEqual,assert.ok);
assert.deepEqual(result.totals,{pairs:25740,reference_checks:302070,bounded_checks:52130,adaptive_checks:52130,paid_builds:15840,paid_builds_avoided:9900});
assert.equal(result.rows.filter(x=>x.route==='singleton').length,5);
assert.equal(result.rows.filter(x=>x.route==='bounded').length,8);
assert.equal(result.rows.reduce((s,x)=>s+x.trials.length,0),65);
for(const [i,x] of result.rows.entries()){
  assert.equal(x.trials.length,5);
  for(const [j,t] of x.trials.entries()){
    assert.deepEqual(t.order,(i+j)%2===0?['bounded','adaptive']:['adaptive','bounded']);
    for(const k of ['bounded_ns','adaptive_ns'])assert.ok(Number.isSafeInteger(t[k])&&t[k]>0);
  }
  assert.equal(x.median_paired_ratio,median(x.trials.map(t=>t.bounded_ns/t.adaptive_ns)));
}
console.log(JSON.stringify({...result,gate_blob,node:process.version,platform:process.platform,arch:process.arch,cpu:os.cpus()[0]?.model,warm_pairs:2,measured_pairs:5},null,2));
