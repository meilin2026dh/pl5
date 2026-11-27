/* INTERNAL/AI_AUTHORED V3.8.38: exact exchange symmetry for combination optimization.
For a fixed ordered pair (i,j), write C(i,j,k)=A*d_i+B*d_j+R({i,j},k).
Feasibility of k, its coefficient, and its resource-union cost are invariant
under i<->j. Hence the minimum residual is shared by both orders. Search only
i<j and reconstruct both ordered minima, retaining every output ledger entry.
Nonnegative safe integer arithmetic verified conservatively on frozen profiles.
No identity of minimizing witnesses or universal runtime improvement is claimed.
One structural hypothesis; no timing trials, new filtering rule or historical input. */
import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
function frozen(path,blob){const s=fs.readFileSync(new URL(path,import.meta.url),'utf8').replace(/\r\n/g,'\n');const b=Buffer.from(s,'utf8');assert.equal(crypto.createHash('sha1').update('blob '+b.length+'\0').update(b).digest('hex'),blob);return s;}
const source=frozen('./quotient_subset_benchmark_v3827.js','c0492072047a10cc2e56a5fa61f45ea8bb322ba2');
const prior=frozen('./quotient_cost_lower_bound_v3834.mjs','4febd2b09abc3e95d40efb38dde40cdc983eb572');
function auditSymmetry(source,prior,compile,eq,ok){
  function replace(s,a,b){eq(s.split(a).length,2);return s.replace(a,b);}
  const begin='function audit(',end='const result=audit(';
  eq(prior.split(begin).length,2);eq(prior.split(end).length,2);
  let code=prior.slice(prior.indexOf(begin),prior.indexOf(end));
  const anchor='  const candidate=compile(bounded+"\\nreturn {solve};")().solve;';
  code=replace(code,anchor,anchor+'\n  const symmetric=compile(adapt(bounded)+"\\nreturn {solve};")().solve;');
  const marker='  }\n  const sum=k=>';
  code=replace(code,marker,'    check(p,grouped,got,symmetric);\n'+marker);
  function adapt(bounded){
    let x=replace(bounded,'const values=[];', 'const values=new Array(m*(m-1));let searches=0;');
    x=replace(x,'for(let i=0;i<m;i++)for(let j=0;j<m;j++){if(i===j)continue;', 'for(let i=0;i<m;i++)for(let j=i+1;j<m;j++){searches++;');
    x=replace(x,'values.push(best);optimum=Math.min(optimum,best);',
      'const reverse=A*p.direct[j]+B*p.direct[i]+(best-base);values[i*(m-1)+j-1]=best;values[j*(m-1)+i]=reverse;optimum=Math.min(optimum,best,reverse);');
    return replace(x,'return {optimum,checks,subset_tests,values,group_visits,tail_skips,individual_skips};',
      'return {optimum,checks,subset_tests,values,group_visits,tail_skips,individual_skips,searches};');
  }
  const rows=[];
  function check(p,grouped,old,symmetric){
    // All nonnegative safe integers, including a conservative bound on every sum.
    const n=10, A=3*n**4-11*n**3+12*n*n-4*n,B=(n-2)*(12*n+6)+4*(n-2)*(n-3),T=12*n+6;
    const cap=BigInt(A+B+Math.max(T,8))*BigInt(Math.max(...p.direct))+p.weights.reduce((s,x)=>s+BigInt(x),0n);
    ok(cap<=BigInt(Number.MAX_SAFE_INTEGER));
    const got=symmetric(p,true);
    eq(got.values.length,1980);ok(got.values.every(Number.isSafeInteger));
    eq(got.values,grouped.values);eq(got.values,old.values);eq(got.optimum,old.optimum);
    eq(got.searches,990);eq(got.subset_tests,old.subset_tests);
    for(const key of ['checks','group_visits','tail_skips','individual_skips'])eq(got[key]*2,old[key]);
    rows.push({profile:p.name,pairs:got.values.length,searches:got.searches,old_checks:old.checks,new_checks:got.checks,old_group_visits:old.group_visits,new_group_visits:got.group_visits,subset_tests:got.subset_tests});
  }
  const audit=compile(code+'\nreturn audit;',['adapt','check'])(adapt,check);
  const old=audit(source,s=>compile(s,[]),eq,ok);
  eq(old.totals,{pairs:25740,grouped_checks:397130,reference_checks:302070,bounded_checks:52130,subset_tests:5557,group_visits:69910,tail_skips:260700,individual_skips:198});
  eq(rows.length,13);
  const totals=Object.fromEntries(['pairs','searches','old_checks','new_checks','old_group_visits','new_group_visits','subset_tests'].map(k=>[k,rows.reduce((s,x)=>s+x[k],0)]));
  eq(totals,{pairs:25740,searches:12870,old_checks:52130,new_checks:26065,old_group_visits:69910,new_group_visits:34955,subset_tests:5557});
  return {source:'INTERNAL/AI_AUTHORED',source_blob:'c0492072047a10cc2e56a5fa61f45ea8bb322ba2',audit_blob:'4febd2b09abc3e95d40efb38dde40cdc983eb572',rows,totals};
}
console.log(JSON.stringify(auditSymmetry(source,prior,(s,args=[])=>vm.compileFunction(s,args),assert.deepEqual,assert.ok),null,2));
