"""Recompute benchmark records from frozen ASTs using the scalar interpreter."""
from pathlib import Path
import hashlib,itertools,json,sys
import numpy as np
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'research_backend'))
from pailie5.structure_evidence_v372 import load_operator
from pailie5.symbolic_operators_v30 import eval_expr_scalar
base=root/'docs/v373/benchmark'
data=json.loads((base/'results.json').read_text())
protocol=json.loads((base/'protocol.json').read_text())
assert hashlib.sha256((base/'protocol.json').read_bytes()).hexdigest()==data['protocol_sha256']
expected=set(itertools.product(protocol['cases'],protocol['seeds'],protocol['arms']))
assert {(r['case'],r['seed'],r['arm']) for r in data['trials']}==expected
assert len(data['trials'])==len(expected)==480
for name,digest in protocol['code_sha256'].items():
    assert hashlib.sha256((root/'research_backend'/name).read_bytes()).hexdigest()==digest,name
for row in data['trials']:
    op=load_operator(base/row['operator_path'])
    p=base/'datasets'/f'{row["case"]}_{row["seed"]}'
    train=json.loads((p/'training_cells.json').read_text());held=json.loads((p/'holdout_cells.json').read_text())
    truth=json.loads((p/'truth_table.json').read_text())
    pred=[[eval_expr_scalar(op.expression,a,b)%10 for b in range(10)] for a in range(10)]
    assert row['training_correct']==sum(pred[a][b]==y for a,b,y in train)
    assert row['holdout_correct']==sum(pred[a][b]==y for a,b,y in held)
    assert row['exact_reconstruction']==(pred==truth)
    assert row['evaluations']==2500 and row['budget_matched']
    fit=row['fit']; ec=fit['evaluation_counts'];pc=fit['proposal_counts']; rc=fit['rejected_counts']
    assert sum(ec.values())==2500
    assert sum(pc.values())==row['proposals']
    assert row['proposals']==2500+rc.get('bounds_or_shape',0)+rc.get('duplicate_AST',0)
    assert not set(tuple(x[:2]) for x in train)&set(tuple(x[:2]) for x in held)
    for k in ('mutation','crossover','guided','warm_start'):
        if not fit['mechanisms'][k]: assert pc.get(k,0)==0
summary=data['summary']
for arm,v in summary['arms'].items():
    r=[x for x in data['trials'] if x['arm']==arm and x['task_group']!='iid_control']
    assert len(r)==64
    assert abs(sum(x['holdout_correct'] for x in r)/2560-v['holdout_accuracy'])<1e-12
    assert sum(x['exact_reconstruction'] for x in r)==v['exact_reconstructions']
for arm,c in summary['prespecified_contrasts'].items():
    differences=np.asarray(c['full_minus_ablation_by_task'])
    signs=2*((np.arange(2**len(differences))[:,None] >> np.arange(len(differences))) & 1)-1
    p=np.mean(np.abs(signs@differences)>=abs(differences.sum())-1e-12)
    assert abs(p-c['p_two_sided_sign_flip'])<1e-12
repeat=json.loads((root/'docs/v373/repeat_subset/results.json').read_text())
ref={(r['case'],r['seed'],r['arm']):r for r in data['trials']}
for r in repeat['trials']:
    a=dict(r);b=dict(ref[r['case'],r['seed'],r['arm']])
    a.pop('fit_seconds');b.pop('fit_seconds')
    assert a==b,r['trial_id']
source=json.loads((root/'docs/v373/source_baseline_sha256.json').read_text())
changed=[p for p,h in source.items() if not (root/p).is_file() or hashlib.sha256((root/p).read_bytes()).hexdigest()!=h]
assert not changed,changed
result={'completed_unique_trials':480,'independent_scalar_recomputations':480,
        'charged_evaluations':sum(r['evaluations'] for r in data['trials']),
        'all_budgets_exact':True,'all_code_fingerprints_match_frozen_protocol':True,
        'protocol_sha256':data['protocol_sha256'],
        'replicated_trials':len(repeat['trials']),'replicated_identical_excluding_timing':True,
        'replications_count_as_new_evidence':False,
        'existing_files_unchanged':len(source),'existing_files_changed':changed,
        'summary_recomputed_from_frozen_operators':True,
        'sign_flip_independently_recomputed':True}
(root/'docs/v373/evidence/independent_verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
