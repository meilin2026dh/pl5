"""V3.7.1 constrained operator evolution. Validation never drives selection."""
from dataclasses import dataclass
import numpy as np
from .math_language_v37 import Expression, validate_table, properties

@dataclass(frozen=True)
class EvolutionConfig:
    population: int = 24
    generations: int = 30
    mutations: int = 2
    seed: int = 20261102
    complexity_penalty: float = 0.001

def evolve(target, training_mask, validation_mask, config=EvolutionConfig()):
    x = validate_table(target)
    train, valid = np.asarray(training_mask), np.asarray(validation_mask)
    if (train.shape != (10,10) or valid.shape != (10,10) or train.dtype != bool
            or valid.dtype != bool or not train.any() or not valid.any() or (train & valid).any()):
        raise ValueError('invalid masks')
    if not (2 <= config.population <= 1000 and 1 <= config.generations <= 10000
            and 1 <= config.mutations <= 100 and config.complexity_penalty >= 0):
        raise ValueError('invalid configuration')
    rng = np.random.default_rng(config.seed)
    seeds = [Expression('affine', t).evaluate() for t in
             [(1,1,0), (1,0,0), (0,1,0), (1,1,1), (1,9,0)]]
    population = [s.copy() for s in seeds[:config.population]]
    while len(population) < config.population:
        population.append(rng.integers(0,10,(10,10),dtype=np.uint8))
    def fitness(t):
        errors = int(np.count_nonzero((t != x) & train))
        complexity = min(int(np.count_nonzero(t != s)) for s in seeds)
        return (errors + config.complexity_penalty * complexity, errors, complexity)
    best = min(population, key=fitness).copy()
    for _ in range(config.generations):
        population.sort(key=fitness)
        if fitness(population[0]) < fitness(best):
            best = population[0].copy()
        elite = population[:max(2,config.population//4)]
        children = [e.copy() for e in elite]
        while len(children) < config.population:
            child = elite[int(rng.integers(len(elite)))].copy()
            for _ in range(config.mutations):
                a,b = rng.integers(0,10,size=2)
                child[a,b] = rng.integers(0,10)
            children.append(child)
        population = children
    candidate = min(population, key=fitness)
    if fitness(candidate) < fitness(best):
        best = candidate.copy()
    return {'table':best.tolist(), 'train_errors':int(np.count_nonzero((best!=x)&train)),
            'validation_errors':int(np.count_nonzero((best!=x)&valid)),
            'train_cells':int(train.sum()), 'validation_cells':int(valid.sum()),
            'properties':properties(best), 'seed':config.seed,
            'production_enabled':False, 'predictive_advantage':'NOT_ESTABLISHED'}
