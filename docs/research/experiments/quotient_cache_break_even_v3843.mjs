/* INTERNAL/AI_AUTHORED V3.8.43. One-task cache break-even accounting.
Pinned V3.8.27 and V3.8.40 sources. For each profile and disjoint paid-set key,
let q be query count, D = baseline full evaluations minus cached full
evaluations (including construction). If incremental non-evaluation overhead
is modeled as h*q+b in evaluation units, strict benefit iff D>h*q+b.
Sensitivity fixes b=0; h is illustrative, not calibrated. Negative keys
are retained. No dispatch policy, no actual timing claim, no new rules.
No historical data accessed. The existing CI workload is not enlarged.
Run: node docs/research/experiments/quotient_cache_break_even_v3843.mjs */
import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
function pinned(name,sha){
 const s=fs.readFileSync(new URL(name,import.meta.url),'utf8').replace(/\r\n/g,'\n');
 const b=Buffer.from(s);assert.equal(crypto.createHash('sha1').update('blob '+b.length+'\0').update(b).digest('hex'),sha);return s;
}
function analyze(frozenSource,source){
 const check=(x,m)=>{if(!x)throw Error(m)};
 const cut=(s,a,b)=>{check(s.split(a).length===2&&s.split(b).length===2&&s.indexOf(a)<s.indexOf(b),"source anchors");return s.slice(s.indexOf(a),s.indexOf(b));};
 const f=new Function(cut(frozenSource,"const n=10,e=[];","const median=")+"\nreturn {n,profiles,expected,solve};")();
 let body=cut(source,"function audit(p,n,enabled){","function evaluate(frozen,reference){");
 const replace=(a,b)=>{check(body.split(a).length===2,"instrument anchor "+a);body=body.replace(a,b)};
 replace("const values=new Array(m*(m-1)),","const ledger=new Map();const values=new Array(m*(m-1)),");
 replace("if(!tri)disPairs++;","const prev=[checks,visits,lookupTests,disCache.size];if(!tri)disPairs++;");
 replace("if(!Number.isSafeInteger(best))","if(!tri){const key=JSON.stringify(paidSet),row=ledger.get(key)||{queries:0,checks:0,visits:0,lookups:0,builds:0};row.queries++;row.checks+=checks-prev[0];row.visits+=visits-prev[1];row.lookups+=lookupTests-prev[2];row.builds+=disCache.size-prev[3];ledger.set(key,row);}\nif(!Number.isSafeInteger(best))");
 replace("return {values,searches,checks,visits,","return {ledger,values,searches,checks,visits,");
 const audit=new Function(body+"\nreturn audit;")();
 const total={keys:0,queries:0,oldChecks:0,newChecks:0,oldVisits:0,newVisits:0,lookups:0,builds:0,positive:0,tied:0,negative:0,singletons:0,singletonPositive:0};
 const penalties=[0,1,2,4,8];const sensitivity=penalties.map(h=>({h,allCacheNet:0,positiveKeys:0,oracleNet:0}));
 const rows=f.profiles.map((p,i)=>{
 const old=audit(p,f.n,false),cached=audit(p,f.n,true),ref=f.solve(p,true);
 check(ref.optimum===f.expected[i][0]&&ref.values.length===1980,"reference");
 check(JSON.stringify(old.values)===JSON.stringify(ref.values)&&JSON.stringify(cached.values)===JSON.stringify(ref.values),"exact costs "+p.name);
 check(old.ledger.size===cached.ledger.size&&cached.ledger.size===cached.disEntries,"keys");
 const t=Object.fromEntries(Object.keys(total).map(k=>[k,0]));
 for(const [key,x] of old.ledger){const y=cached.ledger.get(key);check(y&&x.queries===y.queries&&x.builds===0&&x.lookups===0&&y.builds===1&&y.lookups>=y.queries&&y.lookups<=3*y.queries,"ledger "+key);
 const d=x.checks-y.checks;t.keys++;t.queries+=x.queries;t.oldChecks+=x.checks;t.newChecks+=y.checks;t.oldVisits+=x.visits;t.newVisits+=y.visits;t.lookups+=y.lookups;t.builds+=y.builds;t[d>0?"positive":d===0?"tied":"negative"]++;if(x.queries===1){t.singletons++;if(d>0)t.singletonPositive++;}
 for(const z of sensitivity){const net=d-z.h*x.queries;z.allCacheNet+=net;if(net>0){z.positiveKeys++;z.oracleNet+=net;}}
 }
 check(t.queries===630&&t.builds===cached.disEntries&&t.lookups===cached.lookupTests&&old.checks-t.oldChecks===cached.checks-t.newChecks&&old.visits-t.oldVisits===cached.visits-t.newVisits,"reconciliation "+p.name);
 for(const k of Object.keys(total))total[k]+=t[k];return {profile:p.name,...t};
 });
 check(total.keys===366&&total.queries===8190&&total.oldChecks-total.newChecks===11009&&total.oldVisits-total.newVisits===16327&&total.lookups===8873,"frozen totals");
 check(total.positive+total.tied+total.negative===total.keys,"partition");
 check(sensitivity.every((x,i)=>i===0||x.allCacheNet<=sensitivity[i-1].allCacheNet&&x.positiveKeys<=sensitivity[i-1].positiveKeys&&x.oracleNet<=sensitivity[i-1].oracleNet),"monotonic overhead");
 return {classification:"INTERNAL/AI_AUTHORED",orderedPairs:25740,total,rows,sensitivity,limitations:"h is hypothetical extra cost per disjoint query in full-evaluation units, not a measured conversion. Build full evaluations already counted; non-evaluation build cost, visits, memory, and actual timing not priced. Oracle positive-key total uses observed costs and is not an implementable dispatch policy. Frozen development profiles only."};
}
const report=analyze(pinned('./quotient_subset_benchmark_v3827.js','c0492072047a10cc2e56a5fa61f45ea8bb322ba2'),pinned('./quotient_disjoint_top3_audit_v3840.mjs','d23548d83fe9102527e47f38fa4dadfd14beea1b'));
assert.deepEqual([report.total.positive,report.total.tied,report.total.negative,report.total.singletons,report.total.singletonPositive],[279,13,74,6,0]);
assert.deepEqual(report.sensitivity.map(x=>x.allCacheNet),[11009,2819,-5371,-21751,-54511]);
console.log(JSON.stringify(report,null,2));
