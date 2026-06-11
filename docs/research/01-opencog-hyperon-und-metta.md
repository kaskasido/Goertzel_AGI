# OpenCog Hyperon & MeTTa (Stand Juni 2026)

## 1. Überblick & Architektur

**OpenCog Hyperon** ist die Neuentwicklung des klassischen OpenCog-Frameworks unter Ben Goertzel (SingularityNET / TrueAGI / ASI Alliance) — explizit Infrastruktur für AGI-Forschung. Quellen: [hyperon.opencog.org](https://hyperon.opencog.org/), [trueagi-io/hyperon-experimental](https://github.com/trueagi-io/hyperon-experimental/), Design-Paper [arXiv:2310.18318](https://arxiv.org/abs/2310.18318).

Kernelemente:
- **Atomspace** — zentraler Wissensspeicher, formal ein **Metagraph** (Links können Links verbinden). Jedes MeTTa-Programm ist selbst ein Subgraph: Code = Wissen = Daten, vollständig homoikonisch und durch andere Programme abfragbar/umschreibbar (theoretische Basis: [arXiv:2112.08272](https://arxiv.org/abs/2112.08272)).
- **MeTTa (Meta Type Talk)** — Nachfolger von Atomese; vereint funktionale, logische und Prozesskalkül-Programmierung.
- **DAS (Distributed Atomspace)** — skalierbarer verteilter Backend ([singnet/das](https://github.com/singnet/das), Pip: `hyperon-das`).
- **Kognitive Synergie** — mehrere KI-Algorithmen (PLN, evolutionäres Lernen, ECAN, Pattern Mining, NNs) arbeiten nebenläufig auf demselben Atomspace ([arXiv:1703.04361](https://arxiv.org/pdf/1703.04361)). Laut [Fortschrittsbericht 12/2025](https://singularitynet.io/hyperon-progress-from-prototypes-to-scalable-intelligence/) "interweave dynamically rather than in isolation".

## 2. MeTTa-Sprache

### Atome (4 Arten)
1. **Symbole** (`Sam`, `frog`, `+`), 2. **Variablen** (`$x`), 3. **Expressions** (`(A (B C) D)`), 4. **Grounded Atoms** (Zahlen, Strings, Python/Rust-Objekte, NNs, aufrufbare Prozeduren).

### Pattern Matching (Herz der Sprache)
```metta
(Sam is a frog)
(Tom is a cat)
!(match &self ($who is a $what) ($who the $what))
; => (Sam the frog) (Tom the cat)
```

### Gleichungen als Rewrite-Regeln + Nichtdeterminismus
```metta
(= (color) green)
(= (color) yellow)
!(color)            ; => green, yellow  (alle Treffer, "superposed")
!(collapse (color)) ; nichtdeterministisch -> Tupel
```

### Typsystem (graduell, bis dependente Typen)
```metta
(: Z Nat)
(: S (-> Nat Nat))
(: Add (-> Nat Nat Nat))
(= (Add $x Z) $x)
(= (Add $x (S $y)) (Add (S $x) $y))
!(Add (S Z) Z)   ; => (S Z)
```

### Minimal MeTTa
Der Interpreter ist über einen winzigen Turing-vollständigen Kern spezifiziert (`eval`, `chain`, `unify`, `function`/`return`, `cons-atom`/`decons-atom`, …): [minimal-metta.md](https://github.com/trueagi-io/hyperon-experimental/blob/main/docs/minimal-metta.md).

## 3. Komponenten

- **PLN für Hyperon:** [trueagi-io/hyperon-pln](https://github.com/trueagi-io/hyperon-pln), generisches Chaining: [trueagi-io/chaining](https://github.com/trueagi-io/chaining)
- **MOSES:** Nachfolger "MeTTa-MOSES" (Reife geringer als PLN, kanonisches Repo *unsicher*)
- **ECAN:** aktive PRIMUS-Komponente, aber noch in Design/Evaluation (offene [DeepFunding-RFP](https://deepfunding.ai/rfp/framework-for-evaluating-approaches-to-attention-allocation/))
- **WILLIAM** (kompressionsbasiertes Pattern Mining), **MetaMo** (Motivation), [hyperon-miner](https://github.com/trueagi-io/hyperon-miner)
- **PRIMUS:** die kognitive Architektur über Hyperon (PLN+MOSES+ECAN+WILLIAM+Konzeptbildung); Stack: MeTTa, MeTTa-IL, MORK-Backend, MM2-Kernel, Blockchain-Pfad zu ASI:Chain. Orchestrierung: [HyperClaw v2](https://singularitynet.io/hyperclaw-a-cognitive-orchestration-layer-for-the-road-to-agi/)

## 4. Projektstand 2024 → Mitte 2026

- **Alpha:** April 2024 (MeTTa-Interpreter + DAS) — [Ankündigung](https://medium.com/singularitynet/announcing-the-release-of-opencog-hyperon-alpha-38941f8f389f)
- **Releases:** v0.2.4 (04/2024) … v0.2.9 (11/2024, DAS v1.0.0) → **v0.2.10 (11.02.2026, aktuell)** mit veröffentlichter [MeTTa-Spezifikation](https://trueagi-io.github.io/hyperon-experimental/metta/). Repo weiterhin selbstdeklariert **pre-alpha**; ein offizielles "Beta" existiert nicht (*unsicher/Roadmap-Sprache*).
- **Performance-Story 2025:** [MORK](https://github.com/trueagi-io/MORK) (MeTTa Optimal Reduction Kernel, beanspruchte 10³–10⁶× Speedups) + schnelle Compiler (MM2; Goertzel 10/2025: "a couple different variants of fast MeTTa language compiler working now"). Laut 12/2025 laufen PRIMUS-Experimente "across millions of atoms in real time".
- **Alternative Implementierungen:** [metta-wam](https://github.com/trueagi-io/metta-wam) (SWI-Prolog), PeTTa, jetta (JVM, *unsicher*), MettaWamJam.
- **Anwendungen 2025:** Game-AI-Piloten, Bioinformatik ([Rejuve.Bio](https://singularitynet.io/opencog-hyperon-revolutionizing-biomedical-research-for-longevity-with-the-rejuve-bio/)), Mathematik, soziale Robotik, MeTTa→Smart-Contracts.

## 5. Installation & erste Schritte

```bash
python3 -m pip install hyperon   # aktuell: 0.2.10 (Python 3.8-3.12)
metta-py                          # REPL
metta-py meinskript.metta         # Skript ausführen
# oder: docker run -ti trueagi/hyperon:latest
```

```metta
(= (greet $name) (Hello $name))
!(greet World)                    ; => (Hello World)
```

## 6. Doku & Tutorials

- [metta-lang.dev](https://metta-lang.dev) — offizielle Doku + Browser-Playground
- [MeTTa-Spezifikation](https://trueagi-io.github.io/hyperon-experimental/metta/), [API-Doku](https://trueagi-io.github.io/hyperon-experimental)
- [metta-examples](https://github.com/trueagi-io/metta-examples) + annotierte Testskripte `python/tests/scripts/` (Symbole → Nichtdeterminismus → Typen → Grounded → Spaces → PLN-TVs)
- Wiki: [Hyperon](https://wiki.opencog.org/w/Hyperon), [MeTTa](https://wiki.opencog.org/w/MeTTa)
