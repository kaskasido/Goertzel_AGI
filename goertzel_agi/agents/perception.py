"""Wahrnehmungs-Agent: Sprache -> Atome.

Goertzels Hybrid-These (u.a. "Generative AI vs. AGI", arXiv 2309.10371):
LLMs sind hervorragende Wahrnehmungs-/Sprachorgane, aber keine Denker.
Im Hyperon-Design liefern LLMs Kandidaten-Strukturen, die ins Atomspace
einfliessen, wo PLN & Co. symbolisch und probabilistisch weiterarbeiten.

Dieser Agent kapselt genau diese Grenze:
  - LanguageModel: Protokoll fuer beliebige LLM-Backends
    (z.B. ClaudeLanguageModel in llm_perception.py).
  - RuleBasedParser: deterministischer Fallback ohne Netz/Abhaengigkeiten
    fuer einfache deutsche/englische Aussagen, inkl. Mehrwort-Begriffen
    ("Anna Berg ist ein Mensch") und Verbmustern ("X hat/kann/mag Y").
Eingehende Aussagen werden mit moderater Konfidenz (<1.0) angelegt — Wahr-
nehmung kann irren; PLN-Revision korrigiert bei mehrfacher Evidenz.
"""

from __future__ import annotations

import re
from typing import List, Optional, Protocol, Tuple

from ..core.atom import ConceptNode, EvaluationLink, InheritanceLink, ListLink, PredicateNode
from ..core.truthvalue import TruthValue
from .base import CycleReport, MindAgent

PERCEPT_TV = TruthValue(0.9, 0.7)  # wahrgenommen != bewiesen


def normalize_concept(phrase: str) -> str:
    """Mehrwort-Begriffe zu Atomnamen: 'Anna Berg' -> 'anna_berg'."""
    return re.sub(r"\s+", "_", phrase.strip().lower())


class LanguageModel(Protocol):
    """Minimales LLM-Protokoll. Implementierungen: Claude API, lokale Modelle...

    extract_triples() soll pro Eingabesatz Tripel (subjekt, relation, objekt)
    liefern; Relation "isa" wird zu InheritanceLink, alles andere zu
    EvaluationLink. Namen sollen bereits normalisiert sein (lowercase, _).
    """

    def extract_triples(self, text: str) -> List[Tuple[str, str, str]]: ...


class RuleBasedParser:
    """Abhaengigkeitsfreier Fallback-Parser fuer einfache Aussagesaetze.

    Subjekt/Objekt duerfen aus mehreren Woertern bestehen; Artikel werden
    entfernt. Reihenfolge der Muster ist signifikant (spezifisch -> generisch).
    """

    _ART = r"(?:der|die|das|ein|eine|einen|einem|einer|a|an|the)\s+"

    PATTERNS: List[Tuple[re.Pattern, str]] = [
        # "Anna Berg ist ein Mensch" / "Ein Hund ist ein Tier"
        (re.compile(rf"^(?:{_ART})?(.+?)\s+ist\s+(?:ein|eine)\s+(.+)$", re.I), "isa"),
        # "A border collie is a dog"
        (re.compile(rf"^(?:{_ART})?(.+?)\s+is\s+(?:a|an)\s+(.+)$", re.I), "isa"),
        # "Hunde sind Tiere" (vereinfachter Plural)
        (re.compile(rf"^(?:{_ART})?(.+?)\s+sind\s+(.+)$", re.I), "isa"),
        # "X hat (ein/eine/einen) Y"
        (re.compile(rf"^(?:{_ART})?(.+?)\s+hat\s+(?:{_ART})?(.+)$", re.I), "hat"),
        # "X kann Y"
        (re.compile(rf"^(?:{_ART})?(.+?)\s+kann\s+(.+)$", re.I), "kann"),
        # haeufige + fachliche Verben (Sachrelationen). Unterstrich-Verben wie
        # "fuehrt_zu"/"ist_teil_von" erlaubt der Domain-Wortschatz unten ebenso.
        (re.compile(
            rf"^(?:{_ART})?(.+?)\s+"
            r"(verursacht|fuehrt_zu|ist_teil_von|gehoert_zu|zeigt|hat_symptom|"
            r"behandelt_mit|behandelt|wird_erkannt_durch|erkennt|aehnelt|"
            r"betrifft|liegt_in|entsteht_in|deutet_auf|produziert|aktiviert|"
            r"misst|uebersieht|uebertrifft|entfernt|reduziert|foerdert|lindert|"
            r"bekaempft|verhindert|sichert|liefert|ermoeglicht|analysiert|"
            r"unterstuetzt|erfasst|bezweifelt|fehlt|verknuepft|belegen|fordern|"
            r"praegte|erforscht|hat|"
            # Englische Relationen (zweisprachig)
            r"causes|leads_to|is_part_of|belongs_to|part_of|shows|has_symptom|"
            r"treats|treated_with|detects|resembles|affects|contains|produces|"
            r"requires|indicates|reduces|prevents|improves|measures|"
            r"mag|liebt|isst|frisst|jagt|kennt|braucht|sucht)"
            rf"\s+(?:{_ART})?(.+)$",
            re.I), None),
        # generischer Fallback: "<einwort-subjekt> <verb> <objekt...>"
        (re.compile(r"^(\S+)\s+(\S+)\s+(.+)$", re.I), None),
    ]

    def extract_triples(self, text: str) -> List[Tuple[str, str, str]]:
        triples: List[Tuple[str, str, str]] = []
        for sentence in re.split(r"[.;!?]\s*", text.strip()):
            sentence = sentence.strip()
            if not sentence:
                continue
            for pattern, relation in self.PATTERNS:
                m = pattern.match(sentence)
                if not m:
                    continue
                if relation is not None:
                    subj, obj = m.group(1), m.group(2)
                    rel = relation
                else:
                    subj, rel, obj = m.group(1), m.group(2), m.group(3)
                triples.append((
                    normalize_concept(subj),
                    normalize_concept(rel),
                    normalize_concept(obj),
                ))
                break
        return triples


class PerceptionAgent(MindAgent):
    """Nimmt Texte aus einer Eingabequeue, parst sie und schreibt Atome."""

    name = "PerceptionAgent"

    def __init__(self, atomspace, attention, model: Optional[LanguageModel] = None) -> None:
        super().__init__(atomspace, attention)
        self.model: LanguageModel = model or RuleBasedParser()
        self.inbox: List[str] = []

    def perceive(self, text: str) -> None:
        self.inbox.append(text)

    def step(self) -> CycleReport:
        report = CycleReport(self.name)
        while self.inbox:
            text = self.inbox.pop(0)
            triples = self.model.extract_triples(text)
            if not triples:
                report.note(f"unparsed: {text!r}")
                continue
            for subj, rel, obj in triples:
                atom = self._to_atom(subj, rel, obj)
                stored = self.atomspace.add(atom)
                # Neue Wahrnehmung ist per Definition aktuell relevant
                self.attention.stimulate(stored, 20.0)
                for part in stored.outgoing:
                    self.attention.stimulate(part, 10.0)
                report.note(f"perceived: {stored!r}")
        return report

    def _to_atom(self, subj: str, rel: str, obj: str):
        if rel == "isa":
            return InheritanceLink(ConceptNode(subj), ConceptNode(obj), tv=PERCEPT_TV)
        return EvaluationLink(
            PredicateNode(rel),
            ListLink(ConceptNode(subj), ConceptNode(obj)),
            tv=PERCEPT_TV,
        )
