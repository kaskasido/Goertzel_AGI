"""Dokumente zu lernbarem Text. Stdlib fuer .txt/.md/.nico; PDF/DOCX nur,
wenn optionale Pakete installiert sind (pypdf bzw. python-docx).

Reiner Klartext-Extraktor. Das Zerlegen in kurze, gepruefte Saetze (fuer
PDFs/DOCX sinnvoll) ist Aufgabe des optionalen Lektions-Generators mit Claude
— hier wird Text nur bereitgestellt, nicht erfunden.
"""

from __future__ import annotations

from pathlib import Path

TEXT_SUFFIXES = {".nico", ".txt", ".md"}


def extract_text(path) -> str:
    """Liefert den Rohtext einer Datei (leer, wenn nicht unterstuetzt)."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        return _pdf_text(path)
    if suffix in (".docx",):
        return _docx_text(path)
    return ""


def _pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        return ""
    try:
        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return ""


def _docx_text(path: Path) -> str:
    try:
        import docx  # type: ignore  (python-docx)
    except ImportError:
        return ""
    try:
        document = docx.Document(str(path))
        return "\n".join(p.text for p in document.paragraphs)
    except Exception:
        return ""
