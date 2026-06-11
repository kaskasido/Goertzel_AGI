"""PLN-Inferenz-Engine: Vorwaerts- und Rueckwaertsverkettung auf dem Atomspace.

Der Forward Chainer kombiniert vorhandene Inheritance-/Implication-Links per
Deduktion, Induktion, Abduktion und Inversion und schreibt neue Links (mit
revidierten TruthValues) zurueck in den Atomspace. Der Backward Chainer
beantwortet Zielanfragen wie "(Inheritance Sokrates sterblich)?" durch
rekursive Suche nach Beweisketten.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple

from ..core.atom import Atom, ConceptNode, ImplicationLink, InheritanceLink, Link, Node
from ..core.atomspace import AtomSpace
from ..core.truthvalue import TruthValue, UNKNOWN
from . import rules

# Linktypen, auf denen die Termlogik-Regeln operieren
CHAINABLE = (InheritanceLink, ImplicationLink)

MIN_CONFIDENCE = 0.01  # Schlussfolgerungen unterhalb davon werden verworfen


@dataclass
class InferenceStep:
    rule: str
    premises: Tuple[Atom, ...]
    conclusion: Atom

    def __repr__(self) -> str:
        prem = " ; ".join(repr(p) for p in self.premises)
        return f"[{self.rule}] {prem}  |-  {self.conclusion!r}"


@dataclass
class InferenceResult:
    conclusion: Optional[Atom]
    trace: List[InferenceStep] = field(default_factory=list)

    @property
    def tv(self) -> TruthValue:
        return self.conclusion.tv if self.conclusion is not None else UNKNOWN


def _term_tv(atomspace: AtomSpace, atom: Atom) -> TruthValue:
    """Term-Wahrscheinlichkeit eines Konzepts (Prior); Default 0.5/niedrig."""
    stored = atomspace.get(atom)
    if stored is not None and stored.tv.confidence > 0:
        return stored.tv
    return TruthValue(0.5, 0.1)


class ForwardChainer:
    """Wendet PLN-Regeln erschoepfend (bis max_steps) auf den Atomspace an."""

    def __init__(self, atomspace: AtomSpace):
        self.atomspace = atomspace
        # Persistente Evidenzbuchhaltung: dieselbe Praemissen-Kombination darf
        # nur EINMAL in eine Konklusion einfliessen, sonst zaehlt Revision
        # dieselbe Evidenz mehrfach und die Konfidenz steigt kuenstlich
        # (vgl. EvidenceID-Tracking im trueagi-io/PLN-Repo).
        self._seen: Set[tuple] = set()

    def run(self, max_steps: int = 100) -> List[InferenceStep]:
        steps: List[InferenceStep] = []
        for _ in range(max_steps):
            new_step = self._one_step(self._seen)
            if new_step is None:
                break
            steps.append(new_step)
        return steps

    def _one_step(self, seen: Set[tuple]) -> Optional[InferenceStep]:
        links = [l for l in self.atomspace if isinstance(l, CHAINABLE) and l.tv.confidence > 0]
        for ab in links:
            for bc in links:
                if ab is bc or type(ab) is not type(bc):
                    continue
                step = self._try_deduction(ab, bc, seen)
                if step is not None:
                    return step
                step = self._try_induction(ab, bc, seen)
                if step is not None:
                    return step
                step = self._try_abduction(ab, bc, seen)
                if step is not None:
                    return step
        return None

    # (A->B), (B->C) => (A->C)
    def _try_deduction(self, ab: Link, bc: Link, seen: Set[tuple]) -> Optional[InferenceStep]:
        a, b = ab.outgoing
        b2, c = bc.outgoing
        if b.key != b2.key or a.key == c.key:
            return None
        sig = ("ded", ab.key, bc.key)
        if sig in seen:
            return None
        seen.add(sig)
        tv = rules.deduction(ab.tv, bc.tv, _term_tv(self.atomspace, a),
                             _term_tv(self.atomspace, b), _term_tv(self.atomspace, c))
        return self._commit("Deduction", type(ab), a, c, tv, (ab, bc))

    # (A->B), (A->C) => (B->C)
    def _try_induction(self, ab: Link, ac: Link, seen: Set[tuple]) -> Optional[InferenceStep]:
        a, b = ab.outgoing
        a2, c = ac.outgoing
        if a.key != a2.key or b.key == c.key:
            return None
        sig = ("ind", ab.key, ac.key)
        if sig in seen:
            return None
        seen.add(sig)
        tv = rules.induction(ab.tv, ac.tv, _term_tv(self.atomspace, a),
                             _term_tv(self.atomspace, b), _term_tv(self.atomspace, c))
        return self._commit("Induction", type(ab), b, c, tv, (ab, ac))

    # (A->C), (B->C) => (A->B)
    def _try_abduction(self, ac: Link, bc: Link, seen: Set[tuple]) -> Optional[InferenceStep]:
        a, c = ac.outgoing
        b, c2 = bc.outgoing
        if c.key != c2.key or a.key == b.key:
            return None
        sig = ("abd", ac.key, bc.key)
        if sig in seen:
            return None
        seen.add(sig)
        tv = rules.abduction(ac.tv, bc.tv, _term_tv(self.atomspace, a),
                             _term_tv(self.atomspace, b), _term_tv(self.atomspace, c))
        return self._commit("Abduction", type(ac), a, b, tv, (ac, bc))

    def _commit(self, rule: str, link_cls, src: Atom, dst: Atom,
                tv: TruthValue, premises: Tuple[Link, ...]) -> Optional[InferenceStep]:
        if tv.confidence < MIN_CONFIDENCE:
            return None
        conclusion = self.atomspace.add(link_cls(src, dst, tv=tv))
        return InferenceStep(rule, premises, conclusion)


class BackwardChainer:
    """Beantwortet Zielanfragen durch rekursive Beweissuche (Deduktionsketten)."""

    def __init__(self, atomspace: AtomSpace):
        self.atomspace = atomspace

    def prove(self, goal: Link, max_depth: int = 5) -> InferenceResult:
        if not isinstance(goal, CHAINABLE):
            raise TypeError("BackwardChainer expects Inheritance/Implication goals")
        trace: List[InferenceStep] = []
        tv = self._prove(type(goal), goal.outgoing[0], goal.outgoing[1],
                         max_depth, trace, frozenset())
        if tv is None:
            return InferenceResult(None, trace)
        conclusion = self.atomspace.add(type(goal)(*goal.outgoing, tv=tv))
        return InferenceResult(conclusion, trace)

    def _prove(self, link_cls, a: Atom, c: Atom, depth: int,
               trace: List[InferenceStep], visited: frozenset) -> Optional[TruthValue]:
        direct = self.atomspace.get(link_cls(a, c))
        if direct is not None and direct.tv.confidence > 0:
            return direct.tv
        if depth <= 0:
            return None
        state = (a.key, c.key)
        if state in visited:
            return None
        visited = visited | {state}

        best: Optional[TruthValue] = None
        # Suche Zwischenterm B mit bekanntem (A->B); beweise (B->C) rekursiv.
        for ab in self.atomspace.incoming(a):
            if not isinstance(ab, link_cls) or ab.outgoing[0].key != a.key:
                continue
            b = ab.outgoing[1]
            if b.key == c.key:
                continue
            tv_bc = self._prove(link_cls, b, c, depth - 1, trace, visited)
            if tv_bc is None:
                continue
            tv = rules.deduction(ab.tv, tv_bc, _term_tv(self.atomspace, a),
                                 _term_tv(self.atomspace, b), _term_tv(self.atomspace, c))
            if tv.confidence < MIN_CONFIDENCE:
                continue
            bc_link = self.atomspace.add(link_cls(b, c, tv=tv_bc))
            conclusion = link_cls(a, c, tv=tv)
            trace.append(InferenceStep("Deduction", (ab, bc_link), conclusion))
            best = tv if best is None else best.revise(tv)
        return best
