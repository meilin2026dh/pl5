/* INTERNAL/AI_AUTHORED V3.8.34: exact lower-bound pruning of full combination cost evaluations.
Frozen V3.8.27 profiles, Set witness pruning retained as reference.
For a fixed ordered pair (i,j), base and already-paid resource union are fixed.
Nonnegative weights imply a lower bound base+paid+coeff*d(k).
Groups are sorted by minimum direct cost; all later groups have no smaller bound.
If bound >= incumbent, ties cannot improve the minimum value; no witness identity
or complete tie enumeration is promised. Within a group, its first feasible
member gives the minimum direct cost because resources are identical.
Exact arithmetic is restricted to the frozen safe-integer profiles.
No timing claim, no new rule, no historical input. Fixed 13-profile workload. */
import fs from 'node:fs';
import crypto from 'node:crypto';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const source=fs.readFileSync(new URL('./quotient_subset_benchmark_v3827.js',import.meta.url),'utf8').replace(/\r\n/g,'\n');
const bytes=Buffer.from(source,'utf8');
assert.equal(crypto.createHash('sha1').update('blob '+bytes.length+'\0').update(bytes).digest('hex'),'c0492072047a10cc2e56a5fa61f45ea8bb322ba2');
function audit(source,compile,eq,ok){
  function replace(s,a,b){eq(s.split(a).length,2);return s.replace(a,b)}
  const start="const n=10,e=[];",end="const median=";
  eq(source.split(start).length,2);eq(source.split(end).length,2);
  const solver=source.slice(source.indexOf(start),source.indexOf(end));
  const baseline=compile(solver+"\nreturn {profiles,expected,solve};")();
  let bounded=replace(solver,"let checks=0,optimum=Infinity;const values=[];","let checks=0,optimum=Infinity,group_visits=0,tail_skips=0,individual_skips=0;const values=[]; const ordered=[...groups.values()].sort((a,b)=>p.direct[a[0]]-p.direct[b[0]]||a[0]-b[0]);");
  bounded=replace(bounded,"let best=Infinity;\n    for(const g of groups.values()){","let best=Infinity;const paid=[...new Set([...r[i],...r[j]])].reduce((s,x)=>s+p.weights[x],0);\n    for(const [gi,g] of ordered.entries()){group_visits++;if(base+paid+coeff*p.direct[g[0]]>=best){tail_skips+=ordered.length-gi;break;}");
  bounded=replace(bounded,"if(k===undefined)continue;let c=base+coeff*p.direct[k];","if(k===undefined)continue;if(base+paid+coeff*p.direct[k]>=best){individual_skips++;continue;}let c=base+coeff*p.direct[k];");
  bounded=replace(bounded,"return {optimum,checks,subset_tests,values};","return {optimum,checks,subset_tests,values,group_visits,tail_skips,individual_skips};");
  const candidate=compile(bounded+"\nreturn {solve};")().solve;
  const rows=[];
  for(const [i,p] of baseline.profiles.entries()){
    ok(p.direct.every(x=>Number.isSafeInteger(x)&&x>=0));
    ok(p.weights.every(x=>Number.isSafeInteger(x)&&x>=0));
    ok(p.resources.flat().every(x=>Number.isSafeInteger(x)&&x>=0&&x<p.weights.length));
    const grouped=baseline.solve(p,false),ref=baseline.solve(p,true),got=candidate(p,true);
    eq([grouped.optimum,grouped.checks,ref.checks],baseline.expected[i]);
    eq(got.values.length,1980);ok(got.values.every(Number.isSafeInteger));
    eq(ref.values,grouped.values);eq(got.values,grouped.values);eq(got.optimum,grouped.optimum);
    eq(got.subset_tests,ref.subset_tests);ok(got.checks<=ref.checks);
    rows.push({profile:p.name,pairs:got.values.length,grouped_checks:grouped.checks,reference_checks:ref.checks,bounded_checks:got.checks,subset_tests:got.subset_tests,group_visits:got.group_visits,tail_skips:got.tail_skips,individual_skips:got.individual_skips});
  }
  const sum=k=>rows.reduce((s,x)=>s+x[k],0);
  eq(rows.length,13);eq(sum("pairs"),25740);eq(sum("grouped_checks"),397130);eq(sum("reference_checks"),302070);eq(sum("subset_tests"),5557);
  return {source:"INTERNAL/AI_AUTHORED",source_blob:"c0492072047a10cc2e56a5fa61f45ea8bb322ba2",rows,totals:Object.fromEntries(["pairs","grouped_checks","reference_checks","bounded_checks","subset_tests","group_visits","tail_skips","individual_skips"].map(k=>[k,sum(k)]))};
}
const result=audit(source,s=>vm.compileFunction(s,[]),assert.deepEqual,assert.ok);
assert.deepEqual(result.totals,{"pairs":25740,"grouped_checks":397130,"reference_checks":302070,"bounded_checks":52130,"subset_tests":5557,"group_visits":69910,"tail_skips":260700,"individual_skips":198});
console.log(JSON.stringify(result,null,2));
