"""Independent risk-focused validation of the V3.7.9 selection grammar."""
import numpy as np
from pailie5.structure_search_v372 import CellDataset
from pailie5.adaptive_primitives_v379 import fit_adaptive_primitive
from pailie5.primitive_study_v377 import split_truth
from pailie5.adaptive_study_v379 import challenge_truth


def test_50_independent_random_tables_are_not_forced_into_supported_grammar():
    for seed in range(50400,50450):
        table=np.random.default_rng(seed).integers(0,10,(10,10),dtype=np.uint8)
        training, _=split_truth(table,seed+1)
        assert fit_adaptive_primitive(training).status != 'identified'


def test_corrupting_one_training_value_invalidates_supported_structure():
    truth=challenge_truth('rank_a2b', 92301)
    train, _=split_truth(truth,1000)
    rows=list(train.rows)
    a,b,y=rows[0]
    rows[0]=(a,b,(y+1)%10)
    model=fit_adaptive_primitive(CellDataset(tuple(rows)))
    assert model.status!='identified'


def test_frozen_fit_never_accepts_sparse_underidentified_sample():
    truth=challenge_truth('split_sum',92311)
    train,_=split_truth(truth,1001)
    partial=CellDataset(tuple(train.rows[:14]))
    assert fit_adaptive_primitive(partial).status != 'identified'
