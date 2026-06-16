# hybrid_eval_metrics

## What it is

Aggregate metrics for a **hybrid evaluation** — an evaluation where
the test set mixes synthetic positives with real-data negatives.
Written as `hybrid_eval_metrics.json`. Pairs with a
`predictions_<eval_name>.csv` + `predictions_<eval_name>.json`
written under the `predictions` contract: this file records the
aggregate scores; the predictions file holds per-trace outputs.

Schema version: `1.0`.

## Terminology: "hybrid"

We use "hybrid" following the cardiac-ML convention from Sánchez et
al. 2021 (Frontiers in Physiology 12, 699291) — a "hybrid in silico
+ in vivo" evaluation mixes simulated and real recordings. Both the
schema name and the file name use this convention.

A synthetic bank is *not* called hybrid even when it has real-noise
conditioning applied — the labels are still 100% synthetic. See the
top-level [schemas README](README.md) for the broader terminology
convention.

## Why it exists

Aggregate metrics on a mixed eval are necessary but not sufficient
to characterize generalization. A model that scores every real-data
trace as "fibrotic" can still produce a high AUROC if the synthetic
positives separate well — the AUROC ranking is dominated by the
synthetic-positive vs real-negative split. The fix is to break out
real-data-only behavior separately, which is what the `iafdb_only`
section is for. Three sentinel signals catch the saturation case:

- `mean_prob_fibrotic` — average predicted probability on real
  healthy data. Near 1.0 indicates saturation on the synthetic
  distribution.
- `fpr_at_0_5` — false-positive rate at the standard threshold.
  Near 1.0 means the decision function isn't usable as-is.
- `p1_prob_fibrotic` — 1st-percentile predicted probability on
  real data. The strongest saturation diagnostic: low values mean
  some real traces *did* get low probabilities, so a different
  threshold could recover behavior; high values mean no threshold
  will help.

## Field walkthrough

### Top-level

- **`schema_version`** — `"1.0"`.
- **`predictions_schema_version`** — version stamp for the sibling
  predictions CSV/JSON. Producer must write the predictions file
  using exactly this version. Currently
  `"2.0"`.
- **`created_utc`** — ISO-8601 timestamp.
- **`producer`** — identifies the model + run. Matches the
  `producer` object in the paired predictions manifest. Required:
  `run_id`, `model_checkpoint`.
- **`mixed`** — aggregate metrics on the full mixed eval set.
- **`iafdb_only`** — metrics on the real-data rows alone.

### mixed

- **`n`** — total rows in the eval.
- **`n_positives`** — synthetic-fibrotic rows (the positive class).
- **`n_negatives`** — real-healthy rows (the negative class).
- **`metrics`** — scalar metrics object. Well-known keys: `auroc`,
  `accuracy`, `precision`, `recall`, `f1`, `ece`. Confusion-matrix
  counts under a nested `confusion: {tp, fp, tn, fn}` object.
  Additional producer-defined keys allowed.

### iafdb_only

- **`n`** — count of real-data rows.
- **`mean_prob_fibrotic`** — mean predicted `P(fibrotic)` across
  real rows. Healthy ground truth, so a well-calibrated model is
  well below 0.5.
- **`fpr_at_0_5`** — false-positive rate at the 0.5 decision
  threshold (fraction of real rows predicted as fibrotic). 0.0 is
  ideal.
- **`p1_prob_fibrotic`** — 1st-percentile predicted `P(fibrotic)`
  on real rows.
- **`per_patient`** — optional per-patient breakdown keyed by
  patient_id. Inner shape is producer-defined; convention is one
  object per patient with the same scalar metrics as the aggregate.

## Versioning

Currently `1.0`. Bump triggers:

- Adding required real-data-only diagnostics (e.g., calibration
  drift).
- Renaming `mixed` / `iafdb_only` to multi-source generalizations.
- Adding per-class metrics for multi-class extensions.

## Where this is used

Produced by hybrid-eval pipelines that run a trained model against
a mixed sim+real eval set. Consumed by calibration / generalization
analysis tooling and paper-figure pipelines that render the
sim-only baseline vs hybrid eval comparison.

## Example

```json
{
  "schema_version": "1.0",
  "predictions_schema_version": "2.0",
  "created_utc": "2026-06-13T10:00:00Z",
  "producer": {
    "run_id": "v1_baseline",
    "model_checkpoint": "checkpoints/v1_baseline/best.pt"
  },
  "mixed": {
    "n": 98669,
    "n_positives": 120,
    "n_negatives": 98549,
    "metrics": {
      "auroc": 0.767,
      "accuracy": 0.0014,
      "confusion": {"tp": 120, "fp": 98534, "tn": 15, "fn": 0},
      "ece": 0.85
    }
  },
  "iafdb_only": {
    "n": 98549,
    "mean_prob_fibrotic": 0.999,
    "fpr_at_0_5": 1.00,
    "p1_prob_fibrotic": 0.9974,
    "per_patient": {
      "iaf1": {"mean_prob_fibrotic": 0.999, "fpr_at_0_5": 1.0},
      "iaf2": {"mean_prob_fibrotic": 0.999, "fpr_at_0_5": 1.0}
    }
  }
}
```
