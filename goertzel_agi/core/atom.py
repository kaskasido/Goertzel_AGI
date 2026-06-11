"""Atome: die Grundbausteine des Atomspace (OpenCog / Hyperon).

Goertzels Wissensrepraesentation ist ein gewichteter, getypter Metagraph:
  - Nodes:  benannte Konzepte/Praedikate/Variablen
  - Links:  getypte (Hyper-)Kanten zwischen Atomen, selbst wieder Atome

Jedes Atom traegt einen TruthValue (PLN) und einen AttentionValue (ECAN).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

from .truthvalue import TruthValue, UNKNOWN


@dataclass
class AttentionValue:
    """ECAN-Aufmerksamkeitswerte.

    sti: Short-Term Importance — wie relevant ist das Atom JETZT
    lti: Long-Term Importance — wie wichtig ist es, das Atom zu behalten
    vlti: Very Long-Term Importance — nie vergessen (z.B. Grundwissen)
    """

    sti: float = 0.0
    lti: float = 0.0
    vlti: bool = False


class Atom:
    """Basisklasse. Atome sind nach (Typ, Name/Outgoing) eindeutig im Atomspace."""

    __slots__ = ("tv", "av")

    def __init__(self, tv: TruthValue | None = None):
        self.tv: TruthValue = tv if tv is not None else UNKNOWN
        self.av: AttentionValue = AttentionValue()

    @property
    def key(self):  # Identitaetsschluessel fuer Deduplizierung
        raise NotImplementedError

    @property
    def atom_type(self) -> str:
        return type(self).__name__


class Node(Atom):
    __slots__ = ("name",)

    def __init__(self, name: str, tv: TruthValue | None = None):
        super().__init__(tv)
        self.name = name

    @property
    def key(self):
        return (self.atom_type, self.name)

    def __repr__(self) -> str:
        return f"({self.atom_type} \"{self.name}\" {self.tv})"


class ConceptNode(Node):
    """Ein Konzept, z.B. (ConceptNode "Mensch")."""


class PredicateNode(Node):
    """Ein Praedikat, z.B. (PredicateNode "isst")."""


class VariableNode(Node):
    """Variable fuer Pattern Matching, Konvention: Name beginnt mit $."""


class Link(Atom):
    __slots__ = ("outgoing",)

    def __init__(self, *outgoing: Atom, tv: TruthValue | None = None):
        super().__init__(tv)
        self.outgoing: Tuple[Atom, ...] = tuple(outgoing)

    @property
    def key(self):
        return (self.atom_type, tuple(a.key for a in self.outgoing))

    def __repr__(self) -> str:
        inner = " ".join(repr(a) for a in self.outgoing)
        return f"({self.atom_type} {self.tv} {inner})"


class InheritanceLink(Link):
    """Asymmetrische Vererbung/Subsumption: (Inheritance A B) ~ "A ist ein B".

    Kern der PLN-Termlogik; Deduktion/Induktion/Abduktion operieren darauf.
    """


class SimilarityLink(Link):
    """Symmetrische Aehnlichkeit zwischen Konzepten."""


class EvaluationLink(Link):
    """Praedikat-Anwendung: (Evaluation (Predicate "isst") (List Anna Apfel))."""


class ListLink(Link):
    """Geordnetes Tupel von Argumenten."""


class ImplicationLink(Link):
    """Logische Implikation zwischen Praedikaten/Aussagen."""


class AndLink(Link):
    pass


class OrLink(Link):
    pass


class NotLink(Link):
    pass


class MemberLink(Link):
    """Element-Beziehung (extensional)."""


class ContextLink(Link):
    """Kontextualisierte Aussage: (Context C A) — A gilt im Kontext C."""


@dataclass(frozen=True)
class Bindings:
    """Variablenbelegung eines Pattern-Matches (immutabel)."""

    mapping: tuple = field(default_factory=tuple)  # ((varname, Atom), ...)

    def get(self, var: str):
        for name, atom in self.mapping:
            if name == var:
                return atom
        return None

    def extended(self, var: str, atom: Atom) -> "Bindings | None":
        existing = self.get(var)
        if existing is not None:
            return self if existing.key == atom.key else None
        return Bindings(self.mapping + ((var, atom),))

    def as_dict(self):
        return dict(self.mapping)
