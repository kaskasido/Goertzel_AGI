"""Bruecke zum offiziellen OpenCog Hyperon (MeTTa).

Wenn das Paket `hyperon` installiert ist (pip install hyperon), kann Wissen
aus unserem Atomspace als MeTTa-Ausdruecke exportiert und im echten
Hyperon-Interpreter weiterverarbeitet werden — und umgekehrt. Ohne das Paket
liefert export_metta() trotzdem validen MeTTa-Quelltext (fuer metta-lang.dev
oder den MeTTa-CLI-Interpreter).

MeTTa-Konventionen hier:
  (: Hund Konzept)                         ; Typdeklaration (optional)
  (Inheritance Hund Tier)                  ; Fakt
  (stv 0.9 0.7)                            ; TruthValue als Metadaten-Ausdruck
Wir exportieren Fakten als (= (tv <fakt>) (stv s c)) plus den Fakt selbst,
sodass MeTTa-Programme die TVs per Pattern Matching abfragen koennen.
"""

from __future__ import annotations

from typing import List, Optional

from ..core.atom import Atom, Link, Node
from ..core.atomspace import AtomSpace

try:  # optionale Abhaengigkeit
    from hyperon import MeTTa  # type: ignore

    HYPERON_AVAILABLE = True
except ImportError:
    MeTTa = None  # type: ignore
    HYPERON_AVAILABLE = False


def atom_to_metta(atom: Atom) -> str:
    """Uebersetzt ein Atom in einen MeTTa-S-Ausdruck."""
    if isinstance(atom, Node):
        # MeTTa-Symbole: Leerzeichen vermeiden
        return atom.name.replace(" ", "_")
    assert isinstance(atom, Link)
    type_name = atom.atom_type.removesuffix("Link")
    inner = " ".join(atom_to_metta(o) for o in atom.outgoing)
    return f"({type_name} {inner})"


def export_metta(atomspace: AtomSpace, min_confidence: float = 0.0) -> str:
    """Serialisiert den Atomspace als MeTTa-Programmtext."""
    lines: List[str] = ["; exported from goertzel_agi AtomSpace"]
    for atom in atomspace:
        if not isinstance(atom, Link):
            continue
        if atom.tv.confidence < min_confidence:
            continue
        expr = atom_to_metta(atom)
        lines.append(expr)
        lines.append(f"(= (tv {expr}) (stv {atom.tv.strength:.4f} {atom.tv.confidence:.4f}))")
    return "\n".join(lines)


class MettaBridge:
    """Laedt unseren Wissensbestand in einen echten MeTTa-Interpreter."""

    def __init__(self) -> None:
        if not HYPERON_AVAILABLE:
            raise RuntimeError(
                "Paket 'hyperon' fehlt. Installation: pip install hyperon"
            )
        self.metta = MeTTa()

    def load_atomspace(self, atomspace: AtomSpace, min_confidence: float = 0.0) -> None:
        self.metta.run(export_metta(atomspace, min_confidence))

    def run(self, program: str) -> list:
        """Fuehrt MeTTa-Code aus, z.B. '!(match &self (Inheritance $x Tier) $x)'."""
        return self.metta.run(program)
