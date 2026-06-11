"""Relationale Inferenz ueber benannten Relationen (Rahmenerweiterung).

Die PLN-Termlogik (rules.py/engine.py) operiert auf Inheritance/Implication.
Fuer ein Fachsystem braucht man aber auch Schluesse ueber gerichtete
Sachrelationen wie "verursacht", "ist_teil_von", "fuehrt_zu". Diese liegen
als EvaluationLink(PredicateNode(rel), ListLink(A, B)) im Atomspace.

Hier: transitive Schliessung fuer als transitiv deklarierte Relationen —
"A verursacht B, B verursacht C  =>  A verursacht C" (gedaempft). Das
erschliesst die "Warum"-Fragenklasse fuer Kausalketten, ohne den
Termlogik-Kern aufzuweichen. Konfidenz sinkt pro Kettenschritt (Kausalitaet
ueber viele Glieder ist unsicherer).
"""

from __future__ import annotations

from typing import List, Set, Tuple

from ..core.atom import ConceptNode, EvaluationLink, ListLink, PredicateNode
from ..core.atomspace import AtomSpace
from ..core.truthvalue import TruthValue

# Standardmaessig als transitiv behandelte Relationen (deutsch + englisch)
TRANSITIVE_RELATIONS = (
    "verursacht", "fuehrt_zu", "ist_teil_von", "gehoert_zu",
    "causes", "leads_to", "is_part_of", "part_of", "belongs_to", "contains",
)

CHAIN_DISCOUNT = 0.85  # Konfidenz-Abschlag pro Kettenglied
MIN_CONFIDENCE = 0.05


def _pairs(atomspace: AtomSpace, predicate: str) -> List[Tuple]:
    """Alle (A, B, tv) fuer EvaluationLink(predicate, (A, B))."""
    pred = atomspace.node(PredicateNode, predicate)
    if pred is None:
        return []
    out = []
    for link in atomspace.atoms_of_type(EvaluationLink):
        if len(link.outgoing) != 2:
            continue
        p, args = link.outgoing
        if p.key != pred.key or not isinstance(args, ListLink) or len(args.outgoing) != 2:
            continue
        a, b = args.outgoing
        out.append((a, b, link.tv))
    return out


def transitive_closure(atomspace: AtomSpace, predicate: str,
                       max_new: int = 200) -> List[EvaluationLink]:
    """Fuegt abgeleitete transitive Relationen hinzu und gibt sie zurueck."""
    pred = atomspace.node(PredicateNode, predicate)
    if pred is None:
        return []
    pairs = _pairs(atomspace, predicate)
    # Nachbarschaft A -> [(B, tv)]
    succ: dict = {}
    existing: Set[Tuple] = set()
    for a, b, tv in pairs:
        succ.setdefault(a.key, []).append((b, tv))
        existing.add((a.key, b.key))

    added: List[EvaluationLink] = []
    for a, b, tv_ab in pairs:
        for c, tv_bc in succ.get(b.key, []):
            if a.key == c.key or (a.key, c.key) in existing:
                continue
            conf = CHAIN_DISCOUNT * min(tv_ab.confidence, tv_bc.confidence)
            if conf < MIN_CONFIDENCE:
                continue
            strength = tv_ab.strength * tv_bc.strength
            link = EvaluationLink(
                PredicateNode(predicate),
                ListLink(a, c),
                tv=TruthValue(strength, conf),
            )
            stored = atomspace.add(link)
            added.append(stored)
            existing.add((a.key, c.key))
            if len(added) >= max_new:
                return added
    return added


def close_all(atomspace: AtomSpace, predicates=TRANSITIVE_RELATIONS) -> List[EvaluationLink]:
    added: List[EvaluationLink] = []
    for predicate in predicates:
        added.extend(transitive_closure(atomspace, predicate))
    return added
