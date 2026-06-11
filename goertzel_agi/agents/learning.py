"""Lern-Agent: MOSES-Programmlernen + einfacher Pattern Miner.

Zwei Lernmodi nach CogPrime:
  1. Prozedurales Lernen (MOSES): lernt boolesche Klassifikatoren aus
     gesammelten Beispielen und legt sie als benannte Praedikate ab.
  2. Pattern Mining: findet haeufige Strukturen im Atomspace (hier: Konzepte,
     die viele Inheritance-Eltern teilen) und schlaegt SimilarityLinks vor —
     deklaratives Lernen aus dem eigenen Wissensbestand.

Beides schreibt ins Atomspace zurueck, sodass PLN ueber Gelerntes schliessen
kann und ECAN Gelerntes nach Nuetzlichkeit bewertet.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Sequence, Tuple

from ..core.atom import ConceptNode, InheritanceLink, PredicateNode, SimilarityLink
from ..core.truthvalue import TruthValue
from ..moses.evolution import Example, MosesLearner, MosesResult
from .base import CycleReport, MindAgent

MINED_TV = TruthValue(0.8, 0.4)  # gemustertes Wissen: plausibel, wenig Evidenz


class LearningAgent(MindAgent):
    name = "LearningAgent"

    def __init__(self, atomspace, attention, min_shared_parents: int = 2,
                 seed: int | None = None) -> None:
        super().__init__(atomspace, attention)
        self.min_shared_parents = min_shared_parents
        self.seed = seed
        # Trainingsdaten pro Zielkonzept: {name: [(features, label), ...]}
        self.datasets: Dict[str, List[Example]] = defaultdict(list)
        self.learned: Dict[str, MosesResult] = {}

    # ---- Prozedurales Lernen (MOSES) ---------------------------------------
    def add_example(self, concept: str, features: Dict[str, bool], label: bool) -> None:
        self.datasets[concept].append((features, label))

    def _learn_procedures(self, report: CycleReport) -> None:
        for concept, examples in list(self.datasets.items()):
            if len(examples) < 4 or concept in self.learned:
                continue
            features = sorted({f for env, _ in examples for f in env})
            learner = MosesLearner(features, seed=self.seed)
            result = learner.learn(examples)
            self.learned[concept] = result
            predicate = self.atomspace.add(
                PredicateNode(f"learned:{concept}",
                              tv=TruthValue(result.accuracy, 0.5))
            )
            self.attention.stimulate(predicate, 20.0)
            report.note(
                f"MOSES learned '{concept}': {result.program} "
                f"(accuracy={result.accuracy:.2f}, gen={result.generations})"
            )

    # ---- Pattern Mining ------------------------------------------------------
    def _mine_similarities(self, report: CycleReport) -> None:
        parents: Dict[tuple, set] = defaultdict(set)  # child.key -> {parent.key}
        atoms_by_key = {}
        for link in self.atomspace.atoms_of_type(InheritanceLink):
            child, parent = link.outgoing
            parents[child.key].add(parent.key)
            atoms_by_key[child.key] = child
        children = list(parents)
        for i, a in enumerate(children):
            for b in children[i + 1:]:
                shared = parents[a] & parents[b]
                if len(shared) < self.min_shared_parents:
                    continue
                sim = SimilarityLink(atoms_by_key[a], atoms_by_key[b], tv=MINED_TV)
                if self.atomspace.get(sim) is not None:
                    continue
                stored = self.atomspace.add(sim)
                self.attention.stimulate(stored, 10.0)
                report.note(f"mined: {stored!r} (shared parents: {len(shared)})")

    def step(self) -> CycleReport:
        report = CycleReport(self.name)
        self._learn_procedures(report)
        self._mine_similarities(report)
        return report
