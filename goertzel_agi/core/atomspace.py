"""Atomspace: zentraler Wissens-Metagraph mit Pattern Matching.

Alle kognitiven Prozesse (PLN, ECAN, MOSES, Wahrnehmung, Ziele) lesen und
schreiben denselben Atomspace — das ist die strukturelle Grundlage von
Goertzels "Cognitive Synergy": Prozesse helfen einander ueber das gemeinsame
Substrat, statt isolierte Module zu sein.
"""

from __future__ import annotations

from typing import Callable, Dict, Iterable, Iterator, List, Optional, Type

from .atom import Atom, Bindings, Link, Node, VariableNode
from .truthvalue import TruthValue


class AtomSpace:
    def __init__(self) -> None:
        self._atoms: Dict[tuple, Atom] = {}
        # Index: Atom-Key -> Links, die darauf zeigen (incoming set)
        self._incoming: Dict[tuple, List[Link]] = {}

    # ---- Hinzufuegen / Nachschlagen --------------------------------------
    def add(self, atom: Atom) -> Atom:
        """Fuegt ein Atom ein (dedupliziert). Existiert es schon, werden die
        TruthValues per PLN-Revision fusioniert."""
        existing = self._atoms.get(atom.key)
        if existing is not None:
            if atom.tv.confidence > 0:
                existing.tv = existing.tv.revise(atom.tv)
            return existing
        if isinstance(atom, Link):
            atom = type(atom)(*[self.add(o) for o in atom.outgoing], tv=atom.tv)
        self._atoms[atom.key] = atom
        if isinstance(atom, Link):
            for out in atom.outgoing:
                self._incoming.setdefault(out.key, []).append(atom)
        return atom

    def get(self, atom: Atom) -> Optional[Atom]:
        return self._atoms.get(atom.key)

    def node(self, cls: Type[Node], name: str) -> Optional[Node]:
        return self._atoms.get((cls.__name__, name))  # type: ignore[return-value]

    def incoming(self, atom: Atom) -> List[Link]:
        return list(self._incoming.get(atom.key, []))

    def remove(self, atom: Atom) -> bool:
        """Entfernt ein Atom, sofern kein Link mehr darauf zeigt."""
        if self._incoming.get(atom.key):
            return False
        stored = self._atoms.pop(atom.key, None)
        if stored is None:
            return False
        if isinstance(stored, Link):
            for out in stored.outgoing:
                inc = self._incoming.get(out.key, [])
                self._incoming[out.key] = [l for l in inc if l.key != stored.key]
        return True

    def __len__(self) -> int:
        return len(self._atoms)

    def __iter__(self) -> Iterator[Atom]:
        return iter(list(self._atoms.values()))

    def atoms_of_type(self, cls: Type[Atom]) -> List[Atom]:
        return [a for a in self._atoms.values() if isinstance(a, cls)]

    # ---- Pattern Matching --------------------------------------------------
    # Muster sind Atome, die VariableNodes ("$x") enthalten koennen.
    def match(self, pattern: Atom, bindings: Bindings | None = None) -> List[Bindings]:
        bindings = bindings or Bindings()
        results: List[Bindings] = []
        for candidate in self._candidates(pattern):
            b = self._unify(pattern, candidate, bindings)
            if b is not None:
                results.append(b)
        return results

    def match_all(self, patterns: Iterable[Atom]) -> List[Bindings]:
        """Konjunktive Anfrage: alle Muster muessen mit konsistenter Belegung matchen."""
        solutions = [Bindings()]
        for pattern in patterns:
            next_solutions: List[Bindings] = []
            for sol in solutions:
                next_solutions.extend(self.match(pattern, sol))
            solutions = next_solutions
            if not solutions:
                break
        return solutions

    def instantiate(self, pattern: Atom, bindings: Bindings) -> Atom:
        """Setzt eine Variablenbelegung in ein Muster ein."""
        if isinstance(pattern, VariableNode):
            bound = bindings.get(pattern.name)
            return bound if bound is not None else pattern
        if isinstance(pattern, Link):
            return type(pattern)(
                *[self.instantiate(o, bindings) for o in pattern.outgoing],
                tv=pattern.tv,
            )
        return pattern

    def _candidates(self, pattern: Atom) -> Iterable[Atom]:
        if isinstance(pattern, VariableNode):
            return list(self._atoms.values())
        if isinstance(pattern, Node):
            found = self._atoms.get(pattern.key)
            return [found] if found else []
        # Link: gleiche Typen, gleiche Aritaet
        assert isinstance(pattern, Link)
        return [
            a
            for a in self._atoms.values()
            if isinstance(a, type(pattern)) and len(a.outgoing) == len(pattern.outgoing)
        ]

    def _unify(self, pattern: Atom, target: Atom, bindings: Bindings) -> Bindings | None:
        if isinstance(pattern, VariableNode):
            return bindings.extended(pattern.name, target)
        if isinstance(pattern, Node):
            return bindings if pattern.key == target.key else None
        if isinstance(pattern, Link) and isinstance(target, Link):
            if type(pattern) is not type(target) or len(pattern.outgoing) != len(target.outgoing):
                return None
            current: Bindings | None = bindings
            for p, t in zip(pattern.outgoing, target.outgoing):
                current = self._unify(p, t, current)
                if current is None:
                    return None
            return current
        return None

    # ---- Komfort -----------------------------------------------------------
    def set_tv(self, atom: Atom, tv: TruthValue) -> Atom:
        stored = self.add(atom)
        stored.tv = tv
        return stored

    def dump(self, predicate: Callable[[Atom], bool] | None = None) -> str:
        lines = [repr(a) for a in self if predicate is None or predicate(a)]
        return "\n".join(sorted(lines))
