"""INTERNAL locked-seed synthetic evaluation. Not an independent external blind trial.

This exercises the real public/private challenge protocol and two candidate
approaches on the same 10x10 problem sets. It is a separate developer-authored
setter, not an adversarial third party. Models do not receive family IDs.
"""
from __future__ import annotations
import csv
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
from pailie5.structure_search_v372 import CellDataset
from pailie5.open_grammar_v3725 import VERSION, fit,freeze,evaluate,commit_holdout
from pailie5.grammar_discovery_v3724 import fit as old_fit,freeze as old_freeze,evaluate as old_evaluate,commit_holdout as old_commit
from pailie5.language_evolution_v3722 import _sha

FAMILIES=('cubic_interaction','piecewise_lt','parity_gate','power_sums','linear_control',
          'random_null','opaque_exponential','diagonal_gate','corrupt_training')
# Development seeds 372501/372502 were used for initial engineering pilot and excluded.
FROZEN_SEEDS=(372503,372504,372505,372506)


def setter(family:str,seed:int)->np.ndarray:
    if family not in FAMILIES or seed not in FROZEN_SEEDS:raise ValueError('invalid challenge family/seed')
    a,b=np.indices((10,10),dtype=np.int64)
    shift=seed%10
    if family=='cubic_interaction': t=(a*a*b+b*b+shift)%10
    elif family=='piecewise_lt':t=np.where(a<b,a*b+shift,np.bitwise_xor(a,b)+shift)%10
    elif family=='parity_gate':t=np.where((a%2)==(b%2),a*b+shift,np.bitwise_xor(a,b)+shift)%10
    elif family=='power_sums':t=(a**3+b**3+shift)%10
    elif family=='linear_control':t=(a+b+shift)%10
    elif family=='random_null':t=np.random.default_rng(seed+999).integers(0,10,(10,10))
    elif family=='opaque_exponential':t=np.fromfunction(lambda x,y: ((x+1)**(y%4+1)+y**3+shift)%10,(10,10),dtype=int).astype(int)
    elif family=='diagonal_gate':t=np.where(a==b,a*b+shift,np.bitwise_xor(a,b)+shift)%10
    else:t=(a*a*b+b*b+shift)%10
    return t.reshape(100)


def run(out:Path):
    out.mkdir(parents=True,exist_ok=False)
    protocol={'schema':VERSION+':internal_protocol','families':FAMILIES,'seeds':FROZEN_SEEDS,
       'dev_seeds_excluded':[372501,372502],
       'partitions':{'train':48,'validation':16,'holdout':36},
       'arms':['v3724_expanded','v3725_ring'],
       'research_caveat':'developer authored, cannot claim genuine external blind',
       'source_discovery_costs_equalized':False,'total_compute_budget_equalized':False,
       'lottery_predictive_advantage':'NOT_ESTABLISHED'}
    (out/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    protocol_hash=_sha(protocol)
    rows=[]
    for family in FAMILIES:
        for seed in FROZEN_SEEDS:
            table=setter(family,seed).copy()
            perm=np.random.default_rng(seed+31000).permutation(100)
            # corrupt only ONE training label, after generating the train partition
            if family=='corrupt_training':table[perm[0]]=(table[perm[0]]+1)%10
            chunks=(perm[:48],perm[48:64],perm[64:])
            sets=[CellDataset(tuple((int(x//10),int(x%10),int(table[x])) for x in inds)) for inds in chunks]
            train,val,hold=sets
            private_nonce=hashlib.sha256(f'{VERSION}|{seed}|{family}|local-only-synthetic-nonce'.encode()).hexdigest()
            artifacts={}
            # Fit+freeze BOTH arms before a single held-out label is scored.
            for arm in ('v3724_expanded','v3725_ring'):
                folder=out/'studies'/family/str(seed)/arm
                if arm=='v3725_ring':
                    digest=commit_holdout(hold,private_nonce)
                    fitted=fit(train,folder,holdout_digest=digest,protocol_sha256=protocol_hash)
                    frozen=freeze(folder,val)
                else:
                    digest=old_commit(hold,private_nonce)
                    fitted=old_fit(train,folder,arm='expanded',holdout_digest=digest,protocol_sha256=protocol_hash)
                    frozen=old_freeze(folder,val)
                artifacts[arm]=(folder,fitted,frozen)
            for arm in ('v3724_expanded','v3725_ring'):
                folder,fitted,frozen=artifacts[arm]
                if arm=='v3725_ring': grade=evaluate(folder,hold,nonce=private_nonce)
                else:grade=old_evaluate(folder,hold,nonce=private_nonce)
                rows.append({'family':family,'seed':seed,'arm':arm,
                   'status':frozen['status'],'errors':grade['test_errors'],
                   'test_cells':grade['test_count'],
                   'candidate_evaluations':fitted['candidate_evaluations'],
                   'fit_wall_ms':round(fitted.get('fit_wall_ns',fitted.get('wall_ns_fit',0))/1e6,3),
                   'commitment_verified':grade['commitment_verified']})
    with (out/'results.csv').open('w',encoding='utf-8',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary={'protocol_sha256':protocol_hash,'schema':VERSION+':summary',
      'external_blind':False,'equal_candidate_budget':False,'equal_total_compute':False,
      'source_discovery_cost_included':False,
      'methods':{},'families':{},'logical_results_sha256':_sha([{k:v for k,v in row.items() if k!='fit_wall_ms'} for row in rows]),
      'lottery_predictive_advantage':'NOT_ESTABLISHED'}
    for arm in protocol['arms']:
        subset=[r for r in rows if r['arm']==arm]
        summary['methods'][arm]={'tasks':len(subset),
            'accepted':sum(r['status']=='FROZEN' for r in subset),
            'abstained':sum(r['status']=='ABSTAIN' for r in subset),
            'accepted_test_cells':sum(r['test_cells'] for r in subset if r['errors'] is not None),
            'accepted_test_errors':sum(r['errors'] or 0 for r in subset),
            'total_fit_wall_ms':round(sum(r['fit_wall_ms'] for r in subset),2),
            'candidate_evaluations':sum(r['candidate_evaluations'] for r in subset)}
    for family in FAMILIES:
        summary['families'][family]={arm:{'accepted':sum(r['family']==family and r['arm']==arm and r['status']=='FROZEN' for r in rows),
              'errors':sum(r['errors'] or 0 for r in rows if r['family']==family and r['arm']==arm)} for arm in protocol['arms']}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary

if __name__=='__main__':run(Path(sys.argv[1] if len(sys.argv)>1 else '../runs/v3725/evaluation'))
