"""Glossar & Abdeckungsbericht: was hat die KI gelernt, wo sind Luecken?

Der "Lueckenfinder" fuer den Aufbau eines Fachsystems. Laedt Lektionen
(oder den gespeicherten Atomspace), verdichtet ein paar Zyklen und schreibt
einen lesbaren Bericht:

  - wie viele Konzepte / Relationen das System kennt
  - die am staerksten vernetzten Begriffe (der Wissenskern)
  - schwach vernetzte Begriffe (Kandidaten fuer mehr Saetze)
  - moegliche Dubletten durch Beugung/Schreibweise (z.B. Dativ vs. Nominativ)

Beispiele:
    python -m goertzel_agi.glossary knowledge/demo
    python -m goertzel_agi.glossary --store data/atomspace.json -o GLOSSAR.md
"""

from __future__ import annotations

import argparse
import difflib
from collections import Counter
from pathlib import Path
from typing import List

from .agents.orchestrator import CognitiveKernel
from .core.atom import (
    ConceptNode,
    EvaluationLink,
    InheritanceLink,
    ListLink,
    PredicateNode,
)


def _degree(atomspace) -> Counter:
    deg: Counter = Counter()
    for link in atomspace.atoms_of_type(InheritanceLink) + atomspace.atoms_of_type(EvaluationLink):
        for a in link.outgoing:
            if isinstance(a, ConceptNode):
                deg[a.name] += 1
            elif isinstance(a, ListLink):
                for x in a.outgoing:
                    if isinstance(x, ConceptNode):
                        deg[x.name] += 1
    return deg


def _likely_duplicates(names: List[str], cutoff: float = 0.86) -> List[tuple]:
    """Findet aehnliche Begriffspaare (Tippfehler/Beugung)."""
    names = sorted(names)
    pairs = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if a[:4] != b[:4]:
                continue  # nur sinnvolle Kandidaten vergleichen
            if difflib.SequenceMatcher(None, a, b).ratio() >= cutoff:
                pairs.append((a, b))
    return pairs


def build_report(atomspace) -> str:
    concepts = [a.name for a in atomspace.atoms_of_type(ConceptNode)]
    preds = sorted(a.name for a in atomspace.atoms_of_type(PredicateNode))
    inh = atomspace.atoms_of_type(InheritanceLink)
    ev = atomspace.atoms_of_type(EvaluationLink)
    deg = _degree(atomspace)

    lines = ["# Glossar & Abdeckungsbericht", ""]
    lines += [
        f"- Konzepte: **{len(concepts)}**",
        f"- Taxonomie-Links (ist ein): **{len(inh)}**",
        f"- Relations-Links: **{len(ev)}**",
        f"- Relationen im Einsatz: {', '.join(preds)}",
        "",
        "## Wissenskern (am staerksten vernetzte Begriffe)",
        "",
    ]
    for name, d in deg.most_common(15):
        lines.append(f"- `{name}` — {d} Verbindungen")

    isolated = sorted(n for n in concepts if deg[n] <= 1)
    lines += ["", f"## Schwach vernetzt — Kandidaten fuer mehr Saetze ({len(isolated)})", ""]
    lines += [f"- `{n}`" for n in isolated]

    dups = _likely_duplicates(concepts)
    lines += ["", f"## Moegliche Dubletten (Beugung/Schreibweise) ({len(dups)})", ""]
    if dups:
        lines += [f"- `{a}` ~ `{b}`  → vereinheitlichen oder per `aehnelt` verknuepfen"
                  for a, b in dups]
    else:
        lines.append("- keine gefunden")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Glossar/Abdeckung der KI")
    parser.add_argument("paths", nargs="*", help="Lektionsordner/-dateien")
    parser.add_argument("--store", help="vorhandenen Atomspace laden (JSON)")
    parser.add_argument("--cycles", type=int, default=12, help="Verdichtungszyklen")
    parser.add_argument("-o", "--output", help="Bericht in Datei schreiben")
    args = parser.parse_args()

    kernel = CognitiveKernel()
    if args.store:
        kernel.load(args.store)
    for path in args.paths:
        kernel.teach_path(path, cycles=2)
    for _ in range(max(1, args.cycles // 3)):
        kernel.run(cycles=3)

    report = build_report(kernel.atomspace)
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Bericht geschrieben: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
