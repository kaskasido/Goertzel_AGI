"""Persistenz des Atomspace: speichern und laden als JSON.

Voraussetzung dafuer, dass die KI "Tag und Nacht" lernen kann — ohne
Persistenz lebt der Wissens-Metagraph nur im Arbeitsspeicher und ist beim
Neustart weg. Hier wird der komplette Graph (Atome, TruthValues,
AttentionValues) serialisiert und wieder rekonstruiert.

Format: eine flache Liste von Atomen, topologisch geordnet (Kinder vor
Eltern), Links referenzieren ihre Kinder per Index. So bleibt der Metagraph
mit Links-auf-Links korrekt rekonstruierbar.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from . import atom as atom_module
from .atom import Atom, AttentionValue, Link, Node
from .atomspace import AtomSpace
from .truthvalue import TruthValue

# Registry: Klassenname -> Klasse (fuer die Rekonstruktion)
_ATOM_CLASSES = {
    name: cls
    for name, cls in vars(atom_module).items()
    if isinstance(cls, type) and issubclass(cls, Atom) and cls not in (Atom, Node, Link)
}


def _depth(atom: Atom, cache: Dict[tuple, int]) -> int:
    if atom.key in cache:
        return cache[atom.key]
    if isinstance(atom, Link) and atom.outgoing:
        d = 1 + max(_depth(o, cache) for o in atom.outgoing)
    else:
        d = 0
    cache[atom.key] = d
    return d


def to_dict(atomspace: AtomSpace) -> dict:
    cache: Dict[tuple, int] = {}
    atoms = sorted(atomspace, key=lambda a: (_depth(a, cache), repr(a.key)))
    index = {a.key: i for i, a in enumerate(atoms)}
    entries = []
    for a in atoms:
        entry = {
            "t": a.atom_type,
            "tv": [a.tv.strength, a.tv.confidence],
            "av": [a.av.sti, a.av.lti, a.av.vlti],
        }
        if isinstance(a, Node):
            entry["name"] = a.name
        else:
            entry["out"] = [index[o.key] for o in a.outgoing]
        entries.append(entry)
    return {"version": 1, "atoms": entries}


def from_dict(data: dict, atomspace: AtomSpace | None = None) -> AtomSpace:
    space = atomspace if atomspace is not None else AtomSpace()
    built: List[Atom] = []
    for entry in data.get("atoms", []):
        cls = _ATOM_CLASSES.get(entry["t"])
        if cls is None:
            built.append(None)  # unbekannter Typ -> Platzhalter
            continue
        tv = TruthValue(entry["tv"][0], entry["tv"][1])
        if "name" in entry:
            atom = cls(entry["name"], tv=tv)
        else:
            children = [built[i] for i in entry["out"]]
            if any(c is None for c in children):
                built.append(None)
                continue
            atom = cls(*children, tv=tv)
        stored = space.add(atom)
        stored.tv = tv  # exakt setzen (add() koennte revidieren)
        sti, lti, vlti = entry["av"]
        stored.av = AttentionValue(sti, lti, bool(vlti))
        built.append(stored)
    return space


def save_atomspace(atomspace: AtomSpace, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(to_dict(atomspace)))
    tmp.replace(path)  # atomares Schreiben: kein halb geschriebener Zustand


def load_atomspace(path: str | Path, atomspace: AtomSpace | None = None) -> AtomSpace:
    path = Path(path)
    if not path.exists():
        return atomspace if atomspace is not None else AtomSpace()
    try:
        data = json.loads(path.read_text())
    except ValueError:
        return atomspace if atomspace is not None else AtomSpace()
    return from_dict(data, atomspace)
