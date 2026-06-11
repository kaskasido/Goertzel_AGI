"""Zielsystem nach dem OpenPsi-Modell (CogPrime-Motivationsschicht).

OpenPsi (nach Doerners Psi-Theorie, in OpenCog adaptiert) modelliert
Motivation als Menge von "Demands" (Beduerfnissen) mit Soll- und Ist-Wert.
Abweichungen erzeugen "Urges", die Ziele aktivieren; Ziele stimulieren die
zugehoerigen Atome im Atomspace und lenken so ECAN-Aufmerksamkeit und
PLN-Inferenz auf zielrelevantes Wissen — Top-down-Steuerung der Kognition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from ..core.atom import Atom, ConceptNode
from .base import CycleReport, MindAgent


@dataclass
class Demand:
    name: str
    target: float = 1.0  # Sollwert in [0,1]
    level: float = 0.5   # Istwert in [0,1]
    weight: float = 1.0  # Wichtigkeit des Beduerfnisses
    decay: float = 0.02  # Beduerfnisse "verhungern" langsam ohne Befriedigung
    protected: bool = False  # Kern-Demand: darf nie entfernt werden (Metagoal)
    related_atoms: List[Atom] = field(default_factory=list)

    @property
    def urge(self) -> float:
        return self.weight * max(0.0, self.target - self.level)

    def satisfy(self, amount: float) -> None:
        self.level = min(1.0, self.level + amount)


class GoalAgent(MindAgent):
    """Verwaltet Demands und uebersetzt Urges in Atomspace-Stimulation.

    Metagoals-Waechter (nach Goertzel, "Metagoals Endowing Self-Modifying
    AGI Systems with Goal Stability or Moderated Goal Evolution",
    arXiv:2412.16559): Ein selbstmodifizierendes System braucht Invarianten
    im Zielsystem, sonst kann es seine eigenen Werte zerstoeren. Hier in
    Miniatur umgesetzt als zwei harte Regeln:

      1. Goal Stability:  geschuetzte Kern-Demands koennen nie entfernt und
         nie auf Gewicht/Sollwert 0 gesetzt werden.
      2. Moderated Goal Evolution:  Zielparameter aendern sich pro Aufruf
         hoechstens um MAX_DRIFT (Kontraktions-Idee: kleine Schritte statt
         Spruenge), sodass Zielevolution moeglich, aber gedaempft ist.

    Jede abgelehnte oder gedaempfte Aenderung wird in metagoal_log
    protokolliert — Selbstmodifikation bleibt auditierbar.
    """

    name = "GoalAgent"

    MAX_DRIFT = 0.2          # max. relative Aenderung von weight/target pro Aufruf
    MIN_PROTECTED = 0.05     # Untergrenze fuer geschuetzte Demands

    def __init__(self, atomspace, attention) -> None:
        super().__init__(atomspace, attention)
        self.demands: Dict[str, Demand] = {}
        self.metagoal_log: List[str] = []

    def add_demand(self, demand: Demand) -> Demand:
        self.demands[demand.name] = demand
        # Jedes Demand bekommt ein Konzept-Atom, damit anderes Wissen
        # explizit darauf Bezug nehmen kann (z.B. via PLN-Implikationen).
        node = self.atomspace.add(ConceptNode(f"demand:{demand.name}"))
        node.av.vlti = True
        demand.related_atoms.append(node)
        return demand

    # ---- Metagoals-Waechter --------------------------------------------------
    def remove_demand(self, name: str) -> bool:
        """Entfernt ein Demand — ausser es ist geschuetzt (Goal Stability)."""
        demand = self.demands.get(name)
        if demand is None:
            return False
        if demand.protected:
            self.metagoal_log.append(
                f"VETO: Entfernen des geschuetzten Demands '{name}' verweigert"
            )
            return False
        del self.demands[name]
        return True

    def request_change(self, name: str, weight: float | None = None,
                       target: float | None = None) -> bool:
        """Zielevolution mit Daempfung: Aenderungen werden auf MAX_DRIFT
        relativ zum aktuellen Wert begrenzt; geschuetzte Demands behalten
        eine Untergrenze. Gibt False zurueck, wenn nichts geaendert wurde."""
        demand = self.demands.get(name)
        if demand is None:
            return False
        changed = False
        for attr, requested in (("weight", weight), ("target", target)):
            if requested is None:
                continue
            current = getattr(demand, attr)
            low = current * (1.0 - self.MAX_DRIFT)
            high = current * (1.0 + self.MAX_DRIFT)
            clamped = max(low, min(high, requested))
            if demand.protected:
                clamped = max(self.MIN_PROTECTED, clamped)
            if clamped != requested:
                self.metagoal_log.append(
                    f"GEDAEMPFT: {name}.{attr} {requested:.3f} -> {clamped:.3f} "
                    f"(MAX_DRIFT={self.MAX_DRIFT})"
                )
            if clamped != current:
                setattr(demand, attr, clamped)
                changed = True
        return changed

    def most_urgent(self) -> Demand | None:
        active = [d for d in self.demands.values() if d.urge > 0]
        return max(active, key=lambda d: d.urge) if active else None

    def step(self) -> CycleReport:
        report = CycleReport(self.name)
        for demand in self.demands.values():
            demand.level = max(0.0, demand.level - demand.decay)
            if demand.urge <= 0:
                continue
            # Urge -> Aufmerksamkeit: zielrelevante Atome werden "heiss"
            for atom in demand.related_atoms:
                self.attention.stimulate(atom, demand.urge * 10.0)
            report.note(f"urge {demand.name}={demand.urge:.2f} -> stimulated "
                        f"{len(demand.related_atoms)} atoms")
        top = self.most_urgent()
        report.data["most_urgent"] = top.name if top else None
        return report
