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

Schema versions: `1.3` and `1.4` — both accepted on read; new banks are
stamped `1.4`. (Plain X.Y strings, matching all other schemas in this
package.) `1.4` widened `calibration_method` to admit `"none"`, so a bank
extracted without amplitude calibration can say so; see below for why that
couldn't wait. `1.3` added two optional fields — the `run_record_path`
sidecar pointer and the per-trace `activation_position` (egm-contracts
v0.6.0); both are optional, so banks written before them stay valid.
`1.2` added the optional `bank_id` stable-artifact
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

R-wave anchoring — scaling EGM amplitude so a paired surface-ECG QRS hits
a target peak-to-peak value — converts raw ADC counts into millivolts, and
the configured threshold strategy (absolute or per-record percentile)
selects the segments that pass.

### Why `"none"` exists (1.4)

Calibration used to be mandatory in the schema, not just in practice:
`calibration_method` was an enum with exactly one member. That was fine
while every bank was anchored, and became a problem the moment one wasn't
— because the only value that validated **asserted that a calibration step
had run**. A bank extracted without anchoring could not describe itself
truthfully; it could only make a false claim or be unwritable.

That distinction is why this shipped as a point release rather than
waiting: this project sentinels fields that would merely be *unused*
(`peak_to_peak_mv`, `hop_ms`), but a field that would be *untrue* gets
fixed. The wider context is that surface-QRS-referenced scaling is not a
standard intracardiac practice, so which method is right is a scientific
question settled per corpus — `"none"` makes "we didn't calibrate" a
statement the format can carry, rather than a gap.

## What gets stored

Bank-level root attrs (HDF5):

- `schema_version`, `created_utc`, `source`
- `bank_id` — optional stable artifact id (since 1.2); pattern defined once in `common.schema.json`. Absent on legacy banks.
- `run_record_path` — optional relative path to a sibling JSON run record of per-record extraction diagnostics (since 1.3), e.g. `iafdb_healthy_v1_run_record.json`. Same sibling convention as `noise_bank` ↔ `noise_bank_run_record`. Absence means "no sidecar", not an error. The record's own schema isn't formalized yet, so this is a path rather than an embedded object.
- `fs_hz` (1000.0), `trace_duration_ms`, `window_ms`, `window_samples`, `hop_ms`
- `calibration_method` — `"r_wave_anchoring"` or `"none"` (since 1.4).
  `"none"` means no amplitude calibration was applied and the stored signal is
  in the source dataset's raw units.
- `calibration_target_qrs_pp_mv` — the target amplitude calibrated against.
  **Required and strictly positive even when `calibration_method` is
  `"none"`**, where producers write `+inf`
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
- `activation_position` (N,) float32 — **optional** (since 1.3); the realized
  activation position within the window as a `[0,1]` fraction, written by the
  activation-aware splitter. It's what the splitter *placed*, not a
  measurement taken from the waveform afterwards — a consumer wanting the
  measured dV/dt-max position computes that with egm-features. Optional
  **permanently**, not just during the migration: it's absent on
  sliding-window banks (no anchor exists), on multi-beat traces (several
  activations, so no single position describes the trace), and on
  activation-mode banks written before the splitter shipped. Treat absence as
  "unknown" — never as 0.0, which is a legitimate value meaning the activation
  sits on the first sample, so defaulting would invent a spike at the bottom
  of the distribution.
  `synthetic_bank` carries the identical field, which is what lets the two
  corpora's position distributions be compared stored-vs-stored.

No `label` column — labeling happens at ClassifierBank conversion time.

## Producer contract

The iafdb-pipeline producer is responsible for:

- Choosing a calibration method and recording it honestly. R-wave anchoring
  converts raw ADC counts to mV; `"none"` (since 1.4) leaves the signal in
  the source dataset's raw units. In `"none"` mode the producer still writes
  `calibration_target_qrs_pp_mv`, as `+inf` — the same
  not-applicable-in-this-mode sentinel `peak_to_peak_mv` and `hop_ms` use.
  Downstream amplitude comparisons across banks are only meaningful between
  banks that share a method.
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
