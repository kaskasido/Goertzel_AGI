"""End-to-End-Demo des kognitiven Zyklus.

Zeigt das Zusammenspiel aller Subsysteme an einem Mini-Szenario:
  1. Wahrnehmung: einfache Saetze werden zu Atomen
  2. PLN: leitet neues Wissen ab (Sokrates -> sterblich)
  3. ECAN: haelt das Relevante im Attentional Focus
  4. MOSES: lernt aus Beispielen ein Konzept ("gefaehrlich")
  5. Ziele: ein Wissensdurst-Demand lenkt Aufmerksamkeit
  6. Export des Ergebnisses als MeTTa-Code (fuer echtes Hyperon)

Ausfuehren:  python -m examples.demo_cognitive_cycle  (vom Repo-Root)
"""

from goertzel_agi import CognitiveKernel, ConceptNode, InheritanceLink
from goertzel_agi.agents.goals import Demand
from goertzel_agi.bridge.metta_bridge import export_metta


def main() -> None:
    kernel = CognitiveKernel(seed=42)

    # --- 1. Motivation: ein Demand nach Wissen ueber "tier" ------------------
    demand = kernel.goals.add_demand(Demand("wissensdurst", level=0.2))
    demand.related_atoms.append(kernel.atomspace.add(ConceptNode("tier")))

    # --- 2. Wahrnehmung: Saetze ins System geben ------------------------------
    for satz in [
        "Sokrates ist ein mensch",
        "Ein mensch ist ein lebewesen",
        "Ein lebewesen ist ein sterbliches",
        "Ein hund ist ein tier",
        "Eine katze ist ein tier",
        "Ein tier ist ein lebewesen",
    ]:
        kernel.tell(satz)

    # --- 3. MOSES-Trainingsdaten: was ist "gefaehrlich"? ----------------------
    beispiele = [
        ({"hat_zaehne": True, "ist_gross": True, "ist_zahm": False}, True),
        ({"hat_zaehne": True, "ist_gross": False, "ist_zahm": False}, True),
        ({"hat_zaehne": True, "ist_gross": True, "ist_zahm": True}, False),
        ({"hat_zaehne": False, "ist_gross": True, "ist_zahm": False}, False),
        ({"hat_zaehne": False, "ist_gross": False, "ist_zahm": True}, False),
        ({"hat_zaehne": True, "ist_gross": False, "ist_zahm": True}, False),
    ]
    for features, label in beispiele:
        kernel.learning.add_example("gefaehrlich", features, label)

    # --- 4. Kognitive Zyklen laufen lassen ------------------------------------
    kernel.run(cycles=4, verbose=True)

    # --- 5. Gezielte Frage (Backward Chaining): Ist Sokrates sterblich? -------
    frage = InheritanceLink(ConceptNode("sokrates"), ConceptNode("sterbliches"))
    antwort = kernel.ask(frage)
    print("\n=== Frage: Ist Sokrates sterblich? ===")
    for step in antwort.trace:
        print(f"  {step}")
    print(f"  Antwort-TV: {antwort.tv}")

    # --- 6. Attentional Focus + MeTTa-Export ----------------------------------
    print()
    print(kernel.focus_snapshot())
    print("\n=== MeTTa-Export (Auszug) ===")
    metta = export_metta(kernel.atomspace, min_confidence=0.3)
    print("\n".join(metta.splitlines()[:20]))


if __name__ == "__main__":
    main()
