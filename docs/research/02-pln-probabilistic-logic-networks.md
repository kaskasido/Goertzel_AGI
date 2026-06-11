# PLN — Probabilistic Logic Networks

> Hinweis: Häufig als "PNL" verschrieben — der korrekte Name ist **PLN, Probabilistic Logic Networks**.

## 1. Theorie (Buch 2008)

**Quelle:** *Probabilistic Logic Networks: A Comprehensive Framework for Uncertain Inference* — Ben Goertzel, Matthew Iklé, Izabela Freire Goertzel, Ari Heljakka (Springer 2008, ISBN 9780387768717).

PLN ist ein Framework für **unsicheres Schließen**: von unsicheren Daten zu unsicheren Schlussfolgerungen — Deduktion, Induktion, Abduktion, Analogie, Fuzziness, temporales/kausales Schließen.

### Wahrheitswerte
- **Simple Truth Value (STV):** Paar ⟨strength s, confidence c⟩. s = wahrscheinlichkeitsartiges Glaubensmaß, c = Maß der Evidenzmenge. Äquivalent: (s, n) mit Evidenzanzahl n, verbunden über den "personality parameter" k: **c = n / (n + k)**.
- **Indefinite Truth Values:** ⟨[L, U], b, k⟩ — Wahrscheinlichkeitsintervall, Kredibilität b, Lookahead k; Hybrid aus Walleys impräzisen Wahrscheinlichkeiten und bayesschen Kredibilitätsintervallen.

### Termlogik statt reiner Prädikatenlogik
PLN baut auf **Termlogik** auf (NARS-beeinflusst): `Inheritance A B` ≈ P(B|A). Dadurch werden Induktion und Abduktion natürliche Umstellungen der Deduktion, mit **Bayes-Inversion** als Brücke. First-Order-PLN: Vererbung/Mitgliedschaft zwischen Konzepten; Higher-Order-PLN: Implikationen zwischen Prädikaten/Aussagen.

### Kernformeln (Buch / trueagi-io/PLN)
| Regel | Schema | Formel (strength) |
|---|---|---|
| Deduktion | A→B, B→C ⊢ A→C | `sAC = sAB·sBC + (1−sAB)·(sC − sB·sBC)/(1−sB)` |
| Inversion (Bayes) | A→B ⊢ B→A | `sBA = sAB·sA/sB` |
| Induktion | A→B, A→C ⊢ B→C | Inversion + Deduktion verkettet |
| Abduktion | A→C, B→C ⊢ A→B | Deduktion + Inversion verkettet |
| Modus Ponens | A→B, A ⊢ B | `s ≈ sP·sPQ + kleiner Term·(1−sP)` |
| Revision | zwei TVs derselben Aussage | Gewichte `wi = ci/(1−ci)`: `s = (w1·s1+w2·s2)/(w1+w2)`, `c = (w1+w2)/(w1+w2+1)` — Evidenz addiert sich: n = n1+n2 |

Count↔Konfidenz im MeTTa-Repo: `c2w(c)=c/(1−c)`, `w2c(w)=w/(w+1)` (k=1; OpenCog Classic nutzte teils größeres k).

## 2. Implementierungen

- **OpenCog Classic:** [github.com/opencog/pln](https://github.com/opencog/pln) auf der URE (Unified Rule Engine), Atomese/Scheme (`pln-fc`, `pln-bc`). **Nicht mehr gepflegt** — abgelöst durch die trueagi-io-Repos.
- **Hyperon/MeTTa:**
  - [trueagi-io/PLN](https://github.com/trueagi-io/PLN) — "Modern PLN implementation for Hyperon": MeTTa-nativ, STVs, **EvidenceID-Tracking gegen Evidenz-Doppelzählung** bei Revision, API `PLN.Derive` / `PLN.Query`, Inferenzkontrolle gegen kombinatorische Explosion.
  - [trueagi-io/pln-experimental (hyperon-pln)](https://github.com/trueagi-io/pln-experimental) — Formulierung über **dependente Typen** (Curry-Howard), z.B. `DeductionDTL.metta`; dazu das "nuPLN"-Manuskript (vollständige mathematische Grundlegung über eine globale universelle Verteilung).
  - Neuere Formulierungen: Differentiable PLN ([arXiv:1907.04592](https://arxiv.org/pdf/1907.04592)), parakonsistente Grundlagen ([arXiv:2012.14474](https://arxiv.org/abs/2012.14474)), PLN für temporales/prozedurales Schließen, PLN-vs-NARS-Vergleich ([arXiv:2412.19524](https://arxiv.org/abs/2412.19524), Goertzel 2024).

## 3. Rolle im AGI-Design: Kognitive Synergie

In CogPrime/PrimeAGI und Hyperon ist PLN die deklarative Schlussfolgerungs-Engine, die mit den anderen Prozessen interoperiert ([Formal Model of Cognitive Synergy, arXiv:1703.04361](https://arxiv.org/pdf/1703.04361)):
- **ECAN** lenkt, *worüber* PLN nachdenkt; PLN kann umgekehrt erschließen, was Aufmerksamkeit verdient.
- **MOSES** lernt Prozeduren; PLN+MOSES-Synergie z.B. in spekulativer Bio-Inferenz demonstriert.
- **Pattern Miner** liefert Prämissen für PLN.

Kernthese: Jeder Lernalgorithmus hilft den anderen aus deren kombinatorischen Explosionsengpässen, weil alle denselben Atomspace teilen.

## 4. PLN vs. reine LLMs

Goertzel ([arXiv:2309.10371](https://arxiv.org/pdf/2309.10371)): LLMs machen probabilistische Oberflächenassoziation, halluzinieren und scheitern an mehrstufigem Schließen und echter Kreativität. PLN bietet explizite, auditierbare Inferenzketten mit Unsicherheitspropagation — skaliert aber allein nicht. Daher: **hybride neural-symbolische Architektur** (LLMs + PLN + evolutionäres Lernen in einem Atomspace) unter kognitiver Synergie.

## Umsetzung in diesem Repo
- `goertzel_agi/core/truthvalue.py` — STV mit c=n/(n+k), Revision per Gewichtsformel
- `goertzel_agi/pln/rules.py` — exakte Buchformeln (Deduktion, Inversion, Induktion, Abduktion, Modus Ponens, ∧/∨/¬, Similarity)
- `goertzel_agi/pln/engine.py` — Forward + Backward Chainer mit persistenter Evidenzbuchhaltung (gegen Doppelzählung)
