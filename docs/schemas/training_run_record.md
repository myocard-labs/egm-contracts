# training_run_record

## What it is

A versioned, full-fidelity record of a single training run. Written as
`run.json` into each training-run's checkpoint directory.

Schema version: `1.0`.

## Why it exists

A flat per-epoch metrics table (the sibling `metrics` schema) is
lossy: it can't carry reliability bins, run-level metadata, or
held-out test metrics. `run_record` is the full-fidelity counterpart —
same per-epoch entries plus calibration data, the resolved training
config, the best-epoch summary, and optional final test-set metrics.

Schema version is part of the contract so consumers can refuse
unknown formats cleanly rather than silently misparsing.

## Field walkthrough

### Top-level

- **`schema_version`** — `"1.0"`.
- **`created_utc`** — ISO-8601 timestamp at write time. Set at the
  end of training, not the start.
- **`run`** — run-level metadata (object). Well-known keys
  (producer SHOULD write all of these): `run_id` (unique string),
  `git_sha` (repo state at training start), `host`, `model_version`,
  `training_started_utc`, `training_ended_utc`. Additional
  producer-defined keys allowed.
- **`config`** — fully-resolved training configuration as a nested
  object. Well-known top-level keys: `model`, `data`, `training`,
  `eval`. Contents reflect the producer's config system; consumers
  treat unknown keys as additional context.
- **`epochs`** — array of `EpochRecord`, one per training epoch.
- **`best`** — summary of the selected best epoch by the configured
  selection metric.
- **`test`** — optional. Final test-set metrics, present iff a test
  split was evaluated at the end of training.

### EpochRecord ($defs)

One per epoch:

- **`epoch`** — 1-based epoch number, strictly increasing.
- **`lr`** — learning rate at the epoch's last optimizer step.
- **`train_loss`** — mean training-set loss across batches in this
  epoch.
- **`val_loss`** — mean validation-set loss across batches in this
  epoch.
- **`epoch_seconds`** — wall-clock seconds for the epoch.
- **`val_metrics`** — object of scalar val metrics (AUROC,
  accuracy, precision, recall, F1, ECE, confusion-matrix counts).
  Non-finite values serialize as `null` so the JSON stays strictly
  valid.
- **`val_reliability`** — array of reliability bins for the
  calibration diagram.

### ReliabilityBin ($defs)

One bin of the calibration diagram:

- **`lo`** / **`hi`** — bin edges in [0, 1]. Predicted probabilities
  in `(lo, hi]` belong to this bin.
- **`count`** — number of samples in the bin.
- **`confidence`** — mean predicted probability across the bin
  (null when `count == 0`).
- **`accuracy`** — empirical accuracy across the bin (null when
  `count == 0`).

A well-calibrated model has `accuracy ≈ confidence` for every bin
(the diagonal on a reliability diagram). The integrated gap is
typically summarized by `val_ece`.

## Versioning

Currently `1.0`. Bump triggers:

- Adding a required field to `EpochRecord` or to the top-level.
- Changing the meaning of an existing field.
- Adding multi-class metrics that need new nested structure.
- Splitting `epochs` into a separate JSON-Lines file for very large
  runs.

## Where this is used

Produced by ML training pipelines at the end of a run. Consumed by
training-curve viewers, calibration-analysis tools, and downstream
paper-figure pipelines that render headline performance numbers.

## Example

Skeleton of a complete run.json:

```json
{
  "schema_version": "1.0",
  "created_utc": "2026-06-11T22:00:00Z",
  "run": {
    "run_id": "v1_baseline",
    "git_sha": "abc1234",
    "host": "danielk-desktop",
    "model_version": "mobilevit1d-v1"
  },
  "config": {
    "model": {"width_multiplier": 0.5, "num_classes": 1},
    "data": {"bank_path": "banks/hybrid_v1.h5"},
    "training": {"epochs": 60, "batch_size": 32, "optimizer": "adamw"},
    "eval": {"select_metric": "auroc", "decision_threshold": 0.5}
  },
  "epochs": [
    {
      "epoch": 1,
      "lr": 1e-3,
      "train_loss": 0.5,
      "val_loss": 0.45,
      "epoch_seconds": 12.3,
      "val_metrics": {"auroc": 0.85, "accuracy": 0.80},
      "val_reliability": [
        {"lo": 0.0, "hi": 0.1, "count": 12, "confidence": 0.05, "accuracy": 0.08}
      ]
    }
  ],
  "best": {"epoch": 42, "metric": "auroc", "value": 0.999},
  "test": {
    "loss": 0.05,
    "metrics": {"auroc": 0.92, "accuracy": 0.91, "ece": 0.01},
    "reliability": []
  }
}
```
