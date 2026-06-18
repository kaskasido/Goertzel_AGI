# Goertzel_AGI

**A teachable, explainable neuro-symbolic AI engine** inspired by Ben
Goertzel's OpenCog Hyperon. Instead of training billions of weights, you
*teach* it short sentences and it grows a knowledge graph it can reason over —
and it shows you its proof chains. Pure Python, **zero dependencies**.

> Not pure LLM. The engine combines a knowledge metagraph (**Atomspace**),
> probabilistic logic (**PLN**) with truth values and proof traces, an
> attention economy (**ECAN**), and evolutionary rule learning (**MOSES**) —
> the "cognitive synergy" idea from Goertzel's AGI research, in a small,
> readable codebase you can run on a laptop.

---

## Quickstart

**Windows:** double-click `start.bat`, then open <http://localhost:8000>.

**Any OS (Python 3.10+):**
```bash
python -m webui.server          # then open http://localhost:8000
```
No `pip install` needed — the core has no dependencies.

In the dashboard you can:
- **Teach** it sentences: `Socrates is a human`, `A human is a mammal`
- **Ask** questions it was never told directly: `socrates` → `mortal_thing`
  comes back **with a proof chain** and a confidence value
- **Watch it think**: the Atomspace graph, attention focus, goals and the
  per-cycle log of what each agent did

Load the included demo knowledge pack to see it all at once:
```bash
python -m goertzel_agi.teach knowledge/demo     # or double-click teach_demo.bat
```

## How to use this repository

Think of the repository as a small workshop with three simple modes:

1. **Start the web UI**  
   Run `python -m webui.server` and open <http://localhost:8000>.
2. **Load knowledge**  
   Teach a folder such as `knowledge/demo` or `knowledge/chess` with
   `python -m goertzel_agi.teach <folder>`.
3. **Inspect what the system learned**  
   Ask questions in the UI, inspect proof chains, and watch the knowledge graph
   evolve.

### Typical workflow

- **Try the demo first** to understand the reasoning flow end-to-end.
- **Use a knowledge pack** when you want a ready-made domain, for example the
  chess pack in `knowledge/chess/`.
- **Create your own pack** by copying the structure from `knowledge/demo/` and
  writing short factual sentences.
- **Use the inbox flow** when your knowledge starts as `.txt`, `.md`, `.csv`,
  `.pdf`, or `.docx` files.

### Practical examples

- If you want to explore symbolic reasoning, start with `knowledge/demo/`.
- If you want to model a specific topic step by step, create a new folder under
  `knowledge/` and teach it with `python -m goertzel_agi.teach`.
- If Alex wants to understand chess knowledge or later derive patterns from
  saved games, `knowledge/chess/` is the best starting point before adding more
  source material through the inbox pipeline.

### Alex memory input (important)

If Alex is the only living witness of specific games, he should explicitly teach
those memories to the AGI:

- which **exact moves** he and his brother chose in critical moments
- **why** a move was chosen (plan, evaluation, or practical constraint)
- whether a decision was primarily **emotional** (stress, fear, confidence,
  revenge, surprise) or **rational** (calculation, position, opening prep)

This context is essential because PGN alone shows *what* was played, but Alex's
explanations add *why* it was played.

---

## What makes it different

| | Pure LLM | Goertzel_AGI |
|---|---|---|
| Answers | plausible text | derived facts **with proof traces** |
| Learning | retraining weights | teaching sentences (instant, transparent) |
| Rules | hidden in weights | **human-readable** (MOSES learns e.g. `flu_suspected = has_fever AND has_cough`) |
| Uncertainty | none explicit | every fact carries strength + confidence (PLN) |
| Footprint | GPUs | a laptop, zero dependencies |

---

## Build your own domain expert

The engine is **domain-neutral** — a domain is just a folder of short
sentences. The bundled `knowledge/demo/` shows the pattern; copy it and write
your own:

```
# vocabulary first (defines which questions become askable)
A symptom is a finding
fever causes discomfort
# then taxonomy, then relations ...
```

Teach it, then ask. Relations like `causes` and `is_part_of` are **transitive**
— the system derives multi-step chains you never stated, with confidence that
decreases per step.

### Automated learning: folders, tables, case files
- **Inbox** — drop files in `inbox/`, the engine learns them and tidies up
  (`python -m goertzel_agi.ingest`, or the "Process inbox" button).
  Supports `.nico/.txt/.md`, `.csv`, and `.pdf/.docx` (with optional extras).
- **CSV / SQLite** — import rows as knowledge **or** as case tables that feed
  **MOSES**, which learns a readable classification rule. See
  `examples/inbox_examples/`.

### Optional: LLM as a perception organ
With an Anthropic API key, Claude can turn free-form sentences into knowledge
triples (`pip install anthropic`, set `ANTHROPIC_API_KEY`). The reasoning
still happens symbolically in the Atomspace — the LLM is a swappable organ at
the edge, exactly as Goertzel's "Neural Space" idea suggests. Without a key,
a built-in rule-based parser handles simple sentences offline.

---

## Architecture (in one breath)

```
Perception (rules or LLM) ─┐
Goals (OpenPsi demands) ────┤
Reasoning (PLN + chains) ───┼──▶  shared AtomSpace  ──▶  Web dashboard
Learning (MOSES + mining) ──┤      (typed metagraph         + MeTTa export
Attention (ECAN economy) ───┘       with truth values)        to real Hyperon)
```

All processes read and write the **same** knowledge graph — that shared
substrate is where "cognitive synergy" happens. Background notes and sources
are in `docs/`.

Bridge to the real thing: `examples/demo_hyperon_bridge.py` exports the graph
as MeTTa and (with `pip install hyperon`) queries it inside OpenCog Hyperon.

---

## Tests

```bash
python -m unittest discover -s tests
```

## Disclaimer

This is an independent, educational implementation of ideas from Ben
Goertzel's published work (OpenCog, Hyperon, PLN, MOSES, CogPrime). It is
**not affiliated with or endorsed by** Ben Goertzel, SingularityNET, or the
OpenCog/TrueAGI projects. For the real, full-scale system see
[opencog.org](https://opencog.org) and [metta-lang.dev](https://metta-lang.dev).

## License

MIT — see [LICENSE](LICENSE).
