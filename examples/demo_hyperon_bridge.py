"""Anbindung ans echte OpenCog Hyperon (MeTTa).

Voraussetzung:  pip install hyperon     (Python 3.8-3.12!)
Ausfuehren:     python -m examples.demo_hyperon_bridge

Was passiert:
  1. Unser CognitiveKernel lernt ein paar Fakten und leitet per PLN neue ab.
  2. Der komplette Wissensbestand wird als MeTTa exportiert.
  3. Ist das hyperon-Paket installiert, laedt MettaBridge das Wissen in den
     ECHTEN MeTTa-Interpreter und stellt dort Pattern-Matching-Anfragen —
     dieselben Daten, Goertzels Original-Engine.
  4. Ohne hyperon-Paket wird der MeTTa-Export gedruckt (laeuft auch im
     Browser-Playground auf https://metta-lang.dev).
"""

from goertzel_agi import CognitiveKernel
from goertzel_agi.bridge.metta_bridge import HYPERON_AVAILABLE, MettaBridge, export_metta


def main() -> None:
    kernel = CognitiveKernel()
    kernel.tell(
        "Sokrates ist ein mensch. Ein mensch ist ein lebewesen. "
        "Ein hund ist ein lebewesen. Ein lebewesen ist ein sterbliches."
    )
    kernel.run(cycles=2)

    metta_code = export_metta(kernel.atomspace, min_confidence=0.3)
    print("=== MeTTa-Export unseres Atomspace ===")
    print(metta_code)

    if not HYPERON_AVAILABLE:
        print("\nHinweis: 'pip install hyperon' (Python 3.8-3.12), dann laedt")
        print("dieses Skript das Wissen in den echten MeTTa-Interpreter.")
        print("Alternativ: Export oben in den Playground auf metta-lang.dev kopieren")
        print('und dort anfragen:  !(match &self (Inheritance $x sterbliches) $x)')
        return

    print("\n=== Anfragen im echten Hyperon/MeTTa ===")
    bridge = MettaBridge()
    bridge.load_atomspace(kernel.atomspace, min_confidence=0.3)

    queries = [
        ("Wer ist ein lebewesen?",
         "!(match &self (Inheritance $x lebewesen) $x)"),
        ("Wer ist sterblich (inkl. PLN-Schluesse)?",
         "!(match &self (Inheritance $x sterbliches) $x)"),
        ("TruthValue von (Inheritance sokrates sterbliches)?",
         "!(match &self (= (tv (Inheritance sokrates sterbliches)) $tv) $tv)"),
    ]
    for question, query in queries:
        print(f"\n{question}\n  {query}")
        for result in bridge.run(query):
            print(f"  => {result}")


if __name__ == "__main__":
    main()
