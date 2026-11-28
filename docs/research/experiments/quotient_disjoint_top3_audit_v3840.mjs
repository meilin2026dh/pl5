/* INTERNAL/AI_AUTHORED V3.8.40 disjoint-pair order-statistic cache audit.
For disjoint edge pairs, the vertex union has >=4 vertices: the triangle
condition never excludes a third edge. Only the two selected IDs are forbidden.
For each paid resource set, retain any three distinct minimum-cost witnesses.
At least one survives two exclusions and its cost is the exact residual minimum.
Four-witness subset dominance and four-per-group retention preserve three
minimum costs, including ties. Lower-bound equality may skip ties only after
three distinct witnesses exist. No claim of lower running time or storage.
Compare all 13 frozen development profiles with V3.8.39 and the frozen solver.
The full per-candidate cost count includes all top-three construction work.
No history or production filtering changes. */
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
function audit(p,n,enabled){
const e=[];for(let a=0;a<n;a++)for(let b=a+1;b<n;b++)e.push([a,b]);
const m=e.length,mask=e.map(([a,b])=>(1<<a)|(1<<b)),triangle=v=>{let c=0;while(v){v&=v-1;c++;}return c===3;};
const r=p.resources.map(a=>[...new Set(a)].sort((a,b)=>a-b)),ids=p.direct.map((_,i)=>i).sort((a,b)=>p.direct[a]-p.direct[b]||a-b),sets=r.map(a=>new Set(a));
const A=3*n**4-11*n**3+12*n*n-4*n,B=(n-2)*(12*n+6)+4*(n-2)*(n-3),T=12*n+6;
if(!p.direct.every(x=>Number.isSafeInteger(x)&&x>=0)||!p.weights.every(x=>Number.isSafeInteger(x)&&x>=0)||!r.flat().every(x=>Number.isSafeInteger(x)&&x>=0&&x<p.weights.length))throw Error("invalid costs");
if(BigInt(A+B+Math.max(T,8))*BigInt(Math.max(...p.direct))+p.weights.reduce((a,x)=>a+BigInt(x),0n)>BigInt(Number.MAX_SAFE_INTEGER))throw Error("unsafe costs");
const retained=[];let subset_tests=0;for(const k of ids){let w=0;for(const j of retained){subset_tests++;if(r[j].length<=r[k].length&&r[j].every(x=>sets[k].has(x)))w++;if(w===4)break;}if(w<4)retained.push(k);}
const groups=new Map();for(const k of retained){const key=JSON.stringify(r[k]);if(!groups.has(key))groups.set(key,[]);if(groups.get(key).length<4)groups.get(key).push(k);}
const ordered=[...groups.values()].sort((a,b)=>p.direct[a[0]]-p.direct[b[0]]||a[0]-b[0]);
const values=new Array(m*(m-1)),triCache=new Map(),disCache=new Map();let searches=0,checks=0,visits=0,triHits=0,disHits=0,disPairs=0,lookupTests=0;
for(let i=0;i<m;i++)for(let j=i+1;j<m;j++){
const v=mask[i]|mask[j],tri=triangle(v),coeff=tri?T:8,paidSet=[...new Set([...r[i],...r[j]])].sort((a,b)=>a-b),paid=paidSet.reduce((s,x)=>s+p.weights[x],0);let best=Infinity;
const cost=k=>{checks++;return coeff*p.direct[k]+[...new Set([...paidSet,...r[k]])].reduce((s,x)=>s+p.weights[x],0);};
if(!tri)disPairs++;
if(!tri&&enabled){
const key=JSON.stringify(paidSet);let top=disCache.get(key);
if(top){disHits++;}else{
searches++;top=[];
for(const g of ordered){visits++;const bound=paid+coeff*p.direct[g[0]];if(top.length===3&&bound>=top[2].cost)break;
for(const k of g){if(top.length===3&&paid+coeff*p.direct[k]>=top[2].cost)break;top.push({k,cost:cost(k)});top.sort((a,b)=>a.cost-b.cost||a.k-b.k);if(top.length>3)top.pop();}}
if(top.length!==3)throw Error("missing three witnesses");disCache.set(key,top);
}
for(const x of top){lookupTests++;if(x.k!==i&&x.k!==j){best=x.cost;break;}}
}else{
const key=tri?JSON.stringify([v,paidSet]):null;
if(key!==null&&triCache.has(key)){best=triCache.get(key);triHits++;}
else{searches++;for(const g of ordered){visits++;if(paid+coeff*p.direct[g[0]]>=best)break;const k=g.find(k=>k!==i&&k!==j&&!triangle(v|mask[k]));if(k===undefined||paid+coeff*p.direct[k]>=best)continue;best=Math.min(best,cost(k));}if(key!==null)triCache.set(key,best);}
}
if(!Number.isSafeInteger(best))throw Error("invalid minimum");
values[i*(m-1)+j-1]=A*p.direct[i]+B*p.direct[j]+best;
values[j*(m-1)+i]=A*p.direct[j]+B*p.direct[i]+best;
}
return {values,searches,checks,visits,triHits,disHits,disPairs,lookupTests,disEntries:disCache.size,subset_tests};
}
function evaluate(frozen,reference){
const rows=frozen.profiles.map((p,i)=>{const a=audit(p,frozen.n,false),b=audit(p,frozen.n,true),ref=reference(p,frozen.n,i);
if(a.values.length!==1980||JSON.stringify(a.values)!==JSON.stringify(ref)||JSON.stringify(b.values)!==JSON.stringify(ref))throw Error("mismatch "+p.name);
if(a.disPairs!==630||b.disPairs!==630||b.disHits+b.disEntries!==630||a.searches-b.searches!==b.disHits||a.triHits!==b.triHits||a.subset_tests!==b.subset_tests)throw Error("ledger mismatch "+p.name);
return {profile:p.name,pairs:a.values.length,old_searches:a.searches,new_searches:b.searches,old_checks:a.checks,new_checks:b.checks,old_visits:a.visits,new_visits:b.visits,dis_pairs:b.disPairs,dis_hits:b.disHits,dis_entries:b.disEntries,lookup_tests:b.lookupTests,triangle_hits:b.triHits,subset_tests:b.subset_tests};});
const totals=Object.fromEntries(Object.keys(rows[0]).filter(k=>k!=="profile").map(k=>[k,rows.reduce((s,x)=>s+x[k],0)]));
if(totals.old_searches!==10626||totals.old_checks!==20529||totals.old_visits!==28087||totals.pairs!==25740||totals.triangle_hits!==2244||totals.subset_tests!==5557)throw Error("prior totals changed");
return {rows,totals};
}
const report=evaluate(frozen,(p,n,i)=>{const ref=frozen.solve(p,true);assert.equal(ref.optimum,frozen.expected[i][0]);return ref.values;});
assert.deepEqual(report.totals,{"pairs":25740,"old_searches":10626,"new_searches":2802,"old_checks":20529,"new_checks":9520,"old_visits":28087,"new_visits":11760,"dis_pairs":8190,"dis_hits":7824,"dis_entries":366,"lookup_tests":8873,"triangle_hits":2244,"subset_tests":5557});
console.log(JSON.stringify({source:'INTERNAL/AI_AUTHORED',source_blob:'c0492072047a10cc2e56a5fa61f45ea8bb322ba2',...report},null,2));
