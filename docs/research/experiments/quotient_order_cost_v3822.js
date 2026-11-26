/* INTERNAL/AI_AUTHORED. V3.8.22: dynamic ordered cover certificate.
Scope: abstract length-five graph-cycle objects, elementary coarsenings.
Only the identity-positive target is processed; each rule removes its
positive objects from that target. Not a full-universe union equality.
Each positive object has a failure signature consisting of triangle edges
or the two diagonals of a four-cycle (V3.8.19). A triangle signature has
42 walks on its three vertices plus 12 per possible fourth tail vertex
(three attachment sites and four directed traversals per site). A diagonal
signature has eight four-cycle walks. Therefore the initial target has
A=3*n^4-11*n^3+12*n^2-4*n objects. After one rule the residual is
S=(n-2)*(12*n+6)+4*(n-2)*(n-3); after two distinct rules the residual
is 12*n+6 for adjacent edges and 8 for disjoint edges.
Every pair lies in exactly one failure signature. After a third rule
either the residual vanishes or that rule is the third triangle edge
and the residual is unchanged. Removing this ineffective third rule
and executing the fourth gives the same target coverage, no more direct
work and a subset of setup resources. Repeated rules are ineffective too.
Thus some minimum-cost successful order is an ordered nontriangle triple
for n>=4, assuming nonnegative per-object rule charges and nonnegative
one-time shared setup charges, with no evictions or order-dependent setup.
n<3 has empty target; n=3 is infeasible.
O(m^3) ordered-triple cost evaluations suffice, each including the union
of three resource sets. The independent oracle enumerates abstract walks
and all subset states using exact residual counts from observed signatures.
It does not use the closed-form multiplicities or triple restriction.
Bounded n<=6 audit, safe integer arithmetic within fixed profiles.
No measured runtime, candidate-set compression or historical coverage claim.
Run: node docs/research/experiments/quotient_order_cost_v3822.js
*/
function edges(n){const e=[];for(let i=0;i<n;i++)for(let j=i+1;j<n;j++)e.push([i,j]);return e;}

function cycle(w){const adj=new Map(),seen=new Set();for(let i=1;i<w.length;i++){const a=w[i-1],b=w[i];if(a===b)continue;if(!adj.has(a))adj.set(a,new Set());if(!adj.has(b))adj.set(b,new Set());adj.get(a).add(b);adj.get(b).add(a);}function dfs(a,p){seen.add(a);for(const b of adj.get(a)){if(b===p)continue;if(seen.has(b)||dfs(b,a))return true;}return false;}for(const a of adj.keys())if(!seen.has(a)&&dfs(a,-1))return true;return false;}

function observed(n,e){const h=new Map();for(let x=0;x<n**5;x++){let k=x,w=[];for(let i=0;i<5;i++){w.push(k%n);k=Math.floor(k/n);}if(!cycle(w))continue;let f=0;for(let j=0;j<e.length;j++){const [a,b]=e[j];if(!cycle(w.map(v=>v===b?a:v)))f|=1<<j;}h.set(f,(h.get(f)||0)+1);}return h;}

function signatureFormula(n,e){const h=new Map();if(n<3)return h;for(let i=0;i<e.length;i++)for(let j=i+1;j<e.length;j++){const a=e[i],b=e[j],v=[...new Set([...a,...b])].sort((x,y)=>x-y);if(v.length===4){h.set((1<<i)|(1<<j),8);}else{let f=0;for(let k=0;k<e.length;k++)if(e[k].every(x=>v.includes(x)))f|=1<<k;h.set(f,12*n+6);}}return h;}

function costs(e,n){return [{name:'uniform',direct:e.map(()=>1),resources:e.map(()=>[]),weights:[]},{name:'skew',direct:e.map((_,i)=>1+(i*7)%13),resources:e.map(()=>[]),weights:[]},{name:'zero',direct:e.map(()=>0),resources:e.map(()=>[]),weights:[]},{name:'endpoint',direct:e.map((_,i)=>1+i%3),resources:e.map(x=>x),weights:Array.from({length:n},(_,i)=>20+i*3)},{name:'mixed',direct:e.map((_,i)=>1+i%5),resources:e.map(([a,b],i)=>[a%3,(b+i)%3]),weights:[90,40,70]},{name:'setup_only',direct:e.map(()=>0),resources:e.map(([a,b])=>b<3?[]:[0]),weights:[50]}];}

function setup(ids,p){const r=new Set(ids.flatMap(i=>p.resources[i]));let v=0;for(const k of r)v+=p.weights[k];return v;}

function triple(n,e,p){if(n<3)return 0;if(n===3)return null;const t=12*n+6,s=(n-2)*t+4*(n-2)*(n-3),a=3*n**4-11*n**3+12*n*n-4*n;let best=Infinity;for(let i=0;i<e.length;i++)for(let j=0;j<e.length;j++){if(i===j)continue;const v=new Set([...e[i],...e[j]]),r=v.size===3?t:8;for(let k=0;k<e.length;k++){if(k===i||k===j)continue;if(v.size===3&&e[k].every(x=>v.has(x)))continue;best=Math.min(best,a*p.direct[i]+s*p.direct[j]+r*p.direct[k]+setup([i,j,k],p));}}return best;}

function oracle(e,h,p){const m=e.length,limit=1<<m,dp=new Float64Array(limit).fill(Infinity),remaining=new Int32Array(limit),paid=new Float64Array(limit);for(let s=0;s<limit;s++){for(const [f,c] of h)if((s&~f)===0)remaining[s]+=c;paid[s]=setup(e.flatMap((_,i)=>(s&(1<<i))?[i]:[]),p);}dp[0]=0;let best=Infinity;for(let s=0;s<limit;s++){if(dp[s]===Infinity)continue;if(remaining[s]===0){best=Math.min(best,dp[s]);continue;}for(let i=0;i<m;i++){const b=1<<i;if(s&b)continue;const next=s|b;dp[next]=Math.min(dp[next],dp[s]+remaining[s]*p.direct[i]+paid[next]-paid[s]);}}return Number.isFinite(best)?best:null;}

function audit(){const rows=[];for(let n=1;n<=6;n++){const e=edges(n),h=observed(n,e),f=signatureFormula(n,e);if(h.size!==f.size||[...h].some(([k,v])=>f.get(k)!==v))throw Error('signature mismatch '+n);const results=[];for(const p of costs(e,n)){const x=triple(n,e,p),y=oracle(e,h,p);if(x!==y)throw Error('cost mismatch '+n+' '+p.name+' '+x+' '+y);results.push({profile:p.name,cost:x});}rows.push({n,words:n**5,states:2**e.length,signatures:h.size,positive:[...h.values()].reduce((a,b)=>a+b,0),results});}return rows;}

console.log(JSON.stringify({source:'INTERNAL/AI_AUTHORED',audit:audit()}));
