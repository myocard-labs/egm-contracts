# egm_class_model_metadata

## What it is

A **deployment-time sidecar** that pairs with a model artifact
(typically an ONNX file or a runtime-specific engine). Carries
everything the runtime needs that is *not* encoded in the model
file itself: preprocessing constants, normalization parameters,
decision threshold, model artifact hash, training provenance.

Written as a JSON file next to the model artifact (e.g.,
`<model>.model_metadata.json` alongside `<model>.onnx`). Read by
both Python (training-eval parity checks) and C++ (inference
runtimes).

Schema version: `1.2`. `1.2` added the optional `model_id` stable-artifact
identifier (the model's own id, which a run.json's `produced_model_id`
points at). The model→run link is intentionally *not* stored here — this
file carries only what a deployed model needs.

## Why it exists

Model files encode tensor shapes, dtypes, and the computation
graph — but not what to do with input before sending it to the
model, or what to do with output after. Specifically:

- The model expects preprocessed signal (band-passed, calibrated,
  normalized) at a fixed sample rate. Those preprocessing
  constants must match the training-time values exactly, or the
  model degrades silently.
- The output is a raw logit; the consumer needs a decision
  threshold and the class labels.
- For deployment, the consumer also needs a content hash to
  detect tampering and a pointer back to the training run that
  produced this model.

All of that information has to ride with the model file as a
parsed-once sidecar.

This is the schema that ties Python training to C++ inference. Get
it right and the runtime side becomes a straightforward "load
JSON, validate, apply, dispatch."

## Field walkthrough

### Top-level

- **`schema_version`** — `"1.2"`.
- **`created_utc`** — ISO-8601 timestamp at model-export time.
- **`model_id`** — *optional, since 1.2.* Stable cross-artifact id of
  THIS model (e.g. `model_egm_classifier_v1_5_2026-06-25`); pattern
  defined once in `common.schema.json`. This is what a run.json's
  `produced_model_id` points at — the model→run link is recorded from the
  run side, not duplicated here.
- **`model_artifact`** — pointer to the model file this sidecar
  pairs with.
- **`input`** — expected input tensor spec.
- **`output`** — expected output tensor spec.
- **`preprocessing`** — signal-conditioning constants.
- **`decision`** — decision-rule constants.
- **`training_provenance`** — where the model came from.

### model_artifact

- **`filename`** — relative to the sidecar's directory (e.g.,
  `"best.onnx"`).
- **`framework`** — `"onnx"`, `"tensorrt"`, or `"pytorch"`.
- **`sha256`** — content hash of the artifact (64 hex chars).
  Optional but strongly recommended for any deployed model.
- **`size_bytes`** — file size in bytes. Optional.

### input / output

Both have the same shape:

- **`name`** — tensor name as encoded in the model artifact.
- **`shape`** — array of integers (fixed dims) or strings (`"?"`
  for dynamic dims like the batch axis). Example: `["?", 1, 512]`.
- **`dtype`** — `"float32"` or `"float16"` (the shared `Dtype`
  $def). Half-precision is for quantized runtime engines.

`output` additionally carries:

- **`semantics`** — `"binary_logit"`, `"binary_probability"`,
  `"multiclass_logits"`, or `"multiclass_probabilities"`. Tells
  the consumer whether to apply sigmoid/softmax.

### preprocessing

Constants the runtime applies before inference, in the order
listed:

- **`expected_fs_hz`** — sampling rate the model was trained at.
  Inputs at a different rate must be resampled before invocation.
- **`expected_trace_samples`** — per-trace length in samples.
  Must equal the time-axis dimension in `input.shape`.
- **`bandpass_hz`** — `[low, high]` band-pass filter edges in Hz.
- **`normalization`** — per-trace signal normalization. Object:
  - `scheme` — one of:
    - `"zscore"` — subtract the trace's mean and divide by its
      standard deviation. Suits approximately-Gaussian signals and
      is what the v1 classifier trains with.
    - `"zero2one"` — min-max rescale each trace so its minimum
      maps to 0.0 and its maximum to 1.0. Useful when amplitude
      bounds are meaningful and the distribution is non-Gaussian.
    - `"none"` — pass the raw trace through unchanged. Use only
      when the producer pipeline has already normalized upstream.

  All three schemes are computed per-trace from each trace's own
  samples; there are no global or per-channel statistics in this
  schema. Any sensor- or hardware-level normalization (e.g. ADC-gain
  correction) is expected to have happened upstream of this contract.

### decision

- **`threshold`** — decision threshold applied to the positive-class
  probability. 0.5 by default.
- **`class_labels`** — human-readable labels in output-index order
  (e.g., `["healthy", "fibrotic"]` for the binary case).

### training_provenance

Well-known keys (producer should write all of these):

- `run_id` — identifier into the run record that documents the
  training.
- `run_json_path` — path to that run.json.
- `training_bank_path` — path to the bank used for training.
- `training_bank_schema_version` — schema version of that bank.
- `git_sha` — source-repo state at training time.

Additional producer-defined keys allowed.

## Versioning

Currently `1.2` (`1.2` added the optional `model_id`). Bump triggers:

- Adding required preprocessing steps (e.g., a notch filter).
- Multi-class extensions to `decision` (per-class thresholds).
- Multi-input models needing an `inputs[]` array rather than a
  single `input` object.
- Adding new entries to the `normalization.scheme` enum, or
  re-introducing per-channel/global normalization parameters for
  model topologies that need them.

Per-version change history lives in
[`project/schema_evolution.md`](../../project/schema_evolution.md)
under "Schema change log" — see that file for what changed when
and why.

## Where this is used

Produced by model-export pipelines that emit ONNX (or
runtime-specific) artifacts. Consumed by:

- Python inference loaders for training-eval parity checks.
- C++ inference runtimes that validate the artifact, apply
  preprocessing, dispatch, then apply the decision threshold.

## Example

```json
{
  "schema_version": "1.2",
  "created_utc": "2026-06-11T22:30:00Z",
  "model_id": "model_egm_classifier_v1_baseline_2026-06-11",
  "model_artifact": {
    "filename": "best.onnx",
    "framework": "onnx",
    "sha256": "abc123abc123abc123abc123abc123abc123abc123abc123abc123abc123abcd",
    "size_bytes": 2100000
  },
  "input": {
    "name": "signal",
    "shape": ["?", 1, 512],
    "dtype": "float32"
  },
  "output": {
    "name": "logit",
    "shape": ["?", 1],
    "dtype": "float32",
    "semantics": "binary_logit"
  },
  "preprocessing": {
    "expected_fs_hz": 1000.0,
    "expected_trace_samples": 512,
    "bandpass_hz": [30.0, 300.0],
    "normalization": {
      "scheme": "zscore"
    }
  },
  "decision": {
    "threshold": 0.5,
    "class_labels": ["healthy", "fibrotic"]
  },
  "training_provenance": {
    "run_id": "v1_baseline",
    "run_json_path": "checkpoints/v1_baseline/run.json",
    "training_bank_path": "banks/hybrid_v1.h5",
    "training_bank_schema_version": "1.0",
    "git_sha": "abc1234"
  }
}
```
