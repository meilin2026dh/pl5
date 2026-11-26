# V3.8.2 — expression dimension versus input evaluation cost (2026-11-26)

Source: INTERNAL/AI_AUTHORED. Static aggregate mathematical audit only.

## Hypothesis and disposition

A lossless 11-coordinate linear expression might reduce the number of original rule responses needed for full expression. Under the fixed black-box input model this is false. Do not promote the re-encoding to a default filtering algorithm on the strength of the dimension result.

## Proof

Let R be a finite realized signature set. Coordinate j is essential when R contains two rows differing only at j. Any function injective on R must distinguish those two rows, so it cannot be independent of j on R. For a fixed GF(2) linear map, if column j is zero then the pair has identical outputs, a contradiction. Thus all essential input coordinates must occur in a lossless fixed expression. This also applies to fixed nonlinear expressions that globally omit an input coordinate. It is not a per-row lower bound for adaptive evaluations.

V3.8.1 establishes twelve essential coordinates for the frozen inventory. V3.8.2 establishes eleven output bits are sufficient. Therefore all twelve original response bits are still required as dependencies of a fixed lossless re-encoding; eleven output bits alone do not establish a reduction from twelve original rule evaluations. At least one output parity must combine two or more inputs, by counting dependencies. This statement does not quantify elapsed time, shared intermediate calculations, adaptive evaluations, fused formulas, packing, or downstream query costs.

## Independent small-cube falsification test

Run with Node.js (no dependencies, all 255 nonempty subsets of a three-dimensional binary cube, all 64 linear maps to two dimensions, including rank-deficient maps):

```sh
node <<'JS'
let tests=0,violations=0,injective=0;
for(let mask=1;mask<256;mask++){
  const rows=Array.from({length:8},(_,i)=>i).filter(i=>(mask>>i)&1);
  let essential=0;
  for(let j=0;j<3;j++)
    if(rows.some(x=>rows.includes(x^(1<<j))))essential|=1<<j;
  for(let a=0;a<8;a++)for(let b=0;b<8;b++){
    tests++;
    const parity=x=>((x^(x>>1)^(x>>2))&1);
    if(new Set(rows.map(x=>parity(x&a)+2*parity(x&b))).size===rows.length){
      injective++;
      if((essential&~(a|b))!==0)violations++;
    }
  }
}
console.log({tests,injective,violations});
if(tests!==16320||injective!==3872||violations!==0)process.exit(1);
JS
```

Observed in an independent JavaScript execution: 16,320 cases, 3,872 injective maps across subsets, zero violations. Synthetic verification only; not a third-party test.

## Frozen evidence and reproducibility

- V3.8.1: 1,079 occupied classes; 12 essential coordinates; sole sufficient original subset is all 12. SHA 110b370455b8a982da792558486e9e90983423d9. [CI](https://github.com/meilin2026dh/pl5/actions/runs/45737783058). Reproduce: python docs/research/experiments/boolean_rank_v3801.py
- V3.8.2: 4,095 kernels, 116 collision-free, 3,979 colliding, 581,581 unordered class pairs. SHA 571f9cd25734360c4aa910f8fd1cf777709e5884. [CI](https://github.com/meilin2026dh/pl5/actions/runs/45750233475). Reproduce: python docs/research/experiments/linear_quotient_v3802.py
- Ubuntu and Windows jobs 139675966277 and 139675966568 completed successfully, five tests each; full JSON reports identical, including mask digests. [Application checks](https://github.com/meilin2026dh/pl5/actions/runs/45750233465) successful.
- main observed at c0e38040ec5f389d6444e64b90e7adc42adfca62; PR #11 head b5687f5e848d1fab567fcd15d8b1eb51d9e3b651 (5/5 workflows successful); PR #13 head 53425be6a80533c219f097e023209776b3330f24 (10/10 workflows successful). Both draft; Issue #12 open.

## Failure lineage and limits

Record as a negative result for the fixed-input evaluation-cost hypothesis, not as a failure of the dimension theorem. Preserve original implementation. Mathematical expression compression is not candidate set compression. No new filtering rule, marginal exclusion gain, historical coverage, timing speedup or cross-platform acceptance of this new note is claimed. No historical inputs used. No change to main or production filtering behavior.
