/* INTERNAL/AI_AUTHORED. V3.8.20: exact minimum-cost union-implication certificate
for abstract elementary graph coarsenings, based on V3.8.19.
For n>=3, a nonempty identity cycle set is covered iff the portfolio of
pair identifications is not contained in a triangle edge set or a pair of
disjoint edges. Every set of size <=2 is contained in such an obstruction.
A triple covers iff it is not a triangle; every set of at least four
distinct edges contains a nontriangle triple (two edges of a triangle
uniquely determine its third). Hence all inclusion-minimal covers are
nontriangle triples; their number is C(C(n,2),3)-C(n,3).
For n<3 the empty cover is uniquely minimal, and n=3 is infeasible.
For nonnegative additive integer costs, a minimum-cost cover may be chosen
minimal. Sort by cost and deterministic index. If the first three edges
are not a triangle they are optimal. Otherwise the best cover must include
an edge outside those three, so its cost is at least c1+c2+c4; the first
two and fourth attain that lower bound and are not a triangle.
This is a static implication task, not equality of the whole union;
it assumes additive nonnegative rule costs, not actual execution timing.
Run: node docs/research/experiments/quotient_minimal_portfolio_v3820.js
Independent oracle enumerates small abstract words using DFS cycle tests
and all portfolios; checks exact minima for six fixed cost profiles.
*/
function choose3(n){return n<3?0:n*(n-1)*(n-2)/6}

function pairs(n){let e=[];for(let i=0;i<n;i++)for(let j=i+1;j<n;j++)e.push([i,j]);return e}

function triangle(e,ids){return new Set(ids.flatMap(i=>e[i])).size===3}

function cheapest(n,costs){
 const e=pairs(n);
 if(costs.length!==e.length||costs.some(x=>!Number.isSafeInteger(x)||x<0)||!Number.isSafeInteger(costs.reduce((a,b)=>a+b,0)))throw Error('invalid nonnegative integer costs');
 if(n<3)return [];
 if(n===3)return null;
 const order=e.map((_,i)=>i).sort((a,b)=>costs[a]-costs[b]||a-b);
 const t=order.slice(0,3);
 return triangle(e,t)?[order[0],order[1],order[3]]:t;
}

function positive(w){
 const adj=new Map();
 for(let i=1;i<w.length;i++){const a=w[i-1],b=w[i];if(a===b)continue;if(!adj.has(a))adj.set(a,new Set());if(!adj.has(b))adj.set(b,new Set());adj.get(a).add(b);adj.get(b).add(a);}
 const seen=new Set();
 function visit(a,parent){seen.add(a);for(const b of adj.get(a)){if(b===parent)continue;if(seen.has(b)||visit(b,a))return true;}return false;}
 for(const a of adj.keys())if(!seen.has(a)&&visit(a,-1))return true;
 return false;
}

function audit(){
 const rows=[];
 for(let n=1;n<=6;n++){
  const e=pairs(n),m=e.length,failures=new Set();
  for(let k=0;k<n**5;k++){let x=k,w=[];for(let i=0;i<5;i++){w.push(x%n);x=Math.floor(x/n);}if(!positive(w))continue;
   let mask=0;for(let i=0;i<m;i++){const [a,b]=e[i];if(!positive(w.map(z=>z===b?a:z)))mask|=1<<i;}failures.add(mask);}
  const covered=p=>![...failures].some(f=>(p&~f)===0);
  const profiles=[e.map(()=>0),e.map(()=>1),e.map((_,i)=>i),e.map((_,i)=>m-i),e.map((_,i)=>(i*17+i*i*3)%11)];
  // Force the three cheapest edges to form a triangle when it exists.
  profiles.push(e.map(([a,b])=>b<3?0:9));
  const best=profiles.map(()=>Infinity);let minimal=0,valid=0;
  for(let p=0;p<(1<<m);p++){if(!covered(p))continue;valid++;let min=true;
   for(let i=0;i<m;i++)if((p&(1<<i))&&covered(p^(1<<i))){min=false;break;}
   if(min)minimal++;
   for(let j=0;j<profiles.length;j++){let c=0;for(let i=0;i<m;i++)if(p&(1<<i))c+=profiles[j][i];best[j]=Math.min(best[j],c);}
  }
  const expected=n<3?1:choose3(m)-choose3(n);if(minimal!==expected)throw Error('minimal count mismatch');
  for(let j=0;j<profiles.length;j++){const ids=cheapest(n,profiles[j]);if(ids===null){if(best[j]!==Infinity)throw Error('false infeasibility');continue;}const p=ids.reduce((s,i)=>s|(1<<i),0),c=ids.reduce((s,i)=>s+profiles[j][i],0);if(!covered(p)||c!==best[j])throw Error('cost mismatch');}
  rows.push({n,portfolios:2**m,valid,minimal,cost_profiles:profiles.length});
 }
 return rows;
}

console.log(JSON.stringify({source:'INTERNAL/AI_AUTHORED',audit:audit()}));
