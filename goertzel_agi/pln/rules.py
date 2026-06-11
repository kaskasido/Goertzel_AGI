"""PLN-Inferenzregeln mit den Originalformeln aus dem PLN-Buch (2008).

Notation: sAB = strength von (Inheritance A B), sA = strength von A (Term-
Wahrscheinlichkeit). Die Formeln sind die "independence-based" Heuristiken
der PLN-Termlogik; Konfidenz wird konservativ per Diskontierung propagiert.
"""

from __future__ import annotations

from ..core.truthvalue import TruthValue

# Konfidenz-Diskontierung pro Inferenzschritt: Schlussfolgerungen sind nie
# sicherer als ihre Praemissen, und mehrstufige Ketten verlieren Vertrauen.
RULE_DISCOUNT = 0.9


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def deduction(tv_ab: TruthValue, tv_bc: TruthValue,
              tv_a: TruthValue, tv_b: TruthValue, tv_c: TruthValue) -> TruthValue:
    """Deduktion:  (A->B), (B->C)  =>  (A->C).

    PLN-Formel: sAC = sAB*sBC + (1-sAB)*(sC - sB*sBC)/(1-sB)
    """
    s_ab, s_bc = tv_ab.strength, tv_bc.strength
    s_b, s_c = tv_b.strength, tv_c.strength
    if s_b >= 1.0:
        s_ac = s_bc  # B ist universell -> A->C folgt B->C
    else:
        s_ac = s_ab * s_bc + (1.0 - s_ab) * (s_c - s_b * s_bc) / (1.0 - s_b)
    c = RULE_DISCOUNT * min(tv_ab.confidence, tv_bc.confidence)
    return TruthValue(_clamp(s_ac), _clamp(c))


def inversion(tv_ab: TruthValue, tv_a: TruthValue, tv_b: TruthValue) -> TruthValue:
    """Bayes-Inversion:  (A->B)  =>  (B->A),  sBA = sAB * sA / sB."""
    if tv_b.strength <= 0.0:
        return TruthValue(0.5, 0.0)
    s_ba = tv_ab.strength * tv_a.strength / tv_b.strength
    c = RULE_DISCOUNT * min(tv_ab.confidence, tv_a.confidence, tv_b.confidence)
    return TruthValue(_clamp(s_ba), _clamp(c))


def induction(tv_ab: TruthValue, tv_ac: TruthValue,
              tv_a: TruthValue, tv_b: TruthValue, tv_c: TruthValue) -> TruthValue:
    """Induktion:  (A->B), (A->C)  =>  (B->C).

    Realisiert als Inversion(A->B) gefolgt von Deduktion(B->A, A->C).
    """
    tv_ba = inversion(tv_ab, tv_a, tv_b)
    return deduction(tv_ba, tv_ac, tv_b, tv_a, tv_c)


def abduction(tv_ac: TruthValue, tv_bc: TruthValue,
              tv_a: TruthValue, tv_b: TruthValue, tv_c: TruthValue) -> TruthValue:
    """Abduktion:  (A->C), (B->C)  =>  (A->B).

    Realisiert als Deduktion(A->C, Inversion(B->C)).
    """
    tv_cb = inversion(tv_bc, tv_b, tv_c)
    return deduction(tv_ac, tv_cb, tv_a, tv_c, tv_b)


def modus_ponens(tv_ab: TruthValue, tv_a: TruthValue) -> TruthValue:
    """Modus Ponens: (A->B), A => B.  sB ~ sA*sAB + 0.5*(1-sA) (unbekannter Rest)."""
    s = tv_a.strength * tv_ab.strength + 0.5 * (1.0 - tv_a.strength)
    c = RULE_DISCOUNT * min(tv_ab.confidence, tv_a.confidence)
    return TruthValue(_clamp(s), _clamp(c))


def conjunction(tv_a: TruthValue, tv_b: TruthValue) -> TruthValue:
    """UND unter Unabhaengigkeitsannahme: s = sA*sB."""
    return TruthValue(
        _clamp(tv_a.strength * tv_b.strength),
        min(tv_a.confidence, tv_b.confidence),
    )


def disjunction(tv_a: TruthValue, tv_b: TruthValue) -> TruthValue:
    """ODER: s = sA + sB - sA*sB."""
    s = tv_a.strength + tv_b.strength - tv_a.strength * tv_b.strength
    return TruthValue(_clamp(s), min(tv_a.confidence, tv_b.confidence))


def negation(tv_a: TruthValue) -> TruthValue:
    return TruthValue(1.0 - tv_a.strength, tv_a.confidence)


def similarity_from_inheritance(tv_ab: TruthValue, tv_ba: TruthValue) -> TruthValue:
    """Aehnlichkeit aus beidseitiger Vererbung: 1/sim = 1/sAB + 1/sBA - 1."""
    s_ab, s_ba = tv_ab.strength, tv_ba.strength
    if s_ab <= 0 or s_ba <= 0:
        return TruthValue(0.0, min(tv_ab.confidence, tv_ba.confidence))
    sim = 1.0 / (1.0 / s_ab + 1.0 / s_ba - 1.0)
    return TruthValue(_clamp(sim), RULE_DISCOUNT * min(tv_ab.confidence, tv_ba.confidence))
