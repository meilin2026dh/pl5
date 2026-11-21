"""Post-hoc development stress test: remove each source template, no holdout tuning."""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from pailie5.language_evolution_v3722 import _signed,_write_new
from pailie5.math_discovery_v3720 import read_cells
from pailie5.transfer_language_v3723 import _bank,fit_target,freeze_target,evaluate_target


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--benchmark',type=Path,required=True)
    a=p.parse_args(argv);root=a.benchmark
    bank=_bank(root/'frozen_source_bank.json')
    rows=[]
    for cls in range(4):
        reduced={**bank,'templates':[v for i,v in enumerate(bank['templates']) if i!=cls]}
        dest=root/'ablation'/f'bank_without_{cls}.json'
        _write_new(dest,_signed(reduced))
        for seed in range(6):
            base=root/'targets'/f'{cls:02d}_{seed:02d}'
            study=root/'ablation'/f'without_{cls}'/f'trial_{seed}'
            fit_target(read_cells(base/'training.json'),dest,study,candidate_budget=4)
            frozen=freeze_target(study,dest,read_cells(base/'validation.json'))
            tested=evaluate_target(study,dest,read_cells(base/'holdout.json'))
            rows.append({'omitted_template':cls,'seed':seed,'status':tested['status'],
                         'error':tested['errors'],'reason':frozen['reason']})
    out=root/'ablation'/'results.csv'
    with out.open('x',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,rows[0].keys());w.writeheader();w.writerows(rows)
    print(json.dumps({'trials':len(rows),'abstained':sum(r['status']=='ABSTAIN' for r in rows),
                      'accepted':sum(r['status']=='EVALUATED' for r in rows)},ensure_ascii=False))

if __name__=='__main__':main()
