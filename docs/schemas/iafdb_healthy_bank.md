# iafdb_healthy_bank

## What it is

A bank of healthy bipolar EGM segments extracted from PhysioNet's
Intracardiac Atrial Fibrillation Database. One HDF5 file holding
calibrated + band-pass-filtered segments, all labeled "healthy" by
construction.

The on-disk layout mirrors `synthetic_bank`: bank-level HDF5 root
attrs carry provenance + extraction parameters; a `traces/` group
holds per-trace columns aligned along a first dimension N.

Schema version: `1.0`.
(plain X.Y string, matching all other schemas in this package.)
with the existing on-disk attr name.

## Why it exists

This is the source of real (in vivo) data for the project. IAFDB has
no per-segment "fibrotic" labels — only patient-level AF diagnosis.
The pragmatic move (which mirrors prior cardiac-ML work) is to use
IAFDB for the healthy negative class — extracting traces that pass a
calibrated voltage threshold consistent with healthy atrial tissue
per the clinical literature.

"Healthy" here means: passed the calibrated peak-to-peak voltage
threshold for healthy atrial tissue. R-wave-anchored calibration
produces calibrated millivolt amplitudes from raw ADC counts, and the
configured threshold strategy (absolute or per-record percentile)
selects qualifying segments.

## Field walkthrough

### Bank-level (HDF5 root attrs)

- **`schema_version`** — currently `"1.0"`.
- **`created_utc`** — ISO-8601 timestamp at write time.
- **`source`** — provenance tag for the upstream dataset, currently
  `"iafdb v1.0.0"`.
- **`fs_hz`** — fixed at 1000.0 (IAFDB's native rate).
- **`trace_duration_ms`** — segment length in milliseconds (equals
  `window_ms`).
- **`calibration_method`** — how per-record amplitude calibration was
  computed. Currently only `"r_wave_anchoring"` is supported.
- **`calibration_target_qrs_pp_mv`** — target peak-to-peak QRS
  amplitude (mV) that the calibration anchors against.
- **`threshold_mode`** + **`threshold_value`** — the threshold
  strategy that selected qualifying segments. `"absolute"` + a value
  in mV; or `"percentile"` + a value in (0, 100).
- **`band_hz`** — `[low, high]` band-pass filter edges in Hz.
- **`window_ms`** + **`window_samples`** — sliding-window length in
  the two units. Both are stored even though
  `window_samples = round(window_ms * 1e-3 * fs_hz)`; storing both
  lets readers index without doing the math, and the validator
  enforces consistency.
- **`hop_ms`** — stride between adjacent windows. Additive: not in
  the original format-version-1 spec but recorded for reproducibility;
  readers MAY ignore it.
- **`source_records`** — array of record names that contributed at
  least one segment.

### Per-trace columns (HDF5 `traces/` group)

- **`signal`** — `(N, window_samples)` float32. Calibrated +
  band-pass-filtered bipolar EGM segments.
- **`label`** — `(N,)` int64. All zeros (known healthy). Stored
  explicitly so polymorphic loaders can treat this bank the same way
  as a synthetic bank.
- **`patient_id`** — UTF-8 string, IAFDB patient identifier (e.g.,
  `"iaf1"`).
- **`source_record`** — UTF-8 IAFDB record name (e.g., `"iaf1_afw"`).
- **`source_channel`** — UTF-8 bipolar channel name (e.g., `"CS12"`).
- **`start_sample`** — int64 sample offset of the segment into the
  source record. Combined with `source_record` + `window_samples`,
  uniquely identifies the segment in the raw data.
- **`peak_to_peak_mv`** — float32 calibrated peak-to-peak amplitude
  (mV) that passed the threshold check. Real-millivolt interpretation.
- **`calibration_scalar`** — float32 per-patient scalar applied to
  this segment: `signal_mV = signal_raw_adc * calibration_scalar`.
  Stored per-segment so consumers can sanity-check.

## Versioning

Currently `1.0`. Known triggers for future bumps:

- Adding new calibration methods (changes that alter
  `peak_to_peak_mv` interpretation).
- Adding columns to support multi-band or multi-source variants per the
  evolution roadmap.
- Multi-band or multi-patient variants.

## Where this is used

The producer is a data-extraction pipeline that ingests raw
PhysioNet records, calibrates per record, segments, and exports the
bank. Consumers include training pipelines (for the healthy negative
class), inspection GUIs, and inference benchmarks.

## Example

A minimal valid bank payload:

```json
{
  "schema_version": "1.0",
  "created_utc": "2026-06-12T18:30:00Z",
  "source": "iafdb v1.0.0",
  "fs_hz": 1000.0,
  "trace_duration_ms": 512.0,
  "calibration_method": "r_wave_anchoring",
  "calibration_target_qrs_pp_mv": 1.0,
  "threshold_mode": "absolute",
  "threshold_value": 0.5,
  "band_hz": [30.0, 300.0],
  "window_ms": 512.0,
  "window_samples": 512,
  "hop_ms": 256.0,
  "source_records": ["iaf1_afw", "iaf2_afw"],
  "traces": {
    "signal": [[0.0, 0.05, "..."]],
    "label": [0],
    "patient_id": ["iaf1"],
    "source_record": ["iaf1_afw"],
    "source_channel": ["CS12"],
    "start_sample": [12000],
    "peak_to_peak_mv": [0.42],
    "calibration_scalar": [0.0035]
  }
}
```
