"""Tabellen- und Datenbank-Konnektor: CSV/SQLite -> Wissen oder MOSES-Faelle.

Zwei Modi:
  1. FAKTEN: jede Zeile wird zu einem Tripel (Subjekt, Relation, Objekt).
     Eine Mapping-Beschreibung sagt, welche Spalten das sind.
  2. FAELLE: jede Zeile ist ein Fall mit Merkmals-Spalten (ja/nein) und einer
     Diagnose-/Label-Spalte. Diese fuettern MOSES, das daraus eine lesbare
     Regel lernt -> der direkte Weg fuer anonymisierte Faelle.

Nur Python-Stdlib (csv, sqlite3) — keine Zusatzpakete noetig.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# Werte, die als "wahr" gelten (Fall-Merkmale). Robust gegen Sprache/Format.
TRUE_TOKENS = {"ja", "j", "yes", "y", "true", "wahr", "1", "x", "positiv", "+"}
FALSE_TOKENS = {"nein", "n", "no", "false", "falsch", "0", "", "negativ", "-"}


def bool_of(value) -> bool:
    return str(value).strip().lower() in TRUE_TOKENS


# ---- Modus 1: Fakten ---------------------------------------------------------
def _rows_to_triples(rows: Sequence[dict], mapping: dict) -> List[Tuple[str, str, str]]:
    subj_col = mapping["subject_col"]
    obj_col = mapping["object_col"]
    fixed = mapping.get("relation")
    rel_col = mapping.get("relation_col")
    triples = []
    for row in rows:
        subj = row.get(subj_col, "")
        obj = row.get(obj_col, "")
        rel = row.get(rel_col, "") if rel_col else fixed
        if subj and obj and rel:
            triples.append((subj, rel, obj))
    return triples


def import_facts_csv(kernel, path, mapping: dict, cycles: int = 1,
                     delimiter: Optional[str] = None) -> int:
    """CSV als Fakten lernen. mapping = {subject_col, object_col,
    relation | relation_col}."""
    text = Path(path).read_text(encoding="utf-8-sig")
    if delimiter is None:
        delimiter = ";" if text[:2000].count(";") > text[:2000].count(",") else ","
    rows = list(csv.DictReader(text.splitlines(), delimiter=delimiter))
    return kernel.learn_triples(_rows_to_triples(rows, mapping), cycles=cycles)


def import_facts_sqlite(kernel, db_path, query: str, mapping: dict,
                        cycles: int = 1) -> int:
    """SQLite-Abfrage als Fakten lernen (Spaltennamen = mapping-Spalten)."""
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        rows = [dict(r) for r in con.execute(query).fetchall()]
    finally:
        con.close()
    return kernel.learn_triples(_rows_to_triples(rows, mapping), cycles=cycles)


# ---- Modus 2: Faelle fuer MOSES ----------------------------------------------
def _rows_to_cases(rows: Sequence[dict], label_col: str,
                   feature_cols: Optional[Sequence[str]],
                   positive_label) -> List[Tuple[Dict[str, bool], bool]]:
    if not rows:
        return []
    if feature_cols is None:
        feature_cols = [c for c in rows[0].keys() if c != label_col]
    pos = None if positive_label is None else str(positive_label).strip().lower()
    cases = []
    for row in rows:
        features = {c: bool_of(row.get(c, "")) for c in feature_cols}
        raw = str(row.get(label_col, "")).strip().lower()
        label = (raw == pos) if pos is not None else bool_of(raw)
        cases.append((features, label))
    return cases


def import_cases_csv(kernel, path, label_col: str,
                     feature_cols: Optional[Sequence[str]] = None,
                     positive_label=None, concept: Optional[str] = None,
                     delimiter: Optional[str] = None) -> int:
    """Fall-Tabelle fuer MOSES laden. Eine Zeile = ein Fall:
    Merkmals-Spalten (ja/nein) + Label-Spalte (Diagnose).

    positive_label: welcher Label-Wert 'wahr' bedeutet (z.B. 'flu').
    Fehlt er, werden ja/nein-Tokens interpretiert.
    concept: Name der zu lernenden Regel (Default: label_col)."""
    text = Path(path).read_text(encoding="utf-8-sig")
    if delimiter is None:
        delimiter = ";" if text[:2000].count(";") > text[:2000].count(",") else ","
    rows = list(csv.DictReader(text.splitlines(), delimiter=delimiter))
    cases = _rows_to_cases(rows, label_col, feature_cols, positive_label)
    return kernel.learn_cases(concept or label_col, cases)
