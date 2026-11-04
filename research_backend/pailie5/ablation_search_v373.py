"""Equal-evaluation ablations over the existing safe PL5 integer AST.

A disabled adaptive slot is replaced by a target-independent grammar draw.
This measures marginal contribution under that specific resource reallocation,
not an intrinsic or universal value of a genetic-programming mechanism.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from functools import lru_cache
from hashlib import sha256
import json
import math
import numpy as np

from .symbolic_operators_v30 import BINARY, eval_expr
from .structure_ast_v372 import AST, ATOMS, validate_ast, normalize, mutate, crossover
from .structure_search_v372 import CellDataset, FrozenOperator


@dataclass(frozen=True)
class Mechanisms:
    mutation: bool = True
    crossover: bool = True
    complexity: bool = True
    warm_start: bool = True
    guided: bool = True

    def __post_init__(self):
        if any(type(x) is not bool for x in asdict(self).values()):
            raise ValueError('mechanism switches must be booleans')


@dataclass(frozen=True)
class AblationConfig:
    seed: int = 37301
    evaluation_budget: int = 2500
    pool_size: int = 32
    batch_size: int = 32
    max_nodes: int = 11
    max_depth: int = 6
    bootstrap_fraction: float = 0.30
    complexity_weight: float = 0.05
    proposal_factor: int = 100

    def __post_init__(self):
        bounds = {'seed': (0,2**32-1), 'evaluation_budget': (1,50000),
                  'pool_size': (2,256), 'batch_size': (1,256),
                  'max_nodes': (3,15), 'max_depth': (2,8), 'proposal_factor': (1,1000)}
        for name,(lo,hi) in bounds.items():
            x=getattr(self,name)
            if type(x) is not int or not lo <= x <= hi:
                raise ValueError(f'invalid {name}')
        for name,lo,hi in [('bootstrap_fraction',0,1),('complexity_weight',0,1)]:
            x=getattr(self,name)
            if type(x) not in (int,float) or not math.isfinite(x) or not lo <= x <= hi:
                raise ValueError(f'invalid {name}')


def rank_key(errors: int, nodes: int, identity: str, weight: float) -> tuple:
    """Zero penalty removes *every* explicit size-based tie break."""
    return ((errors,identity) if weight==0 else
            (errors+weight*nodes,errors,nodes,identity))


@dataclass(frozen=True)
class AblationResult:
    operator: FrozenOperator
    training_errors: int
    training_count: int
    evaluations: int
    proposals: int
    distinct_integer_behaviors: int
    proposal_counts: dict
    evaluation_counts: dict
    rejected_counts: dict
    winning_origin: str
    winning_nodes: int
    first_exact_evaluation: int | None
    trace: tuple[dict,...]
    config: AblationConfig
    mechanisms: Mechanisms
    budget_matched: bool

    def to_dict(self):
        data=asdict(self)
        data['operator']=self.operator.to_dict()
        data['selection_used']='training_cells_only'
        data['budget_unit']='distinct_normalized_AST_interpreter_calls_including_arithmetic_failures'
        data['replacement_policy']='disabled_slots_use_target_independent_random_grammar'
        data['wall_time_matched']=False
        return json.loads(json.dumps(data,sort_keys=True,allow_nan=False))


@dataclass(frozen=True)
class _Candidate:
    tree: AST
    errors: int
    nodes: int
    key: tuple
    origin: str
    identity: str


@lru_cache(maxsize=1)
def _basis():
    return tuple(sorted({normalize(('binary',op,left,right)) for op in BINARY
                         for left in ATOMS[:2] for right in ATOMS[:2]},key=repr))


@lru_cache(maxsize=1)
def _expansions():
    basis=_basis()
    return tuple(('binary',op,left,right) for left in basis
                 for right in (*ATOMS,*basis) for op in BINARY)


def _random_tree(rng, max_nodes, max_depth):
    """Sample syntax without reading labels, elites or a target expression."""
    max_binary=min((max_nodes-1)//2,2**(max_depth-1)-1)
    def grow(k,depth):
        if k==0: return ATOMS[int(rng.integers(len(ATOMS)))]
        capacity=2**(max_depth-depth-1)-1
        low,high=max(0,k-1-capacity),min(capacity,k-1)
        left=int(rng.integers(low,high+1))
        return ('binary',BINARY[int(rng.integers(len(BINARY)))],
                grow(left,depth+1),grow(k-1-left,depth+1))
    return grow(int(rng.integers(1,max_binary+1)),1)


def fit_budgeted(training: CellDataset, config: AblationConfig = AblationConfig(),
                 mechanisms: Mechanisms = Mechanisms(), *,
                 warm_starts: tuple[AST,...] = ()) -> AblationResult:
    """The fitter never receives hidden labels or a complete target table.

    Models may be evaluated on all input *coordinates* for safe integer-behavior
    deduplication, but only observed labels enter their scores. Exact fits do not
    stop search. A proposal guard is reported as an unmatched budget, not a win.
    """
    if (not isinstance(training,CellDataset) or not isinstance(config,AblationConfig)
            or not isinstance(mechanisms,Mechanisms)):
        raise ValueError('expected training CellDataset, AblationConfig and Mechanisms')
    if not isinstance(warm_starts,tuple) or len(warm_starts)>64:
        raise ValueError('at most 64 warm ASTs are accepted')
    for tree in warm_starts:
        validate_ast(tree,max_nodes=config.max_nodes,max_depth=config.max_depth)
    rngs=[np.random.default_rng(np.random.SeedSequence([config.seed,i])) for i in range(9)]
    index=np.array([10*a+b for a,b,_ in training.rows],dtype=int)
    target=np.array([y for _,_,y in training.rows],dtype=np.int64)
    seen=set(); archive={}
    proposals=Counter(); evaluations=Counter(); rejected=Counter()
    n_evaluated=0; n_proposed=0; first_exact=None; trace=[]
    weight=config.complexity_weight if mechanisms.complexity else 0.0

    def remaining():
        return n_evaluated<config.evaluation_budget and n_proposed<config.proposal_factor*config.evaluation_budget

    def put(tree,origin):
        nonlocal n_evaluated,n_proposed,first_exact
        if not remaining(): return
        n_proposed+=1; proposals[origin]+=1
        try:
            validate_ast(tree,max_nodes=config.max_nodes,max_depth=config.max_depth)
            tree=normalize(tree)
        except ValueError:
            rejected['bounds_or_shape']+=1; return
        if tree in seen:
            rejected['duplicate_AST']+=1; return
        seen.add(tree); n_evaluated+=1; evaluations[origin]+=1
        try:
            raw=eval_expr(tree)
        except (ValueError,OverflowError):
            rejected['arithmetic']+=1; return
        nodes,_=validate_ast(tree)
        errors=int(np.count_nonzero(raw[index]%10 != target))
        if errors==0 and first_exact is None: first_exact=n_evaluated
        identity=sha256(repr(tree).encode('utf8')).hexdigest()
        row=_Candidate(tree,errors,nodes,rank_key(errors,nodes,identity,weight),origin,identity)
        signature=raw.astype('<i8',copy=False).tobytes()
        if signature not in archive or row.key<archive[signature].key:
            archive[signature]=row

    def best_rows():
        return sorted(archive.values(),key=lambda row:row.key)

    def snapshot(stage):
        row=best_rows()[0]
        trace.append({'stage':stage,'evaluations':n_evaluated,'proposals':n_proposed,
                      'errors':row.errors,'nodes':row.nodes,'origin':row.origin,
                      'expression':row.tree})

    put(('a',),'safe_baseline')
    if mechanisms.warm_start:
        for tree in warm_starts: put(tree,'warm_start')
    limit=min(config.evaluation_budget,max(1,int(config.evaluation_budget*config.bootstrap_fraction)))
    bootstrap=list(ATOMS)+list(_basis())
    bootstrap += [('binary',op,left,right) for left in ATOMS for right in ATOMS for op in BINARY]
    for tree in bootstrap:
        if not remaining() or n_evaluated>=limit: break
        put(tree,'bootstrap')
    expansion=_expansions()
    for j in rngs[0].permutation(len(expansion)):
        if not remaining() or n_evaluated>=limit: break
        put(expansion[int(j)],'grammar_composition')
    snapshot('bootstrap')
    slot=0; elites=best_rows()[:config.pool_size]
    last_snapshot=n_evaluated
    while remaining():
        if slot%config.batch_size==0: elites=best_rows()[:config.pool_size]
        mode=slot%4; rng=rngs[mode+1]
        active=(mechanisms.guided,mechanisms.mutation,mechanisms.crossover,False)[mode]
        if not active:
            tree=_random_tree(rngs[mode+5],config.max_nodes,config.max_depth)
            origin='random_grammar'
        else:
            parent=elites[int(rng.integers(len(elites)))].tree
            if mode==0:
                fragments=(*ATOMS,*_basis())
                other=fragments[int(rng.integers(len(fragments)))]
                op=BINARY[int(rng.integers(len(BINARY)))]
                tree=(('binary',op,parent,other) if int(rng.integers(2)) else ('binary',op,other,parent))
                origin='guided'
            elif mode==1:
                tree=mutate(parent,rng,max_nodes=config.max_nodes,max_depth=config.max_depth)
                origin='mutation'
            else:
                other=elites[int(rng.integers(len(elites)))].tree
                tree=crossover(parent,other,rng,max_nodes=config.max_nodes,max_depth=config.max_depth)
                origin='crossover'
        put(tree,origin); slot+=1
        if n_evaluated-last_snapshot>=256:
            snapshot('search'); last_snapshot=n_evaluated
    snapshot('final')
    row=best_rows()[0]
    return AblationResult(FrozenOperator(row.tree,training.fingerprint,training.pairs),
                          row.errors,len(training.rows),n_evaluated,n_proposed,len(archive),
                          dict(proposals),dict(evaluations),dict(rejected),row.origin,row.nodes,
                          first_exact,tuple(trace),config,mechanisms,
                          n_evaluated==config.evaluation_budget)
