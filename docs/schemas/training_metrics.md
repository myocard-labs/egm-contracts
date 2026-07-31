# training_metrics

## What it is

A flat per-epoch training-metrics table. One row per epoch, written
as `metrics.csv` into each training-run's checkpoint directory.
Column order is the contract.

The lightweight companion to `run_record`: `run.json` is the
full-fidelity record, `metrics.csv` is the lossy flat slice for fast
loading.

## Why it exists

Plotting training curves and skimming "did this run converge?" is a
common workflow. Drilling into `run.json` to assemble a series of
val_auroc values is awkward. A CSV with one row per epoch and named
columns lets you do `pd.read_csv("metrics.csv").plot(x="epoch", y="val_auroc")`
in one line.

CSVs can't carry version metadata cleanly, so the version contract
lives in the sibling `run.json`'s `schema_version`. Consumers that
need the contract identifier read it from `run.json`; consumers that
only need to plot curves read the CSV directly and assume the
column contract is stable.

## Field walkthrough

One row per epoch. Columns in this order:

- **`epoch`** — 1-based, strictly increasing. **Required, non-null.**
- **`lr`** — learning rate at the epoch's last optimizer step.
  **Required and finite.**
- **`train_loss`** — mean training-set loss across batches.
  **Required and finite.**
- **`train_auroc`** / **`train_accuracy`** / **`train_precision`** /
  **`train_recall`** / **`train_f1`** / **`train_ece`** — *added in
  egm-contracts v0.6.0.* The training-split counterparts of the `val_*`
  metrics below, with the same definitions and the same nullability rules.
  Additionally absent altogether from CSVs written before the producer
  emitted them. `train_ece` carries one caveat the val twin doesn't: it is
  computed from predictions accumulated *during* the epoch, so it describes
  the model as it changed, not a single fixed model.
- **`val_loss`** — mean validation-set loss across batches.
  **Required and finite.** (Which split is "validation" is defined
  in the run config, not here.)
- **`val_auroc`** — validation AUROC for the positive class.
  *Nullable*: undefined on a single-class val split.
- **`val_accuracy`** — validation accuracy at the configured
  decision threshold. *Nullable*: undefined on an empty val split.
- **`val_precision`** — TP / (TP + FP). *Nullable* when no
  positives were predicted.
- **`val_recall`** — TP / (TP + FN). *Nullable* when no actual
  positives in the val split.
- **`val_f1`** — harmonic mean of precision and recall. *Nullable*
  when either is null.
- **`val_ece`** — Expected Calibration Error: weighted average gap
  between predicted confidence and empirical accuracy. Lower is
  better-calibrated. *Nullable* when no reliability bin contains
  samples.
- **`epoch_seconds`** — wall-clock seconds for the epoch.
  **Required and finite.**

The required-non-null vs nullable distinction matters: if `lr` or
`train_loss` comes through as null/empty, that's a producer bug
worth surfacing, not legitimate data. The validators fail-fast on
malformed writes rather than silently propagating NaN into
downstream plots.

### Why train and val are interleaved, not appended

The column order pairs the two blocks — `epoch, lr, train_loss, train_*,
val_loss, val_*, epoch_seconds` — rather than appending the train metrics
after the val ones. Appending would have been the smaller change. The reason
for carrying both splits at all is to read the *divergence* between them, and
in a spreadsheet or a printed table that only jumps out when each metric sits
next to its twin. Consumers read by header name, so the order is presentation,
not parsing — which is exactly why it's worth choosing deliberately.

## CSV serialization conventions

- Header row with the column names above, in the documented order.
- Non-finite numbers (NaN / inf) in nullable columns are written
  as **empty cells**. The pandas default for `to_csv` with
  `na_rep=""`; consumers loading via `pd.read_csv(path)` read them
  back as NaN.
- The JSON representation of a row (used inside `run_record`'s
  per-epoch entries) treats those values as `null`. The schema
  describes both: `"type": ["number", "null"]` covers the JSON
  case, and the CSV mapping treats empty cell ≡ null.

## Versioning

This schema has no explicit `schema_version` field (CSV can't
easily embed one). The version contract is in the sibling
`run.json`'s `schema_version`. If you change this column set,
bump `X.Y` accordingly so the run record's
version reflects the change.

That coupling is intentional: anyone reading `metrics.csv` should
look at the run.json next to it to know what they're looking at.

## Where this is used

Produced by ML training pipelines. Consumed by training-curve
viewers, ad-hoc diagnostic notebooks, and any dashboard tool
wanting a quick "did this run converge" view.

## Example

```csv
epoch,lr,train_loss,train_auroc,train_accuracy,train_precision,train_recall,train_f1,train_ece,val_loss,val_auroc,val_accuracy,val_precision,val_recall,val_f1,val_ece,epoch_seconds
1,0.001,0.4500,0.87,0.80,0.82,0.78,0.80,0.04,0.4200,0.85,0.78,0.80,0.76,0.78,0.05,12.3
2,0.001,0.3200,0.92,0.86,0.88,0.84,0.86,0.03,0.3800,0.89,0.82,0.85,0.79,0.82,0.04,11.9
3,0.001,0.2500,0.96,0.91,0.92,0.90,0.91,0.02,0.3500,,0.85,,0.83,,0.03,12.1
```

Row 3 has an empty cell for `val_auroc` — could be because the val
split was all-one-class that epoch, hence AUROC was undefined.

The example also shows what the train block is *for*: train AUROC climbing
0.87 → 0.96 while val AUROC stalls is the divergence signature that
validation metrics alone can't distinguish from a task that's simply hard.
