/* INTERNAL/AI_AUTHORED: cost audit only. Frozen V3.8.40 common evaluator.
   Two warmups and five alternating paired suite passes; verify every result.
   Separate fresh-process RSS observations, no speed/byte acceptance threshold.
   All input, code extraction, subprocess startup and verification outside timing.
   No new filtering rules or historical data changes. */
import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import os from 'node:os';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const dir=import.meta.url;
function pinned(name,sha){
  const s=fs.readFileSync(new URL(name,dir),'utf8').replace(/\r\n/g,'\n');
  const b=Buffer.from(s);assert.equal(crypto.createHash('sha1').update('blob '+b.length+'\0').update(b).digest('hex'),sha);return s;
}
function segment(s,a,b){assert.equal(s.split(a).length,2);assert.equal(s.split(b).length,2);assert.ok(s.indexOf(a)<s.indexOf(b));return s.slice(s.indexOf(a),s.indexOf(b));}
const frozenSource=pinned('./quotient_subset_benchmark_v3827.js','c0492072047a10cc2e56a5fa61f45ea8bb322ba2');
const source=pinned('./quotient_disjoint_top3_audit_v3840.mjs','d23548d83fe9102527e47f38fa4dadfd14beea1b');
const f=vm.compileFunction(segment(frozenSource,'const n=10,e=[];','const median=')+'\nreturn {n,profiles,expected,solve};',[])();
const audit=vm.compileFunction(segment(source,'function audit(p,n,enabled){','function evaluate(frozen,reference){')+'\nreturn audit;',[])();
const refs=f.profiles.map((p,i)=>{const r=f.solve(p,true);assert.equal(r.optimum,f.expected[i][0]);assert.equal(r.values.length,1980);return r.values;});
const methods=['baseline','top3'];
function run(method){
  const results=[];let ns=0;
  for(const p of f.profiles){const t=process.hrtime.bigint();const r=audit(p,f.n,method==='top3');const elapsed=Number(process.hrtime.bigint()-t);ns+=elapsed;results.push({r,elapsed});}
  for(let i=0;i<results.length;i++)assert.deepEqual(results[i].r.values,refs[i]);
  const checks=results.reduce((s,x)=>s+x.r.checks,0),entries=results.reduce((s,x)=>s+x.r.disEntries,0);
  assert.equal(checks,method==='top3'?9520:20529);assert.equal(entries,method==='top3'?366:0);
  return {ns,checks,entries,max_profile_entries:Math.max(...results.map(x=>x.r.disEntries)),profile_ns:results.map(x=>x.elapsed)};
}
if(process.argv.length===3){
  const method=process.argv[2];assert.ok(methods.includes(method));const before=process.resourceUsage().maxRSS;const r=run(method);console.log(JSON.stringify({method,before_max_rss_kib:before,after_max_rss_kib:process.resourceUsage().maxRSS,...r}));
}else{
  assert.equal(process.argv.length,2);for(let j=0;j<2;j++)for(const m of methods)run(m);
  const trials=[];for(let j=0;j<5;j++){const order=j%2===0?methods:[...methods].reverse();const row={order};for(const m of order)row[m]=run(m);trials.push(row);}
  const median=a=>[...a].sort((x,y)=>x-y)[Math.floor(a.length/2)];
  const rss=methods.map(m=>{const c=spawnSync(process.execPath,[fileURLToPath(import.meta.url),m],{encoding:'utf8',timeout:30000});assert.ifError(c.error);assert.equal(c.status,0,c.stderr);return JSON.parse(c.stdout);});
  console.log(JSON.stringify({classification:'INTERNAL/AI_AUTHORED',node:process.version,platform:process.platform,arch:process.arch,cpu:os.cpus()[0]?.model,profiles:f.profiles.map(p=>p.name),trials,median_paired_ratio:median(trials.map(t=>t.baseline.ns/t.top3.ns)),profile_median_ratios:f.profiles.map((p,i)=>({name:p.name,ratio:median(trials.map(t=>t.baseline.profile_ns[i]/t.top3.profile_ns[i]))})),rss,limitations:'Timing is sum of 13 full calls, not whole process. Fresh child maxRSS is process high-water mark, includes common reference, allocator and runtime; not isolated cache bytes. Only one RSS observation per arm. Frozen development profiles, no independent or historical evidence.'},null,2));
}
