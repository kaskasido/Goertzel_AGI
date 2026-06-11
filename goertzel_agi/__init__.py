"""goertzel_agi — Lehr-/Experimentier-Implementierung von Ben Goertzels
AGI-Architektur (CogPrime / OpenCog Hyperon Prinzipien) in reinem Python.

Bausteine:
  core   — Atomspace (Metagraph), Atome, PLN-TruthValues
  pln    — Probabilistic Logic Networks: Regeln + Forward/Backward Chainer
  ecan   — Economic Attention Networks: Aufmerksamkeitsoekonomie
  moses  — evolutionaeres Programmlernen (vereinfachtes MOSES)
  agents — MindAgents + CognitiveKernel (kognitiver Zyklus, OpenPsi-Ziele)
  bridge — Export nach / Integration mit echtem MeTTa (pip install hyperon)
"""

from .agents.orchestrator import CognitiveKernel
from .core.atom import (
    AndLink,
    ConceptNode,
    EvaluationLink,
    ImplicationLink,
    InheritanceLink,
    ListLink,
    MemberLink,
    NotLink,
    OrLink,
    PredicateNode,
    SimilarityLink,
    VariableNode,
)
from .core.atomspace import AtomSpace
from .core.truthvalue import TruthValue

__all__ = [
    "AtomSpace",
    "TruthValue",
    "CognitiveKernel",
    "ConceptNode",
    "PredicateNode",
    "VariableNode",
    "InheritanceLink",
    "SimilarityLink",
    "ImplicationLink",
    "EvaluationLink",
    "ListLink",
    "MemberLink",
    "AndLink",
    "OrLink",
    "NotLink",
]

__version__ = "0.1.0"
