# predictions

## What it is

The unified per-trace predictions interchange. **One format for all
evaluation outputs** — training-time per-split eval (val/test/train),
hybrid eval (mixed sources), inference benchmarks. Two paired files
per eval:

- **`predictions_<eval_name>.csv`** — flat row-per-trace table. CSV
  column order is the contract.
- **`predictions_<eval_name>.json`** — manifest carrying
  `schema_version`, `eval_name`, producer info, source-bank
  pointers, plus the same rows in structured form.

Schema version: `2.0`.

## Why it exists as one format

A prediction is always "model run on a trace, here's the output."
Whether the trace came from a synthetic bank or from real-data
extraction is a per-row attribute (`source`), not a separate format.
Whether the eval is training-time or hybrid is a per-eval attribute
(`eval_name`), not a separate format. Pulling those into columns /
fields gives a single, consistent contract.

The bumped version (`2.0`) signals the consolidation from an
earlier v1 that had separate per-split-eval and cross-source-eval
formats. Old consumers refuse to misread new files because the
major version differs.

## Field walkthrough

### Top-level (the manifest)

- **`schema_version`** — `"2.0"`.
- **`created_utc`** — ISO-8601 timestamp at write time.
- **`eval_name`** — identifier for what this eval represents.
  Producer-defined snake_case (e.g., `"val_epoch_42"`, `"test"`,
  `"hybrid_eval_iafdb_v1"`). Distinguishes the eval at the
  file-system level.
- **`n`** — count of rows, equal to `len(predictions)`.
- **`columns`** — CSV column order. Producer must emit exactly the
  `x-csv-column-order` list documented in the schema; consumers
  can use this to sanity-check the paired CSV.
- **`producer`** — where the predictions came from. Required:
  `run_id` (matches the source run record's id),
  `model_checkpoint` (path to the model artifact). Optional:
  `model_artifact_sha256` for tamper detection.
- **`sources`** — pointers to the source banks each prediction row
  came from. At least one of `synthetic_bank` or `iafdb_bank` must
  be present. Each carries `path`, `schema_version`, and an
  optional `sha256`. Consumers join on `(source, trace_index)` to
  retrieve the original waveform.
- **`predictions`** — array of `Prediction` rows.

### Prediction ($defs)

One row per evaluated trace. Six fields are always present; six
are optional and filled only when applicable:

**Required:**

- **`source`** — `"synthetic"` or `"iafdb"`. Drives which optional
  fields apply.
- **`split`** — `"train"`, `"val"`, `"test"`, `"iafdb"`, or a
  producer-defined snake_case string.
- **`trace_index`** — row index into the source bank's `traces/`
  group.
- **`true_label`** — integer ground-truth class. For the binary
  case: `0` healthy / `1` fibrotic. Integer (not enum) deliberately,
  so the schema doesn't break when multi-class severity or pattern
  classification lands. Class meaning lives in `model_metadata`.
- **`prob_fibrotic`** — calibrated `P(fibrotic)` from the model.
  For multi-class this is the post-softmax probability for class
  index 1.
- **`pred_label`** — predicted class label at the configured
  decision threshold.

**Optional (write when known):**

- **`logit`** — raw model output before sigmoid/softmax. Useful
  for offline threshold sweeps and calibration analysis.
- **`simulation_id`** — synthetic simulation/patient id. Present
  when `source == "synthetic"`.
- **`patient_id`** — real-data patient identifier. Present when
  `source == "iafdb"`.
- **`fibrosis_density`** — realized fibrosis density (synthetic
  only; 0.0 for real-data rows).
- **`eval_index`** — 0-based eval order.
- **`correct`** — `1` iff `pred_label == true_label`, else `0`.
  Semantically boolean; stored as int so CSV serializes as
  `0`/`1`. Optional because consumers can recompute.

## Versioning

Currently `2.0`. Bump triggers:

- A required field added (e.g., per-class probabilities for
  multi-class).
- A required field removed.
- Changing the meaning of `true_label` / `pred_label` integers
  (e.g., adopting a label codebook that's not project-internal).
- Renaming any field.

Adding *optional* fields also bumps minor — old consumers will
silently miss the new data, and the bump is the discovery
mechanism.

## Where this is used

Produced by ML evaluation pipelines (Python or C++ inference).
Consumed by inspection tooling that joins predictions on
`(source, trace_index)` against the source bank, paper-figure
pipelines that render calibration / confusion analyses, and
benchmark comparisons across runtimes.

## Example

Manifest (JSON):

```json
{
  "schema_version": "2.0",
  "created_utc": "2026-06-15T22:00:00Z",
  "eval_name": "hybrid_eval_iafdb_v1",
  "n": 3,
  "columns": ["source", "split", "trace_index", "true_label", "prob_fibrotic", "pred_label",
              "logit", "simulation_id", "patient_id", "fibrosis_density", "eval_index", "correct"],
  "producer": {
    "run_id": "v1_baseline",
    "model_checkpoint": "checkpoints/v1_baseline/best.pt"
  },
  "sources": {
    "synthetic_bank": {"path": "banks/hybrid_v1.h5", "schema_version": "1.0"},
    "iafdb_bank": {"path": "banks/iafdb_healthy_v1.h5", "schema_version": "1.0"}
  },
  "predictions": [
    {"source": "synthetic", "split": "test", "trace_index": 0, "true_label": 1,
     "prob_fibrotic": 0.92, "pred_label": 1, "logit": 2.5,
     "simulation_id": 7, "fibrosis_density": 0.35, "correct": 1},
    {"source": "iafdb", "split": "iafdb", "trace_index": 100, "true_label": 0,
     "prob_fibrotic": 0.99, "pred_label": 1, "logit": 4.6,
     "patient_id": "iaf3", "correct": 0},
    {"source": "iafdb", "split": "iafdb", "trace_index": 101, "true_label": 0,
     "prob_fibrotic": 0.01, "pred_label": 0,
     "patient_id": "iaf3", "correct": 1}
  ]
}
```

CSV (sibling file):

```csv
source,split,trace_index,true_label,prob_fibrotic,pred_label,logit,simulation_id,patient_id,fibrosis_density,eval_index,correct
synthetic,test,0,1,0.92,1,2.5,7,,0.35,,1
iafdb,iafdb,100,0,0.99,1,4.6,,iaf3,,,0
iafdb,iafdb,101,0,0.01,0,,,iaf3,,,1
```

Empty cells in optional columns signal "not applicable to this row's
source" — synthetic rows have no `patient_id`, IAFDB rows have no
`simulation_id` / `fibrosis_density`.
