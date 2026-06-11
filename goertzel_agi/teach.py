"""Headless-Lernen: Lektionsdateien in einen persistenten Atomspace einspeisen.

Fuer "Tag und Nacht lernen" ohne Browser. Laedt den gespeicherten Wissens-
stand, lehrt die angegebenen Dateien/Verzeichnisse, denkt ein paar Zyklen
darueber nach und speichert wieder.

Beispiele:
    # einmalig die ganze Demo-Wissensbasis einspeisen
    python -m goertzel_agi.teach knowledge/demo

    # eine einzelne neue Lektion nachschieben
    python -m goertzel_agi.teach knowledge/demo/01_taxonomy.nico

    # alle 10 Minuten dieselbe Datei nachlernen (Dauerbetrieb), Windows:
    #   :loop & python -m goertzel_agi.teach lektion.nico & timeout /t 600 & goto loop

Mit --claude wird (sofern ANTHROPIC_API_KEY gesetzt und 'anthropic'
installiert ist) Claude als Wahrnehmung genutzt, sonst der Regel-Parser.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .agents.orchestrator import CognitiveKernel

DEFAULT_STORE = "data/atomspace.json"


def build_kernel(use_claude: bool) -> CognitiveKernel:
    language_model = None
    if use_claude and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from .agents.llm_perception import ClaudeLanguageModel

            language_model = ClaudeLanguageModel()
        except RuntimeError:
            language_model = None
    return CognitiveKernel(language_model=language_model)


def main() -> None:
    parser = argparse.ArgumentParser(description="Goertzel-AGI: Lektionen lehren")
    parser.add_argument("paths", nargs="+", help="Lektionsdateien oder -ordner (.nico/.txt)")
    parser.add_argument("--store", default=DEFAULT_STORE, help="Wissensdatei (JSON)")
    parser.add_argument("--cycles", type=int, default=3, help="Denk-Zyklen je Lauf")
    parser.add_argument("--claude", action="store_true", help="Claude als Wahrnehmung")
    args = parser.parse_args()

    kernel = build_kernel(args.claude)
    kernel.load(args.store)
    before = len(kernel.atomspace)

    taught = 0
    for path in args.paths:
        taught += kernel.teach_path(path, cycles=args.cycles)

    kernel.run(cycles=args.cycles)  # noch etwas nachdenken
    kernel.save(args.store)
    after = len(kernel.atomspace)

    print(f"Gelehrt: {taught} Saetze aus {len(args.paths)} Pfad(en).")
    print(f"Atomspace: {before} -> {after} Atome (gespeichert in {args.store}).")


if __name__ == "__main__":
    main()
