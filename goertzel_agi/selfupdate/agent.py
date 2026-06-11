"""SelfUpdateAgent: haelt das Wissen ueber den Vordenker selbstorganisiert aktuell.

Selbstorganisation nach dem OpenPsi-Muster statt eines starren Cronjobs:
ein Demand "aktualitaet" verfaellt langsam; steigt der Urge ueber eine
Schwelle (und ist die Abkuehlzeit vorbei), fragt der Agent seine Quellen
(arXiv, Substack) nach Neuem ab. Erfolg saettigt den Demand, Misserfolg
(offline) laesst den Urge bestehen — das System "will" von sich aus wieder
nachschauen.

Neues Wissen wird dreifach verankert:
  1. Atome im Atomspace (EvaluationLink (publizierte goertzel <werk>)) +
     InheritanceLink <werk> -> publikation/essay, mit ECAN-Stimulus
  2. persistenter Zustand (JSON), damit nichts doppelt aufgenommen wird
  3. menschenlesbares Protokoll docs/research/auto-updates.md

Bewusste Grenze: Der Agent aktualisiert WISSEN, nicht seinen eigenen CODE.
Sichere Code-Selbstmodifikation braucht Zielsystem-Invarianten (Goertzels
"Metagoals"-Paper, arXiv:2412.16559) und bleibt eine dokumentierte
Ausbaustufe.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from ..core.atom import ConceptNode, EvaluationLink, InheritanceLink, ListLink, PredicateNode
from ..core.truthvalue import TruthValue
from ..agents.base import CycleReport, MindAgent
from ..agents.goals import Demand
from .sources import Finding, KnowledgeSource, default_sources

SOURCE_TV = TruthValue(0.95, 0.8)  # Primaerquelle des Vordenkers: hohe Konfidenz
URGE_THRESHOLD = 0.5
COOLDOWN_CYCLES = 50  # fruehestens alle N Zyklen wieder anfragen


def _slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return s[:60] or "unbenannt"


class SelfUpdateAgent(MindAgent):
    name = "SelfUpdateAgent"

    DEMAND_NAME = "aktualitaet"
    LOG_TITLE = "Automatische Vordenker-Updates"
    LOG_INTRO = ("Vom SelfUpdateAgent gefundene neue Veroeffentlichungen "
                 "von Ben Goertzel (arXiv, Substack).")

    def __init__(self, atomspace, attention, goal_agent,
                 sources: Optional[List[KnowledgeSource]] = None,
                 state_file: str | Path = "data/selfupdate_state.json",
                 log_file: str | Path = "docs/research/auto-updates.md",
                 enabled: bool = True) -> None:
        super().__init__(atomspace, attention)
        self.sources = sources if sources is not None else default_sources()
        self.state_file = Path(state_file)
        self.log_file = Path(log_file)
        self.enabled = enabled
        self.cycles_since_fetch = COOLDOWN_CYCLES  # erster Lauf darf sofort
        self.last_result: str = "noch kein Lauf"
        self.demand: Demand = goal_agent.add_demand(
            Demand(self.DEMAND_NAME, level=0.0, decay=0.01, weight=1.0,
                   protected=True)  # Kern-Antrieb: Metagoal-geschuetzt
        )
        self._known: set[str] = self._load_state()

    # ---- Persistenz -----------------------------------------------------------
    def _load_state(self) -> set[str]:
        try:
            return set(json.loads(self.state_file.read_text())["known_uids"])
        except (OSError, ValueError, KeyError):
            return set()

    def _save_state(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(
            {"known_uids": sorted(self._known),
             "updated": datetime.now(timezone.utc).isoformat()},
            indent=2,
        ))

    def _append_log(self, findings: List[Finding]) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_file.exists():
            self.log_file.write_text(f"# {self.LOG_TITLE}\n\n{self.LOG_INTRO}\n")
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines = [f"\n## Lauf {stamp}\n"]
        for f in findings:
            lines.append(f"- **[{f.title}]({f.url})** ({f.source}, {f.published})")
            if f.summary:
                lines.append(f"  - {f.summary[:300]}")
        with self.log_file.open("a") as fh:
            fh.write("\n".join(lines) + "\n")

    # ---- Wissen verankern -------------------------------------------------------
    def _ingest(self, finding: Finding) -> None:
        work = ConceptNode(f"werk:{_slug(finding.title)}")
        kind = "publikation" if finding.source == "arxiv" else "essay"
        published = self.atomspace.add(EvaluationLink(
            PredicateNode("publizierte"),
            ListLink(ConceptNode("goertzel"), work),
            tv=SOURCE_TV,
        ))
        is_kind = self.atomspace.add(
            InheritanceLink(work, ConceptNode(kind), tv=SOURCE_TV)
        )
        for atom in (published, is_kind):
            self.attention.stimulate(atom, 25.0)  # Neues vom Vordenker ist heiss
        stored_work = self.atomspace.add(work)
        stored_work.av.vlti = True  # Vordenker-Wissen nie vergessen

    # ---- Kognitiver Zyklus --------------------------------------------------------
    def step(self) -> CycleReport:
        report = CycleReport(self.name)
        self.cycles_since_fetch += 1
        if not self.enabled:
            report.data["status"] = "deaktiviert"
            return report
        if self.demand.urge < URGE_THRESHOLD or self.cycles_since_fetch < COOLDOWN_CYCLES:
            report.data["status"] = (
                f"wartet (urge={self.demand.urge:.2f}, "
                f"cooldown={max(0, COOLDOWN_CYCLES - self.cycles_since_fetch)})"
            )
            return report
        self.check_now(report)
        return report

    def check_now(self, report: Optional[CycleReport] = None) -> CycleReport:
        """Sofortige Quellenabfrage (auch manuell aus der UI ausloesbar)."""
        report = report or CycleReport(self.name)
        self.cycles_since_fetch = 0
        new_findings: List[Finding] = []
        reached_any = False
        for source in self.sources:
            findings = source.fetch()
            if findings:
                reached_any = True
            for f in findings:
                if f.uid and f.uid not in self._known:
                    self._known.add(f.uid)
                    new_findings.append(f)
        if not reached_any:
            self.last_result = "Quellen nicht erreichbar (offline?) — Urge bleibt"
            report.note(self.last_result)
            return report
        # Erfolg: Demand saettigen, auch wenn nichts Neues kam
        self.demand.satisfy(1.0)
        if new_findings:
            for f in new_findings:
                self._ingest(f)
                report.note(f"neu vom Vordenker [{f.source}]: {f.title}")
            self._save_state()
            self._append_log(new_findings)
            self.last_result = f"{len(new_findings)} neue Werke aufgenommen"
        else:
            self._save_state()
            self.last_result = "Quellen geprueft — nichts Neues"
            report.note(self.last_result)
        report.data["new"] = len(new_findings)
        return report
