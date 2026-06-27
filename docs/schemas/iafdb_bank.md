# iafdb_bank

## What it is

A bank of bipolar EGM segments extracted from PhysioNet's Intracardiac
Atrial Fibrillation Database. One HDF5 file holding calibrated +
band-pass-filtered segments. The bank does NOT carry a `label` column —
labeling is consumer-side policy applied at ClassifierBank conversion
time via a caller-supplied `label_fn`.

The on-disk layout mirrors `synthetic_bank`: bank-level HDF5 root
attrs carry provenance + extraction parameters; a `traces/` group
holds per-trace columns aligned along a first dimension N.

Schema version: `1.2` (plain X.Y string, matching all other schemas in
this package). `1.2` added the optional `bank_id` stable-artifact
identifier (cross-artifact linkage, egm-contracts v0.5.0); the field is
optional so older banks remain valid. `1.1` was a minor bump that added a
`"none"` value to the `threshold_mode` enum and made `threshold_value`
nullable. This enables the unfiltered-export path — every windowed segment
is retained with no healthy-selection threshold applied. Useful for
pretraining banks where label semantics don't gate selection. `1.0` files
remain valid; these are additive changes.

## Why it exists

This is the source of real (in vivo) data for the project. IAFDB has
no per-segment labels — only patient-level AF diagnosis. The producer
(iafdb-pipeline) writes a bank of calibrated, band-passed, threshold-
selected segments. A downstream consumer decides what label semantics
attach to a given bank; that decision lives in the converter call when
the bank is turned into a ClassifierBank, not in this schema.

R-wave-anchored calibration produces calibrated millivolt amplitudes
from raw ADC counts, and the configured threshold strategy (absolute
or per-record percentile) selects segments that pass.

## What gets stored

Bank-level root attrs (HDF5):

- `schema_version`, `created_utc`, `source`
- `bank_id` — optional stable artifact id (since 1.2); pattern defined once in `common.schema.json`. Absent on legacy banks.
- `fs_hz` (1000.0), `trace_duration_ms`, `window_ms`, `window_samples`, `hop_ms`
- `calibration_method` (= "r_wave_anchoring"), `calibration_target_qrs_pp_mv`
- `threshold_mode` ("absolute" | "percentile" | "none" since 1.1), `threshold_value` (nullable since 1.1, when `threshold_mode = "none"`)
- `band_hz` (two-element [low, high] in Hz)
- `source_records` (vlen-UTF-8 string array; contributing IAFDB records)

Per-trace columns under `traces/`:

- `signal` (N, window_samples) float32 — calibrated + band-pass-filtered
- `patient_id` (N,) UTF-8 — IAFDB patient id ("iaf1".."iaf8")
- `source_record` (N,) UTF-8 — record name (e.g. "iaf1_afw")
- `source_channel` (N,) UTF-8 — bipolar pair (e.g. "CS12")
- `start_sample` (N,) int64 — offset in source record
- `peak_to_peak_mv` (N,) float32 — calibrated p-p amplitude that passed the threshold
- `calibration_scalar` (N,) float32 — per-patient calibration scalar

No `label` column — labeling happens at ClassifierBank conversion time.

## Producer contract

The iafdb-pipeline producer is responsible for:

- Calibrating raw ADC counts to mV via R-wave anchoring.
- Band-passing the calibrated signal at the recorded `band_hz`.
- Segmenting calibrated traces by sliding window.
- Applying the threshold strategy to select segments. As of `1.1`,
  `threshold_mode = "none"` is the documented "no filter" path: every
  windowed segment is retained, and the producer writes `null` for
  `threshold_value`.
- Writing the resulting bank with the required attrs + per-trace columns.

What the bank's segments represent (healthy vs fibrotic vs mixed) is
documented downstream by the consumer that interprets the bank, not
encoded in this schema.

## Cross-field invariant

`window_samples == round(window_ms * 1e-3 * fs_hz)`. The validator
enforces this since JSON Schema can't express it directly.
