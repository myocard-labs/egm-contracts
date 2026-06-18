# noise_bank

## What it is

A bank of **low-amplitude (quiet) bipolar EGM segments** used as additive
noise input by the synthetic-EGM mixer. One HDF5 file holding only what
the mixer actually consumes: the signal waveform plus per-trace
identifiers that get propagated onto each hybrid output trace.

Schema version: `1.0`.

## The two-file design

The noise_bank schema is **intentionally minimal**. The mixer's math is:

```
mixed = sig_bp + alpha * noise   where alpha = sqrt(P_s / (10^(SNR/10) * P_n))
```

The only field the math reads is `traces.signal`. The mixer code also
reads `fs_hz` (sample-rate sanity check) and copies `source_record` /
`source_channel` onto each output trace as audit identifiers. That's
the whole working set.

Everything else about how the bank was built — calibration scheme,
threshold strategy, filter band, sliding-window parameters, per-trace
provenance — lives in a sibling **`noise_bank_run_record.json`** file
with its own schema (see [noise_bank_run_record](noise_bank_run_record.md)).
This mirrors the existing `metrics.csv` + `run.json` pattern used by
egm-classifier: data and methods stored in the file format that suits
each, paired by convention rather than enforced cross-reference.

Producers write both files together; the mixer only opens the bank;
debugging, reproducibility audits, and the white paper's methods
section open the JSON.

The convention is matching name stems in the same directory:

```
banks/
├── iafdb_noise_v1.h5                   ← the bank (this schema)
└── iafdb_noise_v1_run_record.json      ← the provenance sidecar
```

## Why generic

Noise extraction is the same operation on any signal — slide a window,
compute peak-to-peak, keep the quiet ones. The schema does not
constrain `source`, `source_record`, or `source_channel` patterns to
IAFDB's conventions; any real EGM dataset can produce a noise_bank.
Source-specific validation (e.g. "is 'iaf9' a real IAFDB patient?")
belongs in the producer, not the schema.

## What gets stored

Bank-level root attrs (HDF5):

- `schema_version`, `created_utc`
- `source` — free-form provenance tag for the upstream dataset (e.g.
  `"iafdb v1.0.0"`)
- `fs_hz` — sampling rate; the mixer asserts this matches the
  synthetic side's fs

Per-trace columns under `traces/`:

- `signal` (N, T) float32 — the noise waveform itself; the only column
  the mixer math reads
- `source_record` (N,) UTF-8 — source-dataset record identifier;
  propagated to each hybrid output trace as `noise_record`
- `source_channel` (N,) UTF-8 — bipolar channel within the source
  record; propagated to each hybrid output trace as `noise_channel`

## Producer contract

The producer is responsible for:

- Writing the bank in this schema with whatever signal data it has.
- **Writing the sibling `noise_bank_run_record.json` for the same run.**
  See that schema for the required provenance fields. The bank alone
  is consumable by the mixer; the sibling is what makes the bank
  reproducible and paper-citable.
- Stamping `source` identically in both files.

## What's NOT in this schema (and where to find it)

| Field | Lives in |
|---|---|
| calibration method + target | `noise_bank_run_record.calibration` |
| threshold mode + value | `noise_bank_run_record.selection` |
| band_hz, window_ms, hop_ms | `noise_bank_run_record.windowing`, `band_hz` |
| source_records (which records contributed) | `noise_bank_run_record.source_records` |
| patient_id, start_sample, peak_to_peak_mv, calibration_scalar | `noise_bank_run_record.per_trace_provenance` |
