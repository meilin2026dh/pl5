"""Frozen-protocol synthetic mechanism ablations for PL5 V3.7.3."""
from __future__ import annotations
from dataclasses import asdict, replace
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import time
import numpy as np

from .ablation_search_v373 import AblationConfig, Mechanisms, fit_budgeted
from .ablation_statistics_v373 import summarize
from .structure_search_v372 import CellDataset
from .structure_ast_v372 import table, GRAMMAR
from .structure_evidence_v372 import save_operator, load_operator, evaluate_frozen, certify_table

A=('a',); B=('b',)
def _bin(op,left,right): return ('binary',op,left,right)
def _c(x): return ('const',x)
AB=_bin('mul',A,B); SUM=_bin('add',A,B)
CASES={
    'shifted_bilinear':{'group':'related_motif','expression':_bin('add',_bin('add',AB,A),_c(3))},
    'shifted_square':{'group':'related_motif','expression':_bin('add',_bin('mul',SUM,SUM),_c(3))},
    'shifted_minimum':{'group':'related_motif','expression':_bin('add',_bin('min',SUM,AB),_c(5))},
    'abs_product_plus_b':{'group':'related_motif','expression':_bin('add',_bin('absdiff',AB,_c(3)),B)},
    'asymmetric_cubic':{'group':'other_composition','expression':_bin('add',_bin('mul',_bin('mul',A,A),B),B)},
    'gcd_offsets':{'group':'other_composition','expression':_bin('gcd',_bin('add',A,_c(3)),_bin('add',B,_c(5)))},
    'xor_mixed':{'group':'other_composition','expression':_bin('xor',AB,SUM)},
    'difference_squares':{'group':'other_composition','expression':_bin('absdiff',_bin('mul',A,A),_bin('mul',B,B))},
    'iid_a':{'group':'iid_control','expression':None},
    'iid_b':{'group':'iid_control','expression':None},
}
ARMS={
    'full':Mechanisms(),
    'no_mutation':Mechanisms(mutation=False),
    'no_crossover':Mechanisms(crossover=False),
    'no_complexity':Mechanisms(complexity=False),
    'no_warm_start':Mechanisms(warm_start=False),
    'grammar_only':Mechanisms(mutation=False,crossover=False,warm_start=False,guided=False),
}
DEFAULT_SEEDS=tuple(range(37301,37309))
SOURCE_CASES=('bilinear','absolute_product','squared_sum','mixed_minimum')


def _write(path,data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False); f.write('\n')


def truth_table(case,seed):
    if case not in CASES: raise ValueError('unknown task')
    if CASES[case]['group']=='iid_control':
        stream=701 if case=='iid_a' else 702
        return np.random.default_rng(np.random.SeedSequence([seed,stream])).integers(0,10,(10,10),dtype=np.uint8)
    return table(CASES[case]['expression'])


