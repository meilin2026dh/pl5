/* INTERNAL/AI_AUTHORED. V3.8.21: nonadditive cost boundary for an abstract
union-implication problem on elementary graph coarsenings.
V3.8.20 identifies nontriangle triples as all inclusion-minimal covers.
For any inclusion-monotone cost C, some minimum-cost cover is minimal:
delete redundant members without increasing cost until minimal. Thus
enumerating nontriangle triples suffices (O(m^3) cost evaluations, not
a general solver for arbitrary rule families).
Here C(S) = sum of nonnegative direct costs + nonnegative weights of
the union of resource sets; a shared resource is charged exactly once.
Ranking by singleton cost can be suboptimal, even in this monotone model.
The oracle uses union-find cycle detection on abstract five-symbol walks,
enumerates every portfolio for n<=6, and compares six fixed cost models.
No measured runtime, full-union equality or historical coverage claim.
Run: node docs/research/experiments/quotient_shared_cost_v3821.js
*/
function pairs(n){const e=[];for(let i=0;i<n;i++)for(let j=i+1;j<n;j++)e.push([i,j]);return e;}

function cycle(w){const parent=new Map();function root(a){if(!parent.has(a))parent.set(a,a);while(parent.get(a)!==a)a=parent.get(a);return a;}const seen=new Set();for(let i=1;i<w.length;i++){const a=w[i-1],b=w[i];if(a===b)continue;const k=[Math.min(a,b),Math.max(a,b)].join(',');if(seen.has(k))continue;seen.add(k);const x=root(a),y=root(b);if(x===y)return true;parent.set(x,y);}return false;}

function failures(n,e){const out=new Set();for(let k=0;k<n**5;k++){const w=[];let x=k;for(let i=0;i<5;i++){w.push(x%n);x=Math.floor(x/n);}if(!cycle(w))continue;let m=0;for(let i=0;i<e.length;i++){const [a,b]=e[i];if(!cycle(w.map(z=>z===b?a:z)))m|=1<<i;}out.add(m);}return [...out];}

function cost(ids,p){let c=0;const shared=new Set();for(const i of ids){c+=p.direct[i];for(const j of p.resources[i])shared.add(j);}for(const j of shared)c+=p.weights[j];return c;}

function nontriangle(e,t){return new Set(t.flatMap(i=>e[i])).size!==3;}

function exact(n,p){const e=pairs(n);if(n<3)return {ids:[],value:0};if(n===3)return null;let best=null;for(let i=0;i<e.length;i++)for(let j=i+1;j<e.length;j++)for(let k=j+1;k<e.length;k++){const ids=[i,j,k];if(!nontriangle(e,ids))continue;const value=cost(ids,p);if(best===null||value<best.value)best={ids,value};}return best;}

function singletonBaseline(n,p){const e=pairs(n);if(n<3)return {ids:[],value:0};if(n===3)return null;const order=e.map((_,i)=>i).sort((a,b)=>cost([a],p)-cost([b],p)||a-b);let ids=order.slice(0,3);if(!nontriangle(e,ids))ids=[order[0],order[1],order[3]];return {ids,value:cost(ids,p)};}

function profiles(n,e){const m=e.length;return [
 {name:'zero',direct:e.map(()=>0),resources:e.map(()=>[]),weights:[]},
 {name:'additive',direct:e.map((_,i)=>(i*7+2)%11),resources:e.map(()=>[]),weights:[]},
 {name:'global_setup',direct:e.map((_,i)=>i%4),resources:e.map(()=>[0]),weights:[13]},
 {name:'endpoint_setup',direct:e.map((_,i)=>i%3),resources:e.map(x=>x),weights:Array.from({length:n},(_,i)=>2+i%5)},
 {name:'mixed_setup',direct:e.map((_,i)=>i%5),resources:e.map(([a,b],i)=>[a%3,(b+i)%3]),weights:[2,7,11]},
 {name:'forced_overlap',direct:e.map(([a,b])=>b<3?4:0),resources:e.map(([a,b])=>b<3?[]:[0]),weights:[5]}
];}

function audit(){const rows=[];for(let n=1;n<=6;n++){const e=pairs(n),m=e.length,obs=failures(n,e),ps=profiles(n,e),oracle=ps.map(()=>Infinity);let feasible=0;for(let mask=0;mask<2**m;mask++){if(obs.some(f=>(mask&~f)===0))continue;feasible++;const ids=e.flatMap((_,i)=>(mask&(1<<i))?[i]:[]);for(let j=0;j<ps.length;j++)oracle[j]=Math.min(oracle[j],cost(ids,ps[j]));}const results=[];for(let j=0;j<ps.length;j++){const p=ps[j],x=exact(n,p),b=singletonBaseline(n,p);if(x===null){if(oracle[j]!==Infinity||b!==null)throw Error('infeasible mismatch');results.push({name:p.name,optimal:null,singleton:null});continue;}const mask=x.ids.reduce((s,i)=>s|(1<<i),0);if(obs.some(f=>(mask&~f)===0)||x.value!==oracle[j]||b.value<x.value)throw Error('minimum mismatch');results.push({name:p.name,optimal:x.value,singleton:b.value});}rows.push({n,portfolios:2**m,feasible,results});}const w=rows[3].results.find(x=>x.name==='forced_overlap');if(w.optimal!==5||w.singleton!==13)throw Error('counterexample mismatch');return rows;}

console.log(JSON.stringify({source:'INTERNAL/AI_AUTHORED',audit:audit()}));
