# Architektur: Agentenstruktur nach Ben Goertzel

Dieses Repo setzt Goertzels Kernideen (CogPrime → OpenCog Hyperon) als
lauffähige, abhängigkeitsfreie Python-Agentenstruktur um. Es ist ein
**Lehr-/Experimentiersystem**: dieselben Prinzipien wie Hyperon, aber klein
genug, um jede Zeile zu verstehen — mit Exportpfad zum echten MeTTa.

## Leitprinzip: Kognitive Synergie statt Monolith

Goertzels zentrale These: Allgemeine Intelligenz entsteht nicht aus einem
einzelnen Algorithmus (auch nicht aus einem LLM), sondern aus dem
**Zusammenspiel heterogener Lern-/Denkprozesse über einem gemeinsamen
Wissens-Metagraphen**. Jeder Prozess rettet die anderen aus ihrer
kombinatorischen Explosion:

```
                    ┌─────────────────────────────┐
                    │      CognitiveKernel        │   kognitiver Zyklus
                    │  (agents/orchestrator.py)   │
                    └──────────────┬──────────────┘
       ┌───────────────┬───────────┼───────────────┬───────────────┐
       ▼               ▼           ▼               ▼               ▼
 PerceptionAgent   GoalAgent  ReasoningAgent  LearningAgent   AttentionBank
 (LLM/Parser →     (OpenPsi:  (PLN Forward/   (MOSES +        (ECAN: STI/LTI,
  Atome)            Demands→   Backward        Pattern         Spreading, Rent,
                    Urges)     Chainer)        Mining)         Forgetting)
       │               │           │               │               │
       └───────────────┴───────────┼───────────────┴───────────────┘
                                   ▼
                    ┌─────────────────────────────┐
                    │         AtomSpace           │   gemeinsamer getypter
                    │   (core/atomspace.py)       │   Metagraph + TruthValues
                    └─────────────────────────────┘
                                   │
                                   ▼
                     bridge/metta_bridge.py  →  echtes Hyperon/MeTTa
```

## Abbildung Goertzel-Konzept → Code

| Goertzel-Konzept | Quelle | Modul hier |
|---|---|---|
| Atomspace (gewichteter, getypter Metagraph) | Hyperon-Paper arXiv:2310.18318 | `core/atom.py`, `core/atomspace.py` |
| PLN Simple Truth Values ⟨s, c⟩, c=n/(n+k) | PLN-Buch 2008 | `core/truthvalue.py` |
| PLN-Regeln (Deduktion, Inversion, Induktion, Abduktion, Revision, Modus Ponens) | PLN-Buch, trueagi-io/PLN | `pln/rules.py` |
| Forward/Backward Chainer + Evidenz-Tracking | trueagi-io/PLN (EvidenceID) | `pln/engine.py` |
| ECAN (STI/LTI, Rent, Spreading, Attentional Focus, Forgetting) | EGI Vol. 2 | `ecan/attention.py` |
| MOSES (evolutionäres Programmlernen, Occam-Bias) | Looks/Goertzel | `moses/evolution.py` |
| Pattern Mining (häufige Strukturen → neue Links) | CogPrime | `agents/learning.py` |
| OpenPsi/MetaMo (Demands → Urges → Zielsteuerung) | EGI; arXiv:2606.05411 | `agents/goals.py` |
| LLM als Wahrnehmungsorgan, nicht als Denker | arXiv:2309.10371 | `agents/perception.py` (`LanguageModel`-Protokoll) |
| Kognitiver Zyklus / MindAgents | CogPrime | `agents/base.py`, `agents/orchestrator.py` |
| MeTTa / Hyperon-Interop | metta-lang.dev | `bridge/metta_bridge.py` |

## Der kognitive Zyklus

Pro `kernel.run()`-Zyklus:

1. **PerceptionAgent** — Texte aus der Inbox werden zu Atomen
   (Inheritance-/EvaluationLinks) mit Wahrnehmungs-TV (s=0.9, c=0.7 — Wahrnehmung
   kann irren) und stimulieren ECAN.
2. **GoalAgent** — Demands verfallen langsam (Homöostase); Abweichung vom
   Sollwert erzeugt Urge, der zielrelevante Atome stimuliert → Top-down-Fokus.
3. **ReasoningAgent** — PLN-Forward-Chaining; Schlüsse über Atome im
   Attentional Focus erhalten mehr Stimulus (Synergie ECAN→PLN). Persistente
   Evidenzbuchhaltung verhindert Konfidenz-Inflation durch Doppelzählung.
