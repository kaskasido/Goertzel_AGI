"""Reasoning-Agent: PLN-Inferenz, fokussiert durch ECAN.

Kognitive Synergie in Aktion: Der Agent laesst PLN nicht blind ueber das
gesamte Wissen laufen (kombinatorische Explosion!), sondern bevorzugt Links,
deren Atome im Attentional Focus liegen — d.h. Wahrnehmung und Ziele steuern,
WORUEBER nachgedacht wird. Neue Schlussfolgerungen werden stimuliert, damit
Folgeinferenzen darauf aufbauen koennen.
"""

from __future__ import annotations

from typing import List

from ..core.atom import ImplicationLink, InheritanceLink, Link
from ..pln.engine import BackwardChainer, ForwardChainer, InferenceResult
from ..pln.relations import TRANSITIVE_RELATIONS, close_all
from .base import CycleReport, MindAgent


class ReasoningAgent(MindAgent):
    name = "ReasoningAgent"

    def __init__(self, atomspace, attention, steps_per_cycle: int = 10,
                 transitive_relations=TRANSITIVE_RELATIONS) -> None:
        super().__init__(atomspace, attention)
        self.forward = ForwardChainer(atomspace)
        self.backward = BackwardChainer(atomspace)
        self.steps_per_cycle = steps_per_cycle
        self.transitive_relations = transitive_relations

    def step(self) -> CycleReport:
        report = CycleReport(self.name)
        focus_keys = {a.key for a in self.attention.focus()}
        steps = self.forward.run(max_steps=self.steps_per_cycle)
        for s in steps:
            # Fokus-Bonus: Schluesse ueber "heisse" Atome werden selbst heiss
            in_focus = any(p.key in focus_keys for p in s.premises)
            self.attention.stimulate(s.conclusion, 15.0 if in_focus else 5.0)
            report.note(f"{'*' if in_focus else ' '} {s}")
        # Kausal-/Teil-Ganzes-Ketten erschliessen (Rahmenerweiterung)
        relational = close_all(self.atomspace, self.transitive_relations)
        for link in relational:
            self.attention.stimulate(link, 6.0)
            report.note(f"  [relational] {link!r}")
        report.data["new_inferences"] = len(steps) + len(relational)
        return report

    # ---- Anfragen von aussen (z.B. Nutzerfragen) ---------------------------
    def query(self, goal: Link, max_depth: int = 5) -> InferenceResult:
        """Backward Chaining: 'Gilt (Inheritance A B)?' mit Beweisspur."""
        result = self.backward.prove(goal, max_depth=max_depth)
        if result.conclusion is not None:
            self.attention.stimulate(result.conclusion, 25.0)
        return result
