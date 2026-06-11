# Inbox examples

Copy these into the `inbox/` folder (at the project root) and click
"Process inbox" in the UI — or run `python -m goertzel_agi.ingest`.

| File | What happens |
|---|---|
| `facts_example.csv` | Each row becomes a knowledge triple (subject/relation/object). |
| `cases_example.csv` + `.csv.json` | Case table → MOSES learns a readable rule `flu_suspected`. |

## Build your own case table

One row per (anonymized) case. Feature columns hold `yes`/`no` (also `x`,
`1`, `true` count as yes), plus one label column. Add a sidecar
`<name>.csv.json`:

```json
{
  "mode": "cases",
  "label_col": "outcome",
  "feature_cols": ["has_fever", "has_cough"],
  "positive_label": "flu",
  "concept": "flu_suspected"
}
```

The learned rule is **readable** — you see exactly what the system bases its
judgement on. Note: never put real personal/patient data in a public repo;
the `inbox/` folder is git-ignored.
