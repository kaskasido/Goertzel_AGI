"""Basisklasse fuer kognitive Agenten (OpenCog: "MindAgents").

In CogPrime/Hyperon ist Kognition keine Pipeline, sondern eine Menge
nebenlaeufiger Prozesse, die zyklisch auf dem gemeinsamen Atomspace arbeiten.
Jeder Agent implementiert step() und liest/schreibt Atome; Kommunikation
zwischen Agenten geschieht NUR ueber den Atomspace (Blackboard-Prinzip).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..core.atomspace import AtomSpace
from ..ecan.attention import AttentionBank


@dataclass
class CycleReport:
    """Was ein Agent in einem Zyklus getan hat (fuer Introspektion/Logging)."""

    agent: str
    actions: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)

    def note(self, message: str) -> None:
        self.actions.append(message)


class MindAgent(ABC):
    """Ein kognitiver Prozess mit Zugriff auf Atomspace und AttentionBank."""

    name: str = "MindAgent"

    def __init__(self, atomspace: AtomSpace, attention: AttentionBank) -> None:
        self.atomspace = atomspace
        self.attention = attention

    @abstractmethod
    def step(self) -> CycleReport:
        """Fuehrt einen kognitiven Zyklus aus und berichtet darueber."""
