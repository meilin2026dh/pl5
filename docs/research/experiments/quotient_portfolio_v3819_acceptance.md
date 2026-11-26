# V3.8.19 collective filtering-rule redundancy: acceptance record

INTERNAL/AI_AUTHORED. Evidence collected 2026-11-27 (Asia/Shanghai).

- Source commit: 00d451160edb628eeeb072e588ea44735c1ac822
- Tested workflow head: 856a4788f670cf292a04a754eee81e12738f5551
- Source blob at tested head: a7a8d6472ff668e4007c628bd34f1574c65ac53b
- Reproduce: `python docs/research/experiments/quotient_portfolio_v3819.py`
- Specialized workflow: https://github.com/meilin2026dh/pl5/actions/runs/45875384817 (success)
- Application checks: https://github.com/meilin2026dh/pl5/actions/runs/45875384849 (success)

Both job records explicitly mark step 40, V3.8.19 collective redundancy certificate, successful. Direct logs confirm command invocation, three tests, OK, and identical structured results.

| OS | Job ID | Step log time UTC | Reported test duration |
|---|---|---|---|
| Windows | 140101029485 | 2026-11-26T18:26:36.1797615Z | 0.377 s |
| Ubuntu | 140101030147 | 2026-11-26T18:25:31.5770456Z | 0.387 s |

Identical audit payload:

```json
{"audit":{"1":{"covering":1,"obstructions":0,"portfolios":1},"2":{"covering":2,"obstructions":0,"portfolios":2},"3":{"covering":0,"obstructions":1,"portfolios":8},"4":{"covering":38,"obstructions":7,"portfolios":64},"5":{"covering":958,"obstructions":25,"portfolios":1024},"6":{"covering":32627,"obstructions":65,"portfolios":32768}},"limitations":["abstract static union implication only","elementary coarsenings only","no historical coverage or measured cost claim"],"source":"INTERNAL/AI_AUTHORED"}
```

The certificate covers 12,201 abstract length-five words and 33,867 portfolios across alphabet sizes 1–6. The identity positive set is covered by a portfolio of elementary coarsenings iff the portfolio is not contained in a triangle-edge or disjoint-pair obstruction (for nonempty identity positive sets). Two distinct elementary rules cannot cover it; for n>=6 three disjoint pairs furnish one inclusion-minimal covering portfolio. Pairwise non-redundancy therefore does not certify collective independence. This is not a claim about arbitrary filtering-rule portfolios, candidate-set compression improvement, historical coverage, or end-to-end computation cost. Test durations are provenance, not a comparative benchmark.

Failure/evidence lineage: prior Windows job cap cancellations remain in PR #34 history. Source-head runs 45873965528 and 45873965477 succeeded but lacked explicit new certificate invocation, hence were insufficient for this acceptance. Prior V3.8.18 evidence head 65e1e445cf3005b49c3050cbdc2c7c93b882d6db passed both associated runs 45869243368 and 45869243242. Current specialized workflow retained all prior checks, one runner per OS and the six-minute cap. Acceptance is scoped to tested head; this evidence-only commit is not itself yet accepted.

Main c0e38040ec5f389d6444e64b90e7adc42adfca62 unchanged. PR #11 and #13 remain drafts at b5687f5e848d1fab567fcd15d8b1eb51d9e3b651 and 53425be6a80533c219f097e023209776b3330f24 respectively, with 5/5 and 10/10 associated checks successful. Issue #12 open. No production or historical data change, no merge.