def split_table(truth,seed,case):
    if case not in CASES: raise ValueError('unknown task')
    case_index=list(CASES).index(case)
    order=np.random.default_rng(np.random.SeedSequence([seed,801,case_index])).permutation(100)
    def take(ids):
        return CellDataset(tuple((int(i//10),int(i%10),int(truth.flat[i])) for i in ids))
    return take(order[:60]),take(order[60:])


def load_warm_bank():
    root=Path(__file__).resolve().parents[2]
    bank=[]; metadata=[]
    for case in SOURCE_CASES:
        path=root/f'docs/v372/benchmark/{case}_20261102/operator.json'
        model=load_operator(path)
        bank.append(model.expression)
        metadata.append({'source_case':case,'source_path':str(path.relative_to(root)),
                         'file_sha256':sha256(path.read_bytes()).hexdigest(),
                         'operator_id':model.identity,'source_data_sha256':model.source_data_sha256,
                         'expression':model.expression})
    return tuple(bank),metadata


def _code_fingerprints():
    root=Path(__file__).resolve().parents[1]
    names=['research_v373.py','pailie5/ablation_search_v373.py',
           'pailie5/ablation_benchmark_v373.py','pailie5/ablation_statistics_v373.py',
           'pailie5/structure_ast_v372.py','pailie5/structure_search_v372.py',
           'pailie5/structure_evidence_v372.py','pailie5/symbolic_operators_v30.py']
    return {name:sha256((root/name).read_bytes()).hexdigest() for name in names}


def run_suite(output, *, seeds=DEFAULT_SEEDS, cases=None, arms=None, budget=2500):
    seeds=tuple(seeds); cases=tuple(CASES if cases is None else cases); arms=tuple(ARMS if arms is None else arms)
    if (not 1<=len(seeds)<=64 or len(set(seeds))!=len(seeds) or not cases or not arms
            or len(set(cases))!=len(cases) or len(set(arms))!=len(arms)
            or any(c not in CASES for c in cases) or any(a not in ARMS for a in arms)):
        raise ValueError('invalid or duplicate seeds/cases/arms')
    configs=[AblationConfig(seed=s,evaluation_budget=budget) for s in seeds]
    bank,metadata=load_warm_bank()
    output=Path(output); output.mkdir(parents=True,exist_ok=False)
    datasets={}
    for case in cases:
        for seed in seeds:
            truth=truth_table(case,seed); train,held=split_table(truth,seed,case)
            datasets[case,seed]=(truth,train,held)
    protocol={
        'release':'3.7.3','recorded_before_fits_utc':datetime.now(timezone.utc).isoformat(),
        'purpose':'equal-evaluation developmental mechanism ablation; not a general ranking or lottery test',
        'cases':{k:CASES[k] for k in cases},'seeds':seeds,
        'arms':{k:asdict(ARMS[k]) for k in arms},'configs':[asdict(c) for c in configs],
        'train_pairs':60,'holdout_pairs':40,'grammar':GRAMMAR,
        'protocol_type':'local preregistered configuration, not externally timestamped or blind',
        'warm_bank':metadata,'warm_start_cost_scope':'destination_search_only; source_acquisition_excluded',
        'budget_unit':'distinct normalized AST interpreter calls; invalid arithmetic charged; duplicate proposals uncharged',
        'disabled_slot_policy':'target-independent random grammar proposal; no change after observing held-out scores',
        'comparison_family':['full_vs_no_mutation','full_vs_no_crossover','full_vs_no_complexity','full_vs_no_warm_start'],
        'analysis':'mean seed scores within task; exact two-sided task sign-flip, Holm across four contrasts; exploratory',
        'datasets':{f'{c}_{s}':{'train_sha256':d[1].fingerprint,'holdout_sha256':d[2].fingerprint,
                              'truth_sha256':sha256(d[0].astype(np.uint8).tobytes()).hexdigest()}
                    for (c,s),d in datasets.items()},
        'code_sha256':_code_fingerprints(),'python':platform.python_version(),'numpy':np.__version__,
        'production_enabled':False,
    }
    _write(output/'protocol.json',protocol)
    digest=sha256((output/'protocol.json').read_bytes()).hexdigest()
    trials=[]
    for case in cases:
        for cfg in configs:
            truth,train,held=datasets[case,cfg.seed]
            data_path=output/'datasets'/f'{case}_{cfg.seed}'
            _write(data_path/'training_cells.json',train.rows)
            _write(data_path/'holdout_cells.json',held.rows)
            _write(data_path/'truth_table.json',truth.tolist())
            fitted=[]
            # Finish and export every policy before examining this dataset's held-out results.
            for arm in arms:
                started=time.perf_counter()
                result=fit_budgeted(train,cfg,ARMS[arm],warm_starts=bank)
                seconds=time.perf_counter()-started
                trial_id=f'{case}_{cfg.seed}_{arm}'
                path=output/'trials'/trial_id/'operator.json'
                save_operator(result.operator,path)
                fitted.append((arm,result,seconds,path,trial_id))
            for arm,result,seconds,path,trial_id in fitted:
                op=load_operator(path)
                hold=evaluate_frozen(op,held)
                cert=certify_table(op,truth)
                row={'trial_id':trial_id,'case':case,'task_group':CASES[case]['group'],
                     'seed':cfg.seed,'arm':arm,'training_correct':len(train.rows)-result.training_errors,
                     'training_n':len(train.rows),'holdout_correct':hold['count']-hold['errors'],
                     'holdout_n':hold['count'],'exact_reconstruction':cert['exact_on_all_100_pairs'],
                     'nodes':result.winning_nodes,'evaluations':result.evaluations,
                     'proposals':result.proposals,'budget_matched':result.budget_matched,
                     'winning_origin':result.winning_origin,'fit_seconds':seconds,
                     'operator_path':str(path.relative_to(output)),'fit':result.to_dict(),
                     'holdout':hold,'certificate':cert,'production_enabled':False}
                _write(path.parent/'result.json',row); trials.append(row)
                print(f'{len(trials)}: {trial_id}: train={row["training_correct"]}/60 '
                      f'held={row["holdout_correct"]}/40 exact={row["exact_reconstruction"]} '
                      f'evals={row["evaluations"]}',flush=True)
    result={'protocol_sha256':digest,'protocol':protocol,'trials':trials,
            'summary':summarize(trials),'production_enabled':False,'predictive_advantage':'NOT_ESTABLISHED'}
    _write(output/'results.json',result)
    _write(output/'summary.json',result['summary'])
    return result
