"""Deterministic developmental synthesis benchmark for V3.7.21.

All tasks are synthetic and programmed in the same repository. Not a blind trial,
not a lottery predictor, and not a compute-matched head-to-head comparison.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys
from collections import defaultdict

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'research_backend'))
from pailie5.math_discovery_v3720 import read_cells
from pailie5.meta_operator_v3721 import make_synthetic, propose, freeze, evaluate, VERSION
from pailie5.structure_evidence_v372 import load_operator
from pailie5.structure_ast_v372 import table

CASES=('square_sum','quadratic_difference','linear_sum','cubic_sum','iid_null')
SEEDS=(3721,3722,3723,3724,3725)


def run(destination:Path):
    if destination.exists():
        raise FileExistsError('research run records are immutable; use a new directory')
    destination.mkdir(parents=True)
    rows=[]
    for case in CASES:
        for seed in SEEDS:
            base=destination/case/str(seed)
            make_synthetic(base/'data',case=case,seed=seed)
            train=read_cells(base/'data/training.json')
            validation=read_cells(base/'data/validation.json')
            holdout=read_cells(base/'data/holdout.json')
            proposal=propose(train,base/'study')
            gate=freeze(base/'study',validation)
            result=evaluate(base/'study',holdout)
            # Baseline is fixed on training, then read-only evaluated on holdout.
            legacy=load_operator(base/'study/operators/legacy_composition.json')
            predictions=table(legacy.expression)
            old_test_errors=sum(int(predictions[a,b])!=y for a,b,y in holdout.rows)
            rows.append({'case':case, 'seed':seed,
                         'train_count':len(train.rows),'validation_count':len(validation.rows),
                         'holdout_count':len(holdout.rows),
                         'legacy_training_errors':proposal['baseline_training_errors'],
                         'legacy_holdout_errors':old_test_errors,
                         'best_validation_errors':gate['best_candidate']['validation_errors'],
                         'status':gate['status'],
                         'meta_holdout_errors':result['holdout_errors'],
                         'winner':gate['selected']['name'] if gate['selected'] else 'ABSTAIN',
                         'proposal_sha256':hashlib.sha256((base/'study/proposal.json').read_bytes()).hexdigest(),
                         'freeze_sha256':hashlib.sha256((base/'study/freeze.json').read_bytes()).hexdigest(),
                         'evaluation_sha256':hashlib.sha256((base/'study/evaluation.json').read_bytes()).hexdigest()})
    with (destination/'results.csv').open('x',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    by_case=defaultdict(list)
    for row in rows:by_case[row['case']].append(row)
    summary={}
    for name, parts in by_case.items():
        scored=[r for r in parts if r['meta_holdout_errors'] is not None]
        summary[name]={'studies':len(parts),'frozen':len(scored),
                       'abstentions':len(parts)-len(scored),
                       'legacy_training_errors_total':sum(r['legacy_training_errors'] for r in parts),
                       'legacy_test_errors_total':sum(r['legacy_holdout_errors'] for r in parts),
                       'meta_test_errors_if_frozen':sum(r['meta_holdout_errors'] for r in scored),
                       'holdout_cells_scored':len(scored)*20}
    info={'schema':VERSION+':development-benchmark','cases':list(CASES),'seeds':list(SEEDS),
          'counts':{'train':60,'validation':20,'holdout':20},'summary':summary,
          'comparison':'legacy_composition_only; NOT compute-matched or full V3.7.20 search',
          'external_blind':False,'production_enabled':False,
          'predictive_advantage':'NOT_ESTABLISHED',
          'protocol':'Developer-defined synthetic families and fixed seeds; no claim of independent task discovery.'}
    (destination/'summary.json').write_text(json.dumps(info,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'runs/v3721/benchmark')
    args=p.parse_args();run(args.out)
