"""Ordner-Lernen (der "Posteingang"): Dateien ablegen -> KI lernt sie -> weg.

Das ist die "Lernsoftware, die Tag und Nacht laeuft": Du legst Dateien in
inbox/, die Engine lernt sie und verschiebt sie nach processed/ (Fehler nach
failed/). Unterstuetzt:

  *.nico / *.txt / *.md   -> Saetze direkt lernen (Satz-Parser/Claude)
  *.csv                   -> Fakten ODER MOSES-Faelle, je nach Sidecar-Mapping
  *.pdf / *.docx          -> Klartext lernen (nur mit pypdf/python-docx)

CSV-Steuerung per gleichnamiger Sidecar-Datei <name>.csv.json:
  Fakten:  {"mode": "facts", "subject_col": "stoff",
            "relation": "verursacht", "object_col": "wirkung"}
  Faelle:  {"mode": "cases", "label_col": "diagnose",
            "positive_label": "flu", "concept": "flu_suspected"}
Ohne Sidecar wird eine CSV als Fakten interpretiert, sofern Spalten
subject/relation/object existieren — sonst nach failed/ verschoben.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from . import tabular
from .documents import extract_text

LEARNABLE = {".nico", ".txt", ".md", ".csv", ".pdf", ".docx"}


@dataclass
class IngestReport:
    learned: int = 0
    files_done: List[str] = field(default_factory=list)
    files_failed: List[tuple] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


class IngestEngine:
    def __init__(self, kernel, inbox="inbox", processed=None,
                 failed=None, cycles: int = 2) -> None:
        self.kernel = kernel
        self.inbox = Path(inbox)
        # processed/failed liegen standardmaessig IM Posteingang
        self.processed = Path(processed) if processed else self.inbox / "processed"
        self.failed = Path(failed) if failed else self.inbox / "failed"
        self.cycles = cycles

    def _candidate_files(self):
        skip = {self.processed.resolve(), self.failed.resolve()}
        return sorted(
            f for f in self.inbox.iterdir()
            if f.is_file() and f.suffix.lower() in LEARNABLE
            and not f.name.endswith(".csv.json")
            and f.parent.resolve() not in skip
        )

    def process_folder(self) -> IngestReport:
        report = IngestReport()
        self.inbox.mkdir(parents=True, exist_ok=True)
        for f in self._candidate_files():
            try:
                n = self._learn_file(f)
                report.learned += n
                report.files_done.append(f.name)
                report.notes.append(f"{f.name}: {n} Einheiten gelernt")
                self._move(f, self.processed)
            except Exception as exc:  # nie haengenbleiben — ab nach failed/
                report.files_failed.append((f.name, str(exc)))
                report.notes.append(f"{f.name}: FEHLER {exc}")
                self._move(f, self.failed)
        return report

    # ---- pro Datei ------------------------------------------------------------
    def _learn_file(self, path: Path) -> int:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            return self._learn_csv(path)
        if suffix in (".nico", ".txt", ".md"):
            return self.kernel.teach_file(path, cycles=self.cycles)
        if suffix in (".pdf", ".docx"):
            text = extract_text(path)
            if not text.strip():
                raise RuntimeError("kein Text extrahierbar (pypdf/python-docx fehlt?)")
            return self.kernel.teach(text, cycles=self.cycles)
        raise RuntimeError(f"nicht unterstuetzt: {suffix}")

    def _learn_csv(self, path: Path) -> int:
        sidecar = path.with_suffix(path.suffix + ".json")
        spec = {}
        if sidecar.exists():
            spec = json.loads(sidecar.read_text(encoding="utf-8"))
        mode = spec.get("mode", "facts")
        if mode == "cases":
            n = tabular.import_cases_csv(
                self.kernel, path,
                label_col=spec["label_col"],
                feature_cols=spec.get("feature_cols"),
                positive_label=spec.get("positive_label"),
                concept=spec.get("concept"),
            )
            self.kernel.run(cycles=self.cycles)  # MOSES laufen lassen
        else:
            mapping = {
                "subject_col": spec.get("subject_col", "subject"),
                "object_col": spec.get("object_col", "object"),
            }
            if "relation" in spec:
                mapping["relation"] = spec["relation"]
            else:
                mapping["relation_col"] = spec.get("relation_col", "relation")
            n = tabular.import_facts_csv(self.kernel, path, mapping, cycles=self.cycles)
        # Sidecar mit verschieben, damit inbox/ sauber bleibt
        if sidecar.exists():
            self._move(sidecar, self.processed)
        return n

    def _move(self, path: Path, target: Path) -> None:
        target.mkdir(parents=True, exist_ok=True)
        dest = target / path.name
        if dest.exists():
            dest.unlink()
        shutil.move(str(path), str(dest))
