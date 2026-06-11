"""ECAN — Economic Attention Networks (Aufmerksamkeitsallokation).

Goertzels Antwort auf das Relevanzproblem: Atome konkurrieren oekonomisch um
Aufmerksamkeit. Kernideen aus OpenCog:

  - STI (Short-Term Importance): Waehrung fuer "jetzt relevant".
    Stimulus (z.B. durch Wahrnehmung oder erfolgreiche Inferenz) zahlt STI ein.
  - Rent: Jedes Atom zahlt pro Zyklus STI-Miete -> Vergessen ist der Default.
  - Spreading: STI fliesst entlang von Links zu Nachbarn -> assoziative
    Aktivierungsausbreitung wie in semantischen Netzen.
  - Attentional Focus (AF): die STI-staerksten Atome; nur sie werden von
    teuren Prozessen (PLN-Inferenz) betrachtet -> beherrschbare Komplexitaet.
  - LTI/Forgetting: Atome mit erschoepftem LTI werden entfernt.
"""

from __future__ import annotations

from typing import List

from ..core.atom import Atom, Link
from ..core.atomspace import AtomSpace


class AttentionBank:
    def __init__(
        self,
        atomspace: AtomSpace,
        focus_size: int = 20,
        sti_rent: float = 1.0,
        spread_fraction: float = 0.2,
        lti_decay: float = 0.05,
    ) -> None:
        self.atomspace = atomspace
        self.focus_size = focus_size
        self.sti_rent = sti_rent
        self.spread_fraction = spread_fraction
        self.lti_decay = lti_decay

    # ---- Stimulus ----------------------------------------------------------
    def stimulate(self, atom: Atom, amount: float) -> None:
        stored = self.atomspace.add(atom)
        stored.av.sti += amount
        stored.av.lti += amount * 0.1  # wiederholt Stimuliertes wird langzeitwichtig

    # ---- Ein ECAN-Zyklus ----------------------------------------------------
    def step(self) -> None:
        self._spread()
        self._collect_rent()
        self._forget()

    def _spread(self) -> None:
        """STI fliesst von jedem Atom anteilig zu direkt verbundenen Atomen."""
        transfers: List[tuple[Atom, float]] = []
        for atom in self.atomspace:
            if atom.av.sti <= 0:
                continue
            neighbors: List[Atom] = []
            if isinstance(atom, Link):
                neighbors.extend(atom.outgoing)
            neighbors.extend(self.atomspace.incoming(atom))
            if not neighbors:
                continue
            budget = atom.av.sti * self.spread_fraction
            atom.av.sti -= budget
            share = budget / len(neighbors)
            transfers.extend((n, share) for n in neighbors)
        for atom, share in transfers:
            atom.av.sti += share

    def _collect_rent(self) -> None:
        for atom in self.atomspace:
            if atom.av.sti > 0:
                atom.av.sti = max(0.0, atom.av.sti - self.sti_rent)
            if not atom.av.vlti:
                atom.av.lti = max(0.0, atom.av.lti - self.lti_decay)

    def _forget(self) -> None:
        """Entfernt unwichtige Atome (LTI und STI erschoepft, nicht VLTI)."""
        doomed = [
            a for a in self.atomspace
            if not a.av.vlti and a.av.sti <= 0 and a.av.lti <= 0 and a.tv.confidence < 0.5
        ]
        for atom in doomed:
            self.atomspace.remove(atom)  # scheitert harmlos bei incoming links

    # ---- Attentional Focus ---------------------------------------------------
    def focus(self) -> List[Atom]:
        ranked = sorted(self.atomspace, key=lambda a: a.av.sti, reverse=True)
        return [a for a in ranked[: self.focus_size] if a.av.sti > 0]
