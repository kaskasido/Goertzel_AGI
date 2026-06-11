"""PLN-Wahrheitswerte nach Goertzel et al., "Probabilistic Logic Networks" (2008).

Ein TruthValue besteht aus:
  - strength  s in [0,1]: geschaetzte Wahrscheinlichkeit der Aussage
  - confidence c in [0,1]: Vertrauen in diese Schaetzung, abgeleitet aus der
    Evidenzmenge n ueber c = n / (n + k), wobei k der "personality parameter"
    (Lookahead) ist. PLN nennt das "simple truth values".
"""

from __future__ import annotations

from dataclasses import dataclass

# k im PLN-Buch: wie viel zukuenftige Evidenz relativ zur bisherigen gewichtet wird
DEFAULT_K = 1.0


@dataclass(frozen=True)
class TruthValue:
    strength: float = 1.0
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if not (0.0 <= self.strength <= 1.0):
            raise ValueError(f"strength must be in [0,1], got {self.strength}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be in [0,1], got {self.confidence}")

    # ---- Evidenz <-> Konfidenz -------------------------------------------
    @classmethod
    def from_evidence(cls, positive: float, total: float, k: float = DEFAULT_K) -> "TruthValue":
        """TV aus Zaehl-Evidenz: s = n+/n, c = n/(n+k)."""
        if total <= 0:
            return cls(0.5, 0.0)
        return cls(positive / total, total / (total + k))

    def to_count(self, k: float = DEFAULT_K) -> float:
        """Inverse von c = n/(n+k):  n = k*c/(1-c)."""
        if self.confidence >= 1.0:
            return float("inf")
        return k * self.confidence / (1.0 - self.confidence)

    # ---- Revision (Evidenz-Fusion), PLN-Revisionsregel --------------------
    def revise(self, other: "TruthValue", k: float = DEFAULT_K) -> "TruthValue":
        """Kombiniert zwei unabhaengige Evidenzquellen fuer dieselbe Aussage.

        Gewichtetes Mittel der Staerken nach Evidenzmenge; Konfidenzen addieren
        sich auf Ebene der Counts: n = n1 + n2.
        """
        n1, n2 = self.to_count(k), other.to_count(k)
        if n1 + n2 == 0:
            return TruthValue(0.5, 0.0)
        if n1 == float("inf") or n2 == float("inf"):
            # Volle Konfidenz dominiert
            return self if n1 == float("inf") else other
        s = (self.strength * n1 + other.strength * n2) / (n1 + n2)
        n = n1 + n2
        return TruthValue(s, n / (n + k))

    @property
    def count(self) -> float:
        return self.to_count()

    def __repr__(self) -> str:  # kompakte OpenCog-artige Notation
        return f"(stv {self.strength:.3f} {self.confidence:.3f})"


TRUE = TruthValue(1.0, 0.9)
FALSE = TruthValue(0.0, 0.9)
UNKNOWN = TruthValue(0.5, 0.0)
