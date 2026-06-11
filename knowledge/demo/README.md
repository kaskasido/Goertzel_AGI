# Demo knowledge pack

A small, neutral knowledge pack that exercises every feature of the engine.
Use it to see how the system learns and reasons before you build your own
domain pack.

## Load it

```bash
# in the web UI: type sentences yourself, or load this pack headless:
python -m goertzel_agi.teach knowledge/demo
```

## Things to ask afterwards

In the UI's **question** box (Subject / is a / Object):

- `socrates` → `mortal_thing` — the system proves it through a chain
  (Socrates → human → mammal → animal → living_being → mortal_thing),
  even though you never stated it directly. You get a **proof trace**.

In the **relation question** box (Subject + relation):

- `rain` + `causes` → the full causal chain down to `accidents`
- `a_cell` + `is_part_of` → the chain up to `an_organism`

## Build your own domain pack

Copy this folder, keep `00_relations.nico` as your vocabulary, then write
short `SUBJECT VERB OBJECT` sentences. Layer them: vocabulary first, then
taxonomy, then relations. The relations you teach define which questions
become answerable. See the main README for the connector tools (folders,
CSV, case tables for rule learning).
