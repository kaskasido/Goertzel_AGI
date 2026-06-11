"""MOSES-inspiriertes evolutionaeres Programmlernen (vereinfacht).

MOSES (Meta-Optimizing Semantic Evolutionary Search, Looks/Goertzel) lernt
kleine Programme — hier: boolesche Ausdrucksbaeume ueber benannten Merkmalen —
aus Beispieldaten. In Goertzels Architektur liefert dieser Prozess Kreativitaet
und prozedurales Lernen, komplementaer zu PLN (Schlussfolgern) und ECAN
(Relevanz). Gelernte Programme werden als Atome ins Atomspace zurueckgeschrieben,
wo PLN ueber sie weiter schliessen kann (kognitive Synergie).

Vereinfachungen gegenueber echtem MOSES: keine Demes/Representation-Building,
nur Turnierselektion + Subtree-Mutation/-Crossover mit Groessenstrafe.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

Example = Tuple[Dict[str, bool], bool]  # (Merkmalsbelegung, Zielwert)


# ---- Programmbaeume ----------------------------------------------------------
@dataclass(frozen=True)
class Expr:
    op: str  # "var" | "not" | "and" | "or"
    name: str = ""  # bei "var"
    children: Tuple["Expr", ...] = ()

    def evaluate(self, env: Dict[str, bool]) -> bool:
        if self.op == "var":
            return env.get(self.name, False)
        if self.op == "not":
            return not self.children[0].evaluate(env)
        if self.op == "and":
            return all(c.evaluate(env) for c in self.children)
        if self.op == "or":
            return any(c.evaluate(env) for c in self.children)
        raise ValueError(self.op)

    def size(self) -> int:
        return 1 + sum(c.size() for c in self.children)

    def __str__(self) -> str:
        if self.op == "var":
            return self.name
        if self.op == "not":
            return f"(not {self.children[0]})"
        return "(" + f" {self.op} ".join(str(c) for c in self.children) + ")"


def _random_expr(features: Sequence[str], depth: int, rng: random.Random) -> Expr:
    if depth <= 0 or rng.random() < 0.4:
        return Expr("var", name=rng.choice(list(features)))
    op = rng.choice(["not", "and", "or"])
    if op == "not":
        return Expr("not", children=(_random_expr(features, depth - 1, rng),))
    return Expr(op, children=(
        _random_expr(features, depth - 1, rng),
        _random_expr(features, depth - 1, rng),
    ))


def _subtrees(e: Expr) -> List[Expr]:
    out = [e]
    for c in e.children:
        out.extend(_subtrees(c))
    return out


def _replace(e: Expr, target: Expr, repl: Expr) -> Expr:
    if e is target:
        return repl
    if not e.children:
        return e
    return Expr(e.op, e.name, tuple(_replace(c, target, repl) for c in e.children))


# ---- Evolutionsschleife ------------------------------------------------------
@dataclass
class MosesResult:
    program: Expr
    accuracy: float
    generations: int


class MosesLearner:
    def __init__(
        self,
        features: Sequence[str],
        population_size: int = 80,
        max_depth: int = 4,
        size_penalty: float = 0.005,
        seed: Optional[int] = None,
    ) -> None:
        self.features = list(features)
        self.population_size = population_size
        self.max_depth = max_depth
        self.size_penalty = size_penalty
        self.rng = random.Random(seed)

    def fitness(self, expr: Expr, examples: Sequence[Example]) -> float:
        correct = sum(1 for env, label in examples if expr.evaluate(env) == label)
        # Occam-Bias: kuerzere Programme bevorzugen (MOSES' Parsimony Pressure)
        return correct / len(examples) - self.size_penalty * expr.size()

    def learn(self, examples: Sequence[Example], generations: int = 60) -> MosesResult:
        pop = [_random_expr(self.features, self.max_depth, self.rng)
               for _ in range(self.population_size)]
        best, best_fit = None, float("-inf")
        for gen in range(generations):
            scored = [(self.fitness(e, examples), e) for e in pop]
            scored.sort(key=lambda t: t[0], reverse=True)
            if scored[0][0] > best_fit:
                best_fit, best = scored[0][0], scored[0][1]
            accuracy = sum(1 for env, l in examples if best.evaluate(env) == l) / len(examples)
            if accuracy >= 1.0:
                return MosesResult(best, accuracy, gen + 1)
            pop = self._next_generation([e for _, e in scored])
        accuracy = sum(1 for env, l in examples if best.evaluate(env) == l) / len(examples)
        return MosesResult(best, accuracy, generations)

    def _next_generation(self, ranked: List[Expr]) -> List[Expr]:
        elite = ranked[: max(2, self.population_size // 10)]
        children: List[Expr] = list(elite)
        while len(children) < self.population_size:
            if self.rng.random() < 0.5:
                children.append(self._mutate(self._tournament(ranked)))
            else:
                children.append(self._crossover(self._tournament(ranked),
                                                self._tournament(ranked)))
        return children

    def _tournament(self, ranked: List[Expr], k: int = 3) -> Expr:
        picks = [self.rng.randrange(len(ranked)) for _ in range(k)]
        return ranked[min(picks)]  # ranked ist absteigend sortiert

    def _mutate(self, e: Expr) -> Expr:
        target = self.rng.choice(_subtrees(e))
        repl = _random_expr(self.features, 2, self.rng)
        return _replace(e, target, repl)

    def _crossover(self, a: Expr, b: Expr) -> Expr:
        target = self.rng.choice(_subtrees(a))
        donor = self.rng.choice(_subtrees(b))
        return _replace(a, target, donor)
