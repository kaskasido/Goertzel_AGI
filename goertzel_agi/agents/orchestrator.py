"""CognitiveKernel: der kognitive Zyklus nach CogPrime/Hyperon.

Orchestriert die MindAgents ueber dem gemeinsamen Atomspace. Reihenfolge je
Zyklus (an CogPrime angelehnt):

    1. PerceptionAgent  — neue Beobachtungen -> Atome (+ Stimulus)
    2. GoalAgent        — Urges -> Stimulation zielrelevanter Atome
    3. ReasoningAgent   — PLN-Inferenz, bevorzugt im Attentional Focus
    4. LearningAgent    — MOSES + Pattern Mining auf dem Wissensbestand
    5. AttentionBank    — Spreading, Rent, Forgetting (ECAN-Haushalt)

Wichtig (Goertzels Pointe): Die Intelligenz soll aus dem ZUSAMMENSPIEL
entstehen, nicht aus einem einzelnen Modul — jeder Prozess entschaerft die
kombinatorische Explosion der anderen (kognitive Synergie).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from ..core.atom import ConceptNode, EvaluationLink, ListLink, PredicateNode
from ..core.atomspace import AtomSpace
from ..core.persistence import load_atomspace, save_atomspace
from ..ecan.attention import AttentionBank
from .base import CycleReport, MindAgent
from .goals import GoalAgent
from .learning import LearningAgent
from .perception import LanguageModel, PerceptionAgent, normalize_concept
from .reasoning import ReasoningAgent


@dataclass
class CycleLog:
    cycle: int
    reports: List[CycleReport] = field(default_factory=list)

    def __str__(self) -> str:
        lines = [f"=== Cognitive Cycle {self.cycle} ==="]
        for r in self.reports:
            if not r.actions:
                continue
            lines.append(f"[{r.agent}]")
            lines.extend(f"  {a}" for a in r.actions)
        return "\n".join(lines)


class CognitiveKernel:
    def __init__(self, language_model: Optional[LanguageModel] = None,
                 focus_size: int = 20, seed: int | None = None,
                 self_update: bool = False, listen: bool = False) -> None:
        self.atomspace = AtomSpace()
        self.attention = AttentionBank(self.atomspace, focus_size=focus_size)
        self.perception = PerceptionAgent(self.atomspace, self.attention, language_model)
        self.goals = GoalAgent(self.atomspace, self.attention)
        self.reasoning = ReasoningAgent(self.atomspace, self.attention)
        self.learning = LearningAgent(self.atomspace, self.attention, seed=seed)
        self.agents: List[MindAgent] = [
            self.perception, self.goals, self.reasoning, self.learning,
        ]
        self.self_update = None
        self.listener = None
        if self_update:
            # Import hier, damit der Kern ohne das Modul lauffaehig bleibt
            from ..selfupdate.agent import SelfUpdateAgent

            self.self_update = SelfUpdateAgent(
                self.atomspace, self.attention, self.goals
            )
            self.agents.append(self.self_update)
        if listen:
            from ..selfupdate.listener import ListenerAgent

            self.listener = ListenerAgent(
                self.atomspace, self.attention, self.goals, self.perception
            )
            self.agents.append(self.listener)
        self.cycle_count = 0
        self.history: List[CycleLog] = []

    # ---- Aussenwelt-Schnittstellen -----------------------------------------
    def tell(self, text: str) -> None:
        """Natuerliche Sprache in die Wahrnehmungsqueue legen."""
        self.perception.perceive(text)

    def teach(self, lines, cycles: int = 1) -> int:
        """Eine Lektion einspeisen: viele Saetze auf einmal, dann verarbeiten.

        Akzeptiert eine Liste von Saetzen oder einen mehrzeiligen String.
        '#'-Kommentare und Leerzeilen werden ignoriert. Gibt die Zahl der
        aufgenommenen Saetze zurueck.
        """
        if isinstance(lines, str):
            lines = lines.splitlines()
        count = 0
        for raw in lines:
            sentence = raw.split("#", 1)[0].strip()
            if not sentence:
                continue
            self.perception.perceive(sentence)
            count += 1
        if count:
            self.run(cycles=cycles)
        return count

    def teach_file(self, path, cycles: int = 1) -> int:
        """Eine .nico/.alex/.txt-Lektionsdatei einspeisen."""
        text = Path(path).read_text(encoding="utf-8")
        return self.teach(text, cycles=cycles)

    def learn_triples(self, triples, cycles: int = 1) -> int:
        """Strukturierte Tripel (subj, relation, obj) direkt verankern.

        Umgeht den Satz-Parser — ideal fuer Tabellen/Datenbanken, deren
        Zellen schon sauber getrennt sind. relation == 'isa' wird zu
        InheritanceLink, alles andere zu EvaluationLink. Gibt die Zahl der
        aufgenommenen Tripel zurueck.
        """
        count = 0
        for subj, rel, obj in triples:
            if not (subj and rel and obj):
                continue
            atom = self.perception._to_atom(
                normalize_concept(str(subj)),
                normalize_concept(str(rel)),
                normalize_concept(str(obj)),
            )
            stored = self.atomspace.add(atom)
            self.attention.stimulate(stored, 12.0)
            count += 1
        if count and cycles:
            self.run(cycles=cycles)
        return count

    def learn_cases(self, concept: str, cases) -> int:
        """Fallbeispiele fuer MOSES sammeln: cases = [(features_dict, label_bool)].

        Aus genuegend Faellen lernt der LearningAgent eine lesbare Regel
        'learned:<concept>'. Gibt die Zahl der aufgenommenen Faelle zurueck.
        """
        count = 0
        for features, label in cases:
            self.learning.add_example(concept, features, bool(label))
            count += 1
        return count

    def teach_path(self, path, cycles: int = 1) -> int:
        """Datei oder ganzes Verzeichnis (rekursiv, *.nico/*.alex/*.txt) lehren."""
        p = Path(path)
        if p.is_dir():
            known = {".nico", ".alex", ".txt"}
            files = sorted(f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in known)
        else:
            files = [p]
        total = 0
        for f in files:
            total += self.teach_file(f, cycles=cycles)
        return total

    # ---- Persistenz (Tag-und-Nacht-Lernen) ---------------------------------
    def save(self, path) -> None:
        save_atomspace(self.atomspace, path)

    def load(self, path) -> None:
        load_atomspace(path, self.atomspace)

    def run(self, cycles: int = 1, verbose: bool = False) -> List[CycleLog]:
        logs: List[CycleLog] = []
        for _ in range(cycles):
            self.cycle_count += 1
            log = CycleLog(self.cycle_count)
            for agent in self.agents:
                log.reports.append(agent.step())
            self.attention.step()
            self.history.append(log)
            logs.append(log)
            if verbose:
                print(log)
        return logs

    def ask(self, goal, max_depth: int = 5):
        """Frage ans System: Backward Chaining mit Beweisspur."""
        return self.reasoning.query(goal, max_depth=max_depth)

    def ask_relation(self, predicate: str, subject: str) -> list:
        """Fachfrage 'Was steht in Relation <predicate> zu <subject>?'.

        z.B. ask_relation('causes', 'rain') -> alle B mit
        (causes rain B). Beruecksichtigt auch transitiv erschlossene
        Ketten. Liefert [(objekt_name, TruthValue), ...] nach Konfidenz.
        """
        pred = self.atomspace.node(PredicateNode, predicate)
        subj = self.atomspace.node(ConceptNode, normalize_concept(subject))
        if pred is None or subj is None:
            return []
        results = []
        for link in self.atomspace.atoms_of_type(EvaluationLink):
            if len(link.outgoing) != 2:
                continue
            p, args = link.outgoing
            if p.key != pred.key or not isinstance(args, ListLink):
                continue
            a, b = args.outgoing
            if a.key == subj.key:
                results.append((b.name, link.tv))
        results.sort(key=lambda t: t[1].confidence, reverse=True)
        return results

    # ---- Introspektion --------------------------------------------------------
    def focus_snapshot(self) -> str:
        lines = ["--- Attentional Focus ---"]
        for atom in self.attention.focus():
            lines.append(f"  sti={atom.av.sti:7.2f}  {atom!r}")
        return "\n".join(lines)
