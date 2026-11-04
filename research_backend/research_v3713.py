#!/usr/bin/env python3
"""V3.7.13 bounded one-shot combinatorial + conformal audit CLI.

This command only designs/reviews candidate sets and precommitted rankings;
it does NOT scrape draws, predict them, run a daemon or deploy research models.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from pailie5.codebook_v3713 import audit_codebook, select_diverse_codebook
from pailie5.covering_arrays_v3713 import generate_pl5_covering_array, audit_interactions
from pailie5.conformal_audit_v3713 import (
    calibrate_rank_cutoff, assess_future_ranks, audit_fixed_filter,
)
from pailie5.dynamic_budget_v3713 import (
    calibrate_scaled_ranks, recommend_daily_budget, evaluate_dynamic_holdout,
)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def command_codebook(args) -> dict:
    original = generate_pl5_covering_array(args.strength)
    target = select_diverse_codebook(original, budget=args.budget,
                                     min_distance=args.min_distance, strength=args.strength)
    folder = Path(args.output)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'codebook.txt').write_text(''.join(row + '\n' for row in target), encoding='utf-8')
    audit = {
        'schema': 'pl5-v3713-structured-codebook-workflow-1',
        'source_count': len(original),
        'source_cover': audit_interactions(original, args.strength),
        'requested_budget': args.budget,
        'budget_fulfilled': len(target) == args.budget,
        'minimum_distance_hard_constraint': args.min_distance,
        'codebook': audit_codebook(target, strength=args.strength),
        'generation_method': 'GF11 polynomial evaluations, coarsen 10 to 9',
        'selection_method': 'deterministic greedy; not optimality certified',
        'predictive_advantage': 'NOT_ESTABLISHED',
    }
    _write_json(folder / 'audit.json', audit)
    return audit


def command_conformal(args) -> dict:
    data = json.loads(Path(args.input).read_text(encoding='utf-8'))
    calibration = calibrate_rank_cutoff(
        data['calibration_ranks'], data['calibration_issues'],
        alpha=data['alpha'], frozen_model_sha256=data['model_sha256'],
        training_end_issue=data['training_end_issue'],
    )
    result = {'schema': 'pl5-v3713-calibration-cli-1',
              'calibration': asdict(calibration),
              'dataset_provenance': data.get('input_type', 'not_provided'),
              'source_provenance_verified_by_software': False,
              'exchangeability_cannot_be_inferred_from_software': True,
              'predictive_advantage': 'NOT_ESTABLISHED'}
    if 'test_ranks' in data or 'test_issues' in data:
        result['holdout'] = assess_future_ranks(calibration, data['test_ranks'], data['test_issues'],
                                                confidence=data.get('confidence', 0.95))
    _write_json(Path(args.output), result)
    return result


def command_fixed_filter(args) -> dict:
    data = json.loads(Path(args.input).read_text(encoding='utf-8'))
    result = audit_fixed_filter(
        data['observations'], data['kept_by_issue'],
        training_end_issue=data['training_end_issue'],
        precommitted=data.get('precommitted', False),
        confidence=data.get('confidence', 0.95),
    )
    result['dataset_provenance'] = data.get('input_type', 'not_provided')
    _write_json(Path(args.output), result)
    return result



def command_dynamic_budget(args) -> dict:
    data=json.loads(Path(args.input).read_text(encoding='utf-8'))
    cal=calibrate_scaled_ranks(
        data['calibration_ranks'], data['calibration_difficulty_scales'],
        data['calibration_issues'], alpha=data['alpha'],
        training_end_issue=data['training_end_issue'],
        frozen_model_sha256=data['model_sha256'],
        frozen_scale_sha256=data['scale_model_sha256'],
    )
    requests=data['future_issues']
    budgets=[asdict(recommend_daily_budget(
        cal, row['issue'], difficulty_scale=row['difficulty_scale'],
        affordable_max_tickets=row['affordable_max_tickets'],
    )) for row in requests]
    result={
        'schema':'pl5-v3713-dynamic-budget-cli-1',
        'calibration':asdict(cal),
        'daily_budgets':budgets,
        'dataset_provenance':data.get('input_type','not_provided'),
        'pre_draw_difficulty_inputs_not_verified_by_software':True,
        'marginal_coverage_requires_normalized_score_exchangeability':True,
        'capped_budget_does_not_inherit_unaffordable_target_guarantee':True,
        'predictive_advantage':'NOT_ESTABLISHED',
    }
    if 'holdout' in data:
        records=[(r['issue'],r['difficulty_scale'],r['affordable_max_tickets'],r['actual_rank']) for r in data['holdout']]
        result['holdout']=evaluate_dynamic_holdout(cal,records)
    _write_json(Path(args.output), result)
    return result

def main() -> int:
    parser=argparse.ArgumentParser(description='PL5 V3.7.13 research design/risk audit (NOT prediction)')
    subs=parser.add_subparsers(dest='command',required=True)
    codebook=subs.add_parser('codebook',help='design distance-constrained subset of algebraic covering array')
    codebook.add_argument('--strength',type=int,choices=(2,3),default=2)
    codebook.add_argument('--budget',type=int,required=True)
    codebook.add_argument('--min-distance',type=int,default=3)
    codebook.add_argument('--output',required=True)
    for command in ('conformal','fixed-filter','dynamic-budget'):
        sub=subs.add_parser(command,help='audit previously frozen model outcomes')
        sub.add_argument('--input',required=True)
        sub.add_argument('--output',required=True)
    args=parser.parse_args()
    if args.command=='codebook':
        report=command_codebook(args)
    elif args.command=='conformal':
        report=command_conformal(args)
    elif args.command=='fixed-filter':
        report=command_fixed_filter(args)
    else:
        report=command_dynamic_budget(args)
    print(json.dumps(report,ensure_ascii=False,sort_keys=True))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
