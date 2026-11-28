/* INTERNAL/AI_AUTHORED V3.8.39: exact residual cache for triangle-union pair classes.
For intersecting distinct edges i,j, their union v has exactly 3 vertices.
The condition !triangle(v|mask[k]) already excludes i and j, so the feasible
set depends only on v. The residual coefficient is T and the resource union
cost depends only on the canonical paid resource set. Therefore cache key
(v, paid set) preserves the exact residual minimum. Disjoint pairs never
share this cache because their exclusions may differ. No timing claim.
Fixed 13-profile workload; cache-on and cache-off compared to prior ledger.
Only safe nonnegative integer costs. No new filtering rules or historical input. */
import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
const source=fs.readFileSync(new URL('./quotient_subset_benchmark_v3827.js',import.meta.url),'utf8').replace(/\r\n/g,'\n');
const bytes=Buffer.from(source,'utf8');
assert.equal(crypto.createHash('sha1').update('blob '+bytes.length+'\0').update(bytes).digest('hex'),'c0492072047a10cc2e56a5fa61f45ea8bb322ba2');
const start='const n=10,e=[];',end='const median=';
assert.equal(source.split(start).length,2);assert.equal(source.split(end).length,2);
const frozen=vm.compileFunction(source.slice(source.indexOf(start),source.indexOf(end))+'\nreturn {n,profiles,expected,solve};',[])();
function solve(p,n,cacheEnabled){
  const e=[];for(let a=0;a<n;a++)for(let b=a+1;b<n;b++)e.push([a,b]);
  const m=e.length,masks=e.map(([a,b])=>(1<<a)|(1<<b)),triangle=v=>{let c=0;while(v){v&=v-1;c++;}return c===3;};
  const r=p.resources.map(a=>[...new Set(a)].sort((a,b)=>a-b)),ids=p.direct.map((_,i)=>i).sort((a,b)=>p.direct[a]-p.direct[b]||a-b);
  const retained=[],sets=r.map(a=>new Set(a));let subset_tests=0;
  for(const k of ids){let witnesses=0;for(const j of retained){subset_tests++;if(r[j].length<=r[k].length&&r[j].every(x=>sets[k].has(x)))witnesses++;if(witnesses===4)break;}if(witnesses<4)retained.push(k);}
  const groups=new Map();for(const k of retained){const key=JSON.stringify(r[k]);if(!groups.has(key))groups.set(key,[]);if(groups.get(key).length<4)groups.get(key).push(k);}
  const ordered=[...groups.values()].sort((a,b)=>p.direct[a[0]]-p.direct[b[0]]||a[0]-b[0]);
  const A=3*n**4-11*n**3+12*n*n-4*n,B=(n-2)*(12*n+6)+4*(n-2)*(n-3),T=12*n+6;
  if(!p.direct.every(x=>Number.isSafeInteger(x)&&x>=0)||!p.weights.every(x=>Number.isSafeInteger(x)&&x>=0)||!p.resources.flat().every(x=>Number.isSafeInteger(x)&&x>=0&&x<p.weights.length))throw Error("invalid costs");
  const cap=BigInt(A+B+Math.max(T,8))*BigInt(Math.max(...p.direct))+p.weights.reduce((s,x)=>s+BigInt(x),0n);
  if(cap>BigInt(Number.MAX_SAFE_INTEGER))throw Error("unsafe costs");
  const values=new Array(m*(m-1)),cache=new Map();let searches=0,hits=0,checks=0,group_visits=0,triangle_pairs=0;
  for(let i=0;i<m;i++)for(let j=i+1;j<m;j++){
    const v=masks[i]|masks[j],tri=triangle(v),coeff=tri?T:8,paidSet=[...new Set([...r[i],...r[j]])].sort((a,b)=>a-b);
    if(tri)triangle_pairs++;
    const key=cacheEnabled&&tri?JSON.stringify([v,paidSet]):null;
    let best;
    if(key!==null&&cache.has(key)){best=cache.get(key);hits++;}
    else{
      searches++;best=Infinity;const paid=paidSet.reduce((s,x)=>s+p.weights[x],0);
      for(const g of ordered){group_visits++;if(paid+coeff*p.direct[g[0]]>=best)break;
        const k=g.find(k=>k!==i&&k!==j&&!triangle(v|masks[k]));if(k===undefined)continue;
        if(paid+coeff*p.direct[k]>=best)continue;
        let c=coeff*p.direct[k];for(const x of new Set([...paidSet,...r[k]]))c+=p.weights[x];
        checks++;best=Math.min(best,c);
      }
      if(key!==null)cache.set(key,best);
    }
    values[i*(m-1)+j-1]=A*p.direct[i]+B*p.direct[j]+best;
    values[j*(m-1)+i]=A*p.direct[j]+B*p.direct[i]+best;
  }
  return {values,optimum:Math.min(...values),searches,hits,checks,group_visits,subset_tests,triangle_pairs,cache_entries:cache.size};
}
const rows=frozen.profiles.map((p,i)=>{
  const ref=frozen.solve(p,true),a=solve(p,frozen.n,false),b=solve(p,frozen.n,true);
  assert.equal(ref.optimum,frozen.expected[i][0]);assert.deepEqual(a.values,ref.values);assert.deepEqual(b.values,ref.values);
  assert.ok(b.values.every(Number.isSafeInteger));assert.equal(a.searches,990);assert.equal(b.searches+b.hits,990);
  assert.equal(a.triangle_pairs,360);assert.equal(b.cache_entries+b.hits,360);
  assert.equal(a.subset_tests,b.subset_tests);assert.ok(b.checks<=a.checks);assert.ok(b.group_visits<=a.group_visits);
  return {profile:p.name,pairs:a.values.length,old_searches:a.searches,new_searches:b.searches,hits:b.hits,old_checks:a.checks,new_checks:b.checks,old_group_visits:a.group_visits,new_group_visits:b.group_visits,subset_tests:b.subset_tests,triangle_pairs:b.triangle_pairs,cache_entries:b.cache_entries};
});
const totals=Object.fromEntries(Object.keys(rows[0]).filter(k=>k!=='profile').map(k=>[k,rows.reduce((s,x)=>s+x[k],0)]));
assert.deepEqual(totals,{"pairs":25740,"old_searches":12870,"new_searches":10626,"hits":2244,"old_checks":26065,"new_checks":20529,"old_group_visits":34955,"new_group_visits":28087,"subset_tests":5557,"triangle_pairs":4680,"cache_entries":2436});
console.log(JSON.stringify({source:'INTERNAL/AI_AUTHORED',source_blob:'c0492072047a10cc2e56a5fa61f45ea8bb322ba2',rows,totals},null,2));
