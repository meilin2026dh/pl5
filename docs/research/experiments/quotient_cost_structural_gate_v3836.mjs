/* INTERNAL/AI_AUTHORED V3.8.36: structural singleton-group gate for exact combination optimization.
Hypothesis: when dominance pruning leaves exactly one canonical resource group,
lower-bound setup cannot avoid a complete cost evaluation. There is at most one
first feasible member to evaluate; the incumbent starts at Infinity. Therefore
skip the bound setup in that case, preserving the frozen exact minimum per pair.
Other structures retain the V3.8.34 bounded path. No profile-name or timing
thresholds. This tests structural work, not wall-clock acceleration. No history,
new filtering rules, candidate compression or external evidence. */
import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
function frozen(path,blob){const s=fs.readFileSync(new URL(path,import.meta.url),'utf8').replace(/\r\n/g,'\n');const b=Buffer.from(s,'utf8');assert.equal(crypto.createHash('sha1').update('blob '+b.length+'\0').update(b).digest('hex'),blob);return s;}
const source=frozen('./quotient_subset_benchmark_v3827.js','c0492072047a10cc2e56a5fa61f45ea8bb322ba2');
const prior=frozen('./quotient_cost_lower_bound_v3834.mjs','4febd2b09abc3e95d40efb38dde40cdc983eb572');
function gate(source,prior,compile,eq,ok){
  // Build the original bounded evaluator from its frozen source, retaining all its checks.
  function replace(s,a,b){eq(s.split(a).length,2);return s.replace(a,b);}
  const begin='function audit(',end='const result=audit(';
  eq(prior.split(begin).length,2);eq(prior.split(end).length,2);
  let code=prior.slice(prior.indexOf(begin),prior.indexOf(end));
  const solverAnchor='  const candidate=compile(bounded+"\\nreturn {solve};")().solve;';
  code=replace(code,solverAnchor,solverAnchor+'\n  const adaptive=compile(adapt(bounded)+"\\nreturn {solve};")().solve;');
  const marker='  }\n  const sum=k=>';
  code=replace(code,marker,'    check(i,p,grouped,ref,got,adaptive);\n'+marker);
  function adapt(bounded){
    let x=replace(bounded,
      'const ordered=[...groups.values()].sort((a,b)=>p.direct[a[0]]-p.direct[b[0]]||a[0]-b[0]);',
      'const one=groups.size===1?groups.values().next().value:null;const ordered=one?null:[...groups.values()].sort((a,b)=>p.direct[a[0]]-p.direct[b[0]]||a[0]-b[0]);let paid_builds=0;');
    x=replace(x,
      'let best=Infinity;const paid=[...new Set([...r[i],...r[j]])].reduce((s,x)=>s+p.weights[x],0);',
      'let best=Infinity;if(one){group_visits++;const k=one.find(k=>k!==i&&k!==j&&!triangle(v|vm[k]));if(k!==undefined){let c=base+coeff*p.direct[k];for(const x of new Set([...r[i],...r[j],...r[k]]))c+=p.weights[x];checks++;best=c;}}else{paid_builds++;const paid=[...new Set([...r[i],...r[j]])].reduce((s,x)=>s+p.weights[x],0);');
    x=replace(x,'best=Math.min(best,c);}\n    values.push(best);','best=Math.min(best,c);}}\n    values.push(best);');
    return replace(x,'return {optimum,checks,subset_tests,values,group_visits,tail_skips,individual_skips};',
      'return {optimum,checks,subset_tests,values,group_visits,tail_skips,individual_skips,paid_builds,groups_count:groups.size,route:one?"singleton":"bounded"};');
  }
  const rows=[];
  function check(i,p,grouped,ref,old,adaptive){
    const got=adaptive(p,true);
    eq(got.values,grouped.values);eq(got.values,old.values);eq(got.optimum,ref.optimum);
    for(const key of ['checks','subset_tests','group_visits','tail_skips','individual_skips'])eq(got[key],old[key]);
    ok(got.groups_count>0);
    eq(got.route,got.groups_count===1?'singleton':'bounded');
    eq(got.paid_builds,got.route==='singleton'?0:got.values.length);
    if(got.route==='singleton'){eq(got.checks,ref.checks);eq(got.tail_skips,0);eq(got.individual_skips,0);}
    rows.push({profile:p.name,groups:got.groups_count,route:got.route,pairs:got.values.length,reference_checks:ref.checks,bounded_checks:old.checks,adaptive_checks:got.checks,paid_builds:got.paid_builds,paid_builds_avoided:got.values.length-got.paid_builds});
  }
  const audit=compile(code+'\nreturn audit;',['adapt','check'])(adapt,check);
  const old=audit(source,s=>compile(s,[]),eq,ok);
  eq(old.totals,{pairs:25740,grouped_checks:397130,reference_checks:302070,bounded_checks:52130,subset_tests:5557,group_visits:69910,tail_skips:260700,individual_skips:198});
  eq(rows.length,13);
  eq(rows.map(x=>x.adaptive_checks),[1980,1980,1980,21886,3578,1980,1980,3456,2556,3364,1980,3430,1980]);
  const total=k=>rows.reduce((s,x)=>s+x[k],0);
  eq(total('pairs'),25740);eq(total('adaptive_checks'),52130);
  return {source:'INTERNAL/AI_AUTHORED',source_blob:'c0492072047a10cc2e56a5fa61f45ea8bb322ba2',audit_blob:'4febd2b09abc3e95d40efb38dde40cdc983eb572',rows,totals:Object.fromEntries(['pairs','reference_checks','bounded_checks','adaptive_checks','paid_builds','paid_builds_avoided'].map(k=>[k,total(k)]))};
}
const result=gate(source,prior,(s,args=[])=>vm.compileFunction(s,args),assert.deepEqual,assert.ok);
console.log(JSON.stringify(result,null,2));
