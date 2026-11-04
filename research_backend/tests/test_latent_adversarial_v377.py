"""Additional tests: deliberately inconsistent and minimally identified systems."""
import numpy as np
from pailie5.structure_search_v372 import CellDataset
from pailie5.primitive_study_v377 import make_truth,split_truth
from pailie5.latent_primitives_v377 import fit_additive_primitive,evaluate_frozen_latent


def test_negative_random_tables_do_not_get_certificates():
    for seed in range(25):
        rng=np.random.default_rng(seed+10000)
        train,_ = split_truth(rng.integers(0,10,(10,10)),seed+10111)
        assert fit_additive_primitive(train).status == 'rejected_inconsistent'


def test_single_label_corruption_is_rejected():
    for case in ('latent_quadratic','latent_cubic','latent_mixed'):
        train,_ = split_truth(make_truth(case,81001),81002)
        rows=list(train.rows)
        a,b,y=rows[0]
        rows[0]=(a,b,(y+1)%10)
        assert fit_additive_primitive(CellDataset(tuple(rows))).status == 'rejected_inconsistent'


def test_connected_19_edge_spanning_tree_is_sufficient():
    truth = make_truth('latent_cubic',11011)
    pairs={(0,b) for b in range(10)} | {(a,0) for a in range(1,10)}
    train=CellDataset(tuple((a,b,int(truth[a,b])) for a,b in sorted(pairs)))
    holdout=CellDataset(tuple((a,b,int(truth[a,b])) for a in range(10) for b in range(10) if (a,b) not in pairs))
    fit=fit_additive_primitive(train)
    assert fit.status=='identified'
    evidence=evaluate_frozen_latent(fit,holdout)
    assert evidence['errors']==0 and evidence['count']==81