4. **LearningAgent** — MOSES lernt boolesche Konzeptdefinitionen aus
   Beispielen; der Pattern Miner schlägt SimilarityLinks für Konzepte mit
   gemeinsamen Eltern vor (Synergie Mining→PLN).
5. **AttentionBank.step()** — Spreading (Assoziation), Rent (Vergessen als
   Default), Forgetting (LTI-erschöpfte Atome werden entfernt).

Anfragen von außen: `kernel.ask(InheritanceLink(A, B))` → Backward Chainer
liefert TruthValue **plus Beweisspur** (auditierbare Inferenz — Goertzels
Gegenentwurf zur LLM-Blackbox).

## Wo LLMs andocken (bewusst als Rand, nicht als Kern)

`agents/perception.py` definiert das Protokoll `LanguageModel.extract_triples()`.
Default ist ein regelbasierter Parser (offline, deterministisch). Ein
Claude-/anderes-LLM-Backend kann eingesteckt werden, ohne dass sich am
Reasoning etwas ändert — genau Goertzels "Neural Space"-Idee: neuronale
Modelle als austauschbare Organe am symbolisch-probabilistischen Kern.

## Bewusste Vereinfachungen gegenüber echtem Hyperon

- Kein verteilter Atomspace (DAS), keine Nebenläufigkeit — ein Prozess, ein Graph.
- PLN: nur First-Order-Termlogik-Kern (keine intensionale Inferenz,
  keine Indefinite Truth Values, keine Quantoren).
- MOSES: Turnierselektion + Subtree-Operatoren statt Demes/Representation-Building.
- ECAN: vereinfachte Ökonomie (kein Wages/Rent-Marktmechanismus, keine HebbianLinks).
- MeTTa: Export von Fakten + TVs, kein vollständiger Interpreter — dafür
  `MettaBridge` zum offiziellen `hyperon`-Paket (`pip install hyperon`).

## Web-UI: dem System beim Denken zusehen

`python3 -m webui.server` startet das **Kognitions-Cockpit** (reine Stdlib,
Port 8000): links Dialog (Aussagen beibringen, Fragen mit PLN-Beweiskette),
Mitte der Atomspace als Force-Directed-Graph (Knotengröße = STI, Kanten-
Deckkraft = Konfidenz), rechts Attentional Focus, Demands und der
Self-Update-Status, unten das Live-Protokoll des kognitiven Zyklus.
JSON-API: `/api/state`, `/api/tell`, `/api/ask`, `/api/step`, `/api/selfupdate`.

## Selbstorganisiertes Vordenker-Update

`goertzel_agi/selfupdate/` hält das Wissen über Goertzels aktuelle Arbeit
selbst aktuell — gesteuert nicht per Cronjob, sondern OpenPsi-konform:
ein Demand `aktualitaet` verfällt langsam; übersteigt der Urge die Schwelle
(und ist der Cooldown vorbei), fragt der `SelfUpdateAgent` seine Quellen ab
(arXiv-API `au:"Goertzel"`, Substack-RSS). Neue Werke werden als Atome
verankert (`(Evaluation publizierte (List goertzel werk:...))`, VLTI =
nie vergessen), dedupliziert über `data/selfupdate_state.json` und
menschenlesbar in `docs/research/auto-updates.md` protokolliert. Offline
bleibt der Urge bestehen — das System versucht es von selbst wieder.

**Bewusste Grenze:** Der Agent aktualisiert *Wissen*, nicht seinen eigenen
*Code*. Sichere Code-Selbstmodifikation verlangt Zielsystem-Invarianten —
genau das Thema von Goertzels Metagoals-Paper (arXiv:2412.16559) — und
bleibt eine dokumentierte Ausbaustufe (siehe unten).

## Nächste Ausbaustufen

1. `pip install hyperon` und PLN-Regeln in MeTTa selbst formulieren
   (Vorlage: [trueagi-io/PLN](https://github.com/trueagi-io/PLN)).
2. LLM-Backend für `LanguageModel` (Wissensextraktion aus Freitext).
3. Higher-Order-PLN (ImplicationLinks zwischen Prädikaten, Quantoren).
4. ActPC-Linie (arXiv:2412.16547 / 2501.04832) als alternativer Lernkern.
5. Metagoals (arXiv:2412.16559) im GoalAgent: Invarianten bei Zielrevision.
