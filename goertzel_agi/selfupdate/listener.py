"""ListenerAgent ("Denker-Agent"): hoert Theoretikern zu und laesst das
System wachsen — auf zwei Ebenen:

  1. WISSEN: Jede neue Episode/jedes Paper wird als Atom verankert
     ((Evaluation veroeffentlichte (List denker:X werk:Y))), und der Text
     (Titel + Beschreibung) laeuft durch die Wahrnehmung (Claude oder
     Regel-Parser) — extrahierte Tripel wachsen in den Atomspace, wo PLN
     darueber schlussfolgert. Das ist Goertzels Antwort auf "eigene LLM":
     Wissen im Metagraphen wachsen lassen statt Gewichte zu trainieren.

  2. KORPUS: Jeder gehoerte Text wird zusaetzlich als JSONL in data/corpus/
     gesammelt. Das ist der Trainingsdatensatz, falls spaeter doch ein
     kleines offenes Modell nachtrainiert werden soll (LoRA-Finetuning) —
     der realistische Weg zu einer "eigenen LLM light".

Selbstorganisation wie beim SelfUpdateAgent: Demand "horizont" verfaellt,
der Urge loest das Zuhoeren aus. Quellen sind konfigurierbar
(data/denker_feeds.json), Standard: Lex Fridman, TED, David Deutsch.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from ..core.atom import ConceptNode, EvaluationLink, InheritanceLink, ListLink, PredicateNode
from ..core.truthvalue import TruthValue
from .agent import SOURCE_TV, SelfUpdateAgent, _slug
from .sources import Finding, KnowledgeSource
from .thinkers import load_thinker_sources

# Aus Beschreibungstexten extrahierte Aussagen: plausibel, wenig Evidenz —
# es ist Sekundaerwissen ueber das Gesagte, nicht das gepruefte Werk selbst.
HEARD_TV = TruthValue(0.8, 0.3)


class ListenerAgent(SelfUpdateAgent):
    name = "ListenerAgent"

    DEMAND_NAME = "horizont"
    LOG_TITLE = "Denker-Log: Gehoertes von Theoretikern"
    LOG_INTRO = ("Vom ListenerAgent aufgenommene Episoden/Talks/Papers "
                 "(Lex Fridman, TED, David Deutsch, eigene Feeds).")

    def __init__(self, atomspace, attention, goal_agent, perception,
                 sources: Optional[List[KnowledgeSource]] = None,
                 state_file: str | Path = "data/listener_state.json",
                 log_file: str | Path = "docs/research/denker-log.md",
                 corpus_dir: str | Path = "data/corpus",
                 enabled: bool = True) -> None:
        super().__init__(
            atomspace, attention, goal_agent,
            sources=sources if sources is not None else load_thinker_sources(),
            state_file=state_file, log_file=log_file, enabled=enabled,
        )
        self.perception = perception
        self.corpus_dir = Path(corpus_dir)
        self.corpus_added = 0

    # ---- Wachstum -------------------------------------------------------------
    def _ingest(self, finding: Finding) -> None:
        thinker = self.atomspace.add(ConceptNode(f"denker:{finding.source}"))
        thinker.av.vlti = True
        work = self.atomspace.add(ConceptNode(f"werk:{_slug(finding.title)}"))
        published = self.atomspace.add(EvaluationLink(
            PredicateNode("veroeffentlichte"),
            ListLink(thinker, work),
            tv=SOURCE_TV,
        ))
        self.attention.stimulate(published, 20.0)

        # Gehoertes durch die Wahrnehmung in Wissens-Tripel zerlegen
        text = f"{finding.title}. {finding.summary}".strip()
        for subj, rel, obj in self.perception.model.extract_triples(text):
            atom = self.perception._to_atom(subj, rel, obj)
            atom.tv = HEARD_TV
            stored = self.atomspace.add(atom)
            self.attention.stimulate(stored, 8.0)

        self._append_corpus(finding)

    def _append_corpus(self, finding: Finding) -> None:
        """Korpus fuer ein spaeteres Finetuning sammeln (JSONL pro Quelle)."""
        self.corpus_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "source": finding.source,
            "title": finding.title,
            "text": finding.summary,
            "url": finding.url,
            "published": finding.published,
        }
        with (self.corpus_dir / f"{finding.source}.jsonl").open("a") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.corpus_added += 1

    def corpus_size(self) -> int:
        """Anzahl gesammelter Korpus-Dokumente (Zeilen ueber alle Quellen)."""
        if not self.corpus_dir.exists():
            return 0
        total = 0
        for f in self.corpus_dir.glob("*.jsonl"):
            with f.open() as fh:
                total += sum(1 for _ in fh)
        return total
