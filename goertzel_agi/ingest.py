"""Headless-Ordner-Lernen: inbox/ verarbeiten, Wissen speichern.

Einmalig:
    python -m goertzel_agi.ingest

Dauerbetrieb (alle 5 Minuten den Posteingang leeren), Windows:
    :loop
    python -m goertzel_agi.ingest
    timeout /t 300
    goto loop

Mit --claude wird (sofern ANTHROPIC_API_KEY gesetzt) Claude als Wahrnehmung
genutzt, sonst der Regel-Parser.
"""

from __future__ import annotations

import argparse
import os

from .agents.orchestrator import CognitiveKernel
from .connect.ingest import IngestEngine


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
    parser = argparse.ArgumentParser(description="Ordner-Lernen (Posteingang)")
    parser.add_argument("--inbox", default="inbox")
    parser.add_argument("--store", default="data/atomspace.json")
    parser.add_argument("--cycles", type=int, default=2)
    parser.add_argument("--claude", action="store_true")
    args = parser.parse_args()

    kernel = build_kernel(args.claude)
    kernel.load(args.store)
    before = len(kernel.atomspace)

    engine = IngestEngine(kernel, inbox=args.inbox, cycles=args.cycles)
    report = engine.process_folder()

    kernel.run(cycles=args.cycles)
    kernel.save(args.store)

    print(f"Verarbeitet: {len(report.files_done)} Datei(en), "
          f"{report.learned} Einheiten gelernt.")
    for note in report.notes:
        print(f"  {note}")
    if report.files_failed:
        print("Fehlgeschlagen (nach inbox/failed/ verschoben):")
        for name, err in report.files_failed:
            print(f"  {name}: {err}")
    print(f"Atomspace: {before} -> {len(kernel.atomspace)} Atome (in {args.store}).")


if __name__ == "__main__":
    main()
