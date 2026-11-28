/* INTERNAL/AI_AUTHORED V3.8.23: exact resource-signature pruning of the
V3.8.22 ordered nontriangle triple objective. No new filter rules.
For a fixed first and second edge, the third-edge residual is positive
and fixed. At most three edges are forbidden: the first two and, when
adjacent, their unique triangle-closing edge. Group third-edge choices
by their exact canonical set of required setup resources. Within a group
the incremental setup charge is constant, so its cheapest admissible
direct-cost edge dominates every other edge in that group. Retaining
only the first four edges per group in (direct cost, index) order is
sufficient, even when all three forbidden edges are in that group.
Scanning the ordered first two edges and at most one candidate per
group gives O(m^2*g) complete cost evaluations after O(m log m) sorting
(excluding resource-set operations), g distinct resource signatures.
Worst case g=m; no general improvement over cubic is claimed. The
certificate counts complete objective evaluations, not instructions or
runtime. Reference cubic search shares the V3.8.22 objective; that
objective was separately verified previously. Tests are fixed abstract
profiles and n<=10, safe integer arithmetic; not an independent
historical test, no full-union equivalence or empirical coverage claim.
Run: node docs/research/experiments/quotient_grouped_order_v3823.js
*/
function edges(n){const out=[];for(let i=0;i<n;i++)for(let j=i+1;j<n;j++)out.push([i,j]);return out;}

function unionCost(ids,p){let total=0;const used=new Set();for(const i of ids)for(const r of p.resources[i])used.add(r);for(const r of used)total+=p.weights[r];return total;}

function residual(n){return [3*n**4-11*n**3+12*n*n-4*n,(n-2)*(12*n+6)+4*(n-2)*(n-3),12*n+6];}

function admissible(e,i,j,k){return i!==k&&j!==k&&new Set([...e[i],...e[j],...e[k]]).size!==3;}

function cubic(n,e,p){if(n<3)return {value:0,checks:0};if(n===3)return {value:null,checks:0};const [a,s,t]=residual(n);let value=Infinity,checks=0;for(let i=0;i<e.length;i++)for(let j=0;j<e.length;j++){if(i===j)continue;const r=new Set([...e[i],...e[j]]).size===3?t:8;for(let k=0;k<e.length;k++){if(!admissible(e,i,j,k))continue;checks++;value=Math.min(value,a*p.direct[i]+s*p.direct[j]+r*p.direct[k]+unionCost([i,j,k],p));}}return {value,checks};}

function grouped(n,e,p){if(n<3)return {value:0,checks:0,groups:0};if(n===3)return {value:null,checks:0,groups:0};const groups=new Map();for(let k=0;k<e.length;k++){const key=JSON.stringify([...new Set(p.resources[k])].sort((a,b)=>a-b));if(!groups.has(key))groups.set(key,[]);groups.get(key).push(k);}for(const [key,ids] of groups)groups.set(key,ids.sort((i,j)=>p.direct[i]-p.direct[j]||i-j).slice(0,4));const [a,s,t]=residual(n);let value=Infinity,checks=0;for(let i=0;i<e.length;i++)for(let j=0;j<e.length;j++){if(i===j)continue;const r=new Set([...e[i],...e[j]]).size===3?t:8;for(const ids of groups.values()){const k=ids.find(k=>admissible(e,i,j,k));if(k===undefined)continue;checks++;value=Math.min(value,a*p.direct[i]+s*p.direct[j]+r*p.direct[k]+unionCost([i,j,k],p));}}return {value,checks,groups:groups.size};}

function profiles(n,e){const m=e.length;const make=(name,direct,resources,weights)=>({name,direct,resources,weights});const out=[make('uniform',e.map(()=>1),e.map(()=>[]),[]),make('skew',e.map((_,i)=>1+(i*7)%13),e.map(()=>[]),[]),make('zero',e.map(()=>0),e.map(()=>[]),[]),make('endpoint',e.map((_,i)=>1+i%3),e.map(x=>x),Array.from({length:n},(_,i)=>20+i*3)),make('mixed',e.map((_,i)=>1+i%5),e.map(([a,b],i)=>[a%3,(b+i)%3]),[90,40,70]),make('setup_only',e.map(()=>0),e.map(([a,b])=>b<3?[]:[0]),[50])];out.push(make('triangle_first',e.map(([a,b])=>b<3?0:5),e.map(()=>[0,0]),[7]));for(let z=0;z<3;z++){let state=(3823+n*19+z*101)>>>0;const next=()=>{state=(Math.imul(1664525,state)+1013904223)>>>0;return state;};const direct=e.map(()=>next()%17),resources=e.map(()=>Array.from({length:3},()=>next()%5)),weights=Array.from({length:5},()=>next()%31);out.push(make('fixed_'+z,direct,resources,weights));}return out;}

function audit(){const rows=[];for(const n of [1,2,3,4,5,6,8,10]){const e=edges(n),cases=[];for(const p of profiles(n,e)){const a=cubic(n,e,p),b=grouped(n,e,p);if(a.value!==b.value||b.checks>a.checks)throw Error('mismatch '+n+' '+p.name);cases.push({profile:p.name,optimum:a.value,groups:b.groups,cubic_checks:a.checks,grouped_checks:b.checks});}rows.push({n,rules:e.length,cases});}const t=rows.find(r=>r.n===10);const u=t.cases.find(c=>c.profile==='uniform');if(u.grouped_checks!==1980||u.cubic_checks!==84420)throw Error('work count mismatch');return rows;}

console.log(JSON.stringify({source:'INTERNAL/AI_AUTHORED',audit:audit()}));
