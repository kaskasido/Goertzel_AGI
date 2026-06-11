"""Claude als Wahrnehmungsorgan: beliebige Saetze -> Wissens-Tripel.

Setzt Goertzels "Neural Space"-Idee praktisch um: Das LLM ist ein
austauschbares Organ am Rand der Architektur. Es extrahiert nur
Kandidaten-Tripel; Schlussfolgern, Lernen und Vergessen bleiben beim
symbolisch-probabilistischen Kern (PLN/ECAN/MOSES) im Atomspace.

Benoetigt das offizielle SDK und einen API-Schluessel:
    pip install anthropic
    export ANTHROPIC_API_KEY=...   (Windows: setx ANTHROPIC_API_KEY ...)

Robustheit: Jeder Fehler (kein Netz, kein Schluessel, Ratenlimit) faellt
lautlos auf den RuleBasedParser zurueck — das System bleibt immer handlungs-
faehig, nur die Sprachabdeckung sinkt.
"""

from __future__ import annotations

import json
from typing import List, Optional, Tuple

from .perception import RuleBasedParser, normalize_concept

try:  # optionale Abhaengigkeit — Kern bleibt ohne SDK lauffaehig
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:  # pragma: no cover
    anthropic = None  # type: ignore
    ANTHROPIC_AVAILABLE = False

MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """Du extrahierst Wissens-Tripel aus Saetzen fuer einen \
Wissensgraphen (OpenCog-Stil). Regeln:
- Klassenzugehoerigkeit ("X ist ein Y", "Xe sind Ye") => relation "isa".
- Sonst ist die Relation das Verb im Infinitiv, klein geschrieben \
(z.B. "haben", "moegen", "kennen").
- subject und object sind kurze Nominalphrasen ohne Artikel, klein \
geschrieben, Leerzeichen durch Unterstriche ersetzt ("anna_berg").
- Zerlege zusammengesetzte Aussagen in mehrere Tripel.
- Extrahiere nur, was der Text tatsaechlich behauptet — nichts erfinden.
- Wenn nichts extrahierbar ist, gib eine leere Liste zurueck."""

TRIPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "triples": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "relation": {"type": "string"},
                    "object": {"type": "string"},
                },
                "required": ["subject", "relation", "object"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["triples"],
    "additionalProperties": False,
}


class ClaudeLanguageModel:
    """LanguageModel-Backend auf Basis der Claude API (Messages + Structured
    Output). Erfuellt das LanguageModel-Protokoll aus perception.py."""

    def __init__(self, model: str = MODEL, client=None,
                 fallback: Optional[RuleBasedParser] = None) -> None:
        if client is None:
            if not ANTHROPIC_AVAILABLE:
                raise RuntimeError(
                    "Paket 'anthropic' fehlt. Installation: pip install anthropic"
                )
            client = anthropic.Anthropic()  # liest ANTHROPIC_API_KEY aus der Umgebung
        self.client = client
        self.model = model
        self.fallback = fallback if fallback is not None else RuleBasedParser()
        self.last_status = "bereit"

    def extract_triples(self, text: str) -> List[Tuple[str, str, str]]:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": text}],
                output_config={
                    "format": {"type": "json_schema", "schema": TRIPLE_SCHEMA}
                },
            )
            payload = next(b.text for b in response.content if b.type == "text")
            data = json.loads(payload)
        except Exception as exc:  # Netz/Key/Limit -> regelbasierter Fallback
            self.last_status = f"Fallback ({type(exc).__name__})"
            return self.fallback.extract_triples(text)
        self.last_status = "ok"
        triples = [
            (
                normalize_concept(t["subject"]),
                normalize_concept(t["relation"]),
                normalize_concept(t["object"]),
            )
            for t in data.get("triples", [])
            if t.get("subject") and t.get("relation") and t.get("object")
        ]
        # Nichts erkannt? Der Regelparser versteht manche Kurzformen trotzdem.
        return triples or self.fallback.extract_triples(text)
