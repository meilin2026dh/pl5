/* V3.8.41 — Exact bounded-exclusion order-statistic cache theorem
INTERNAL/AI_AUTHORED; standalone finite audit; derived from
quotient_disjoint_top3_audit_v3840.mjs at 420cf3dafd1456ba7086de17cb6e3883bb13327a.

Theorem. Let E be a fixed finite eligible ID set and
c(i)=a*d(i)+sum_{u in P union S(i)} w(u), with a,d,w nonnegative.
For any integer k>=0,r>=1, q=k+r, cache the min(q,|E|) cheapest
distinct IDs (ties arbitrary). For every F subset E, |F|<=k, the
first min(r,|E minus F|) surviving costs are exactly recoverable.
Proof: if |E|<q all IDs are present. Otherwise at least q-k=r
cached IDs survive, each costing no more than any uncached ID.
Sorting survivors and taking r therefore returns the exact cost
multiset, not necessarily a uniquely prescribed ID tie-break.

Dominance construction: process E in increasing (d,ID) order;
discard i only if q distinct ALREADY RETAINED IDs have S(j) subset
S(i). For fixed P each such j costs <= c(i). Any discarded ID has
q retained witnesses no more expensive than itself, hence the
retained q smallest costs equal the global q smallest costs.
Keeping at most q IDs for an identical resource set follows the
same argument. This is a cost-multiset result, not arbitrary
query-dependent structural eligibility; construct E first or
separately prove an eligibility-preserving dominance relation.

Sharpness for a fixed cache of explicit ID witnesses with no
fallback: when |E|>=q, any cache of q-1 IDs can lose min(k,q-1)
of them and leave fewer than r while E minus F has >=r IDs.
This is NOT an information-theoretic lower bound on all data
structures or a claim that a q-cache minimizes total compute.
For |E|<q, storing all is sufficient; all-excluded queries are empty.

Finite test budget: 1152 states (all 3-ID binary direct/resource
assignments, all 1-resource paid sets, weights 0..2, coefficients
0..2), 14976 residual queries, 18 sharpness examples and 3 scope
negative controls. k=2,r=1 recovers the V3.8.40 cache bound.
The proof allows arbitrary finite resource sets; the bitmask test
harness is intentionally limited to the tiny finite domain.
No measured runtime/memory advantage; no changes to production
filter rules, historical data, or candidate compression.
Run: node docs/research/experiments/quotient_order_statistic_theorem_v3841.mjs
This iteration does not extend the existing cumulative CI workflow
because its Windows time limit has repeatedly been reached.
*/
function audit(){
  const check=(b,msg)=>{if(!b)throw Error(msg);};
  const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
  const cost=(x,P,w,a)=>a*x.d+w.reduce((s,v,i)=>s+(((P|x.S)&(1<<i))?v:0),0);
  const sort=(a,b)=>a.c-b.c||a.id-b.id;
  // Eligibility is fixed before pruning; unique integer IDs, nonnegative costs.
  function cache(items,P,w,a,q){
    const retained=[];const counts=new Map();
    for(const x of [...items].sort((x,y)=>x.d-y.d||x.id-y.id)){
      if(retained.filter(y=>(y.S&x.S)===y.S).length>=q)continue;
      if((counts.get(x.S)||0)>=q)continue;
      retained.push(x);counts.set(x.S,(counts.get(x.S)||0)+1);
    }
    return retained.map(x=>({id:x.id,c:cost(x,P,w,a)})).sort(sort).slice(0,q);
  }
  // Independent set-union and full sorting oracle.
  function oracle(items,P,w,a,F,r){
    return items.filter(x=>!F.has(x.id)).map(x=>{
      const union=new Set();
      for(let i=0;i<w.length;i++){if((P>>i)%2===1)union.add(i);if((x.S>>i)%2===1)union.add(i);}
      return a*x.d+[...union].reduce((s,i)=>s+w[i],0);
    }).sort((x,y)=>x-y).slice(0,r);
  }
  const query=(C,F,r)=>C.filter(x=>!F.has(x.id)).slice(0,r).map(x=>x.c);
  let states=0,queries=0,ties=0,pruned=0,empty=0;
  for(let z=0;z<64;z++){
    const items=Array.from({length:3},(_,id)=>({id,d:(z>>(2*id))&1,S:(z>>(2*id+1))&1}));
    for(let P=0;P<2;P++)for(let w=0;w<3;w++)for(let a=0;a<3;a++){
      states++;const full=oracle(items,P,[w],a,new Set(),3);if(new Set(full).size<3)ties++;
      const caches=Array.from({length:5},(_,q)=>q?cache(items,P,[w],a,q):[]);
      for(let Fmask=0;Fmask<8;Fmask++){
        const F=new Set(items.filter(x=>Fmask&(1<<x.id)).map(x=>x.id));
        for(let r=1;r<=Math.max(1,3-F.size);r++){
          const q=F.size+r,C=caches[q],expected=oracle(items,P,[w],a,F,r);
          check(equal(query(C,F,r),expected),"residual mismatch "+JSON.stringify({z,P,w,a,Fmask,r}));
          check(C.length===Math.min(q,items.length),"cache cardinality mismatch");
          queries++;if(expected.length===0)empty++;
          if(C.length<items.length)pruned++;
        }
      }
    }
  }
  // q-1 fixed ID witnesses cannot supply r survivors after arbitrary k deletions.
  let sharpness=0;
  for(let k=0;k<=5;k++)for(let r=1;r<=3;r++){
    const q=k+r,items=Array.from({length:q},(_,id)=>({id,d:id,S:0}));
    const C=cache(items,0,[0],1,q);
    const F=new Set(C.slice(0,k).map(x=>x.id));
    check(equal(query(C,F,r),oracle(items,0,[0],1,F,r)),"sharpness sufficient");
    check(!equal(query(C.slice(0,q-1),F,r),oracle(items,0,[0],1,F,r)),"sharpness necessary");
    sharpness++;
  }
  // Explicit scope violations: changing eligibility after pruning, negative resource
  // weight, and negative direct coefficient each break the dominance guarantee.
  const x=[{id:0,d:0,S:0},{id:1,d:1,S:1}];
  const wrong=cache(x,0,[0],1,1);
  check(wrong[0].id===0&&cache(x.slice(1),0,[0],1,1)[0].id===1,"eligibility witness");
  check(!equal(query(wrong,new Set([0]),1),oracle(x.slice(1),0,[0],1,new Set(),1)),"eligibility negative control");
  check(!equal(query(cache(x,0,[-2],1,1),new Set(),1),oracle(x,0,[-2],1,new Set(),1)),"negative resource control");
  check(!equal(query(cache(x,0,[0],-1,1),new Set(),1),oracle(x,0,[0],-1,new Set(),1)),"negative coefficient control");
  check(states===1152&&queries===14976&&sharpness===18&&empty===1152,"ledger mismatch");
  return {source:"INTERNAL/AI_AUTHORED",states,queries,tied_cost_states:ties,queries_with_short_cache:pruned,empty_queries:empty,sharpness_cases:sharpness,scope_negative_controls:3};
}
console.log(JSON.stringify(audit(),null,2));
