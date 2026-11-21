"""V3.4 exact certified operator transfer: affine seed -> sparse residual repair.

Table-cell diagnostic is *not* lottery out-of-sample validation.
A transfer is accepted only after 100/100 exact reconstruction and a true
coding-length gain over the whole reference table.
"""
from __future__ import annotations
import hashlib
import numpy as np
from .operator_metalearning_v33 import (LearnedOperator,props,scalar,code_bits,canon,VERSION)
from .primitive_categories_v31 import _validated_table,_sha

def transfer(source:LearnedOperator,target,*,source_id='transferred_math_table',
             holdout_cells=20,seed=20261102,max_exceptions=6):
    if not isinstance(source,LearnedOperator):raise ValueError('source must be V3.3 verified operator')
    source.certify()
    if source.family not in ('affine_orbit','sparse_exceptions'):
        return {'status':'unsupported_source_family','reason':'目前仅能迁移同模轨道的稀疏残差',
                'operator':None,'predictive_advantage':'NOT_ESTABLISHED'}
    target,k=_validated_table(target)
    if k!=source.levels:raise ValueError('output class count mismatch')
    if not (type(seed) is int and 0<=seed<2**32 and type(holdout_cells) is int and 5<=holdout_cells<=35
            and type(max_exceptions) is int and 0<=max_exceptions<=6
            and type(source_id) is str and 1<=len(source_id)<=1024):raise ValueError('bad transfer parameters')
    base={'u':source.payload['u'],'v':source.payload['v'],'orbit':list(source.payload['orbit'])}
    def base_table():return np.array([[scalar('affine_orbit',base,a,b,k) for b in range(10)] for a in range(10)],dtype=np.uint8)
    reconstructed=base_table()
    rng=np.random.default_rng(seed)
    train=np.ones(100,dtype=bool);train[rng.choice(100,holdout_cells,replace=False)]=False
    train=train.reshape(10,10)
    changed=np.argwhere(reconstructed!=target)
    # Only diagnose with 80 observed cells. Do not use held-out cells for transfer training.
    train_changed=np.argwhere((reconstructed!=target)&train)
    observed=[(int(a),int(b),int(target[a,b])) for a,b in train_changed]
    observed_dict={(a,b):c for a,b,c in observed}
    diag=np.array([[observed_dict.get((a,b),int(reconstructed[a,b])) for b in range(10)] for a in range(10)],dtype=np.uint8)
    diagnostic={'training_mismatches':int(np.count_nonzero((diag!=target)&train)),
                'cell_holdout_mismatches':int(np.count_nonzero((diag!=target)&~train)),
                'unseen_cell_count':holdout_cells,'not_lottery_forecast':True}
    # Full 100-cell proof creates only a research table expression, not a predictive hypothesis.
    if len(changed)>max_exceptions:
        return {'status':'exceeds_transfer_capacity','changed_count':len(changed),
                'diagnostic':diagnostic,'operator':None,'predictive_advantage':'NOT_ESTABLISHED'}
    if len(changed)==0:
        return {'status':'identical_table_no_new_capability','changed_count':0,
                'diagnostic':diagnostic,'operator':None,'predictive_advantage':'NOT_ESTABLISHED'}
    exceptions=[[int(a),int(b),int(target[a,b])] for a,b in changed]
    p={**base,'exceptions':exceptions}
    bits=code_bits('sparse_exceptions',p,k)
    raw_bits=100*max(1,(k-1).bit_length())
    if bits>=raw_bits:
        return {'status':'no_compression','description_bits_proxy':bits,'raw_bits_proxy':raw_bits,
                'diagnostic':diagnostic,'operator':None,'predictive_advantage':'NOT_ESTABLISHED'}
    sig={'family':'sparse_exceptions','payload':p,'levels':k,'sha':_sha(target),'version':VERSION}
    identifier='pl5.v33.'+hashlib.sha256(canon(sig).encode()).hexdigest()[:24]
    op=LearnedOperator(identifier,'sparse_exceptions',p,k,_sha(target),bits,source_id,props(target))
    proof=op.certify()
    return {'status':'exact_transfer','parent_id':source.id,'source_family':source.family,
            'child_id':identifier,'changed_count':len(changed),'description_bits_proxy':bits,
            'raw_bits_proxy':raw_bits,'diagnostic':diagnostic,'certification':proof,
            'operator':op,'predictive_advantage':'NOT_ESTABLISHED'}

def public_result(result):
    return {k:(v.card() if isinstance(v,LearnedOperator) else v) for k,v in result.items()}
