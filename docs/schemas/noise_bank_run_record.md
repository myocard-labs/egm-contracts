# noise_bank_run_record

## What it is

A **provenance sidecar** for a NoiseBank HDF5 file: how the noise
segments were extracted, what their calibration scheme was, and the
per-trace audit data needed to reproduce or interrogate the bank.
Written as a JSON file alongside the bank.

Schema version: `1.1`. `1.1` added the optional `bank_id` stable-artifact
identifier for the noise bank (cross-artifact linkage, egm-contracts
v0.5.0); the field is optional so older records remain valid.

## Why it exists

The companion `noise_bank` schema is intentionally minimal — it
carries only what the synthetic-EGM mixer actually consumes
(signal, source_record, source_channel, fs_hz). Everything else about
*how* the bank was built lives here. The split keeps two concerns
separate:

- The bank is the **data**: opened by the mixer, the only thing it
  needs at run-time.
- The run record is the **methods**: opened by debuggers, audit
  scripts, the white paper's methods section, and (in the future) a
  v2 mixer that wants unit-aware mixing.

The pattern mirrors `metrics.csv` (data) + `run.json` (methods) in
egm-classifier. The two files are paired by convention — same
directory, matching name stem — not by an explicit cross-reference
inside either schema.

## File pairing convention

```
banks/
├── iafdb_noise_v1.h5                   ← the bank (noise_bank schema)
└── iafdb_noise_v1_run_record.json      ← this schema
```

Producers MUST write both files in the same run. Mixers ignore the
sidecar; auditing tools open both.

## What gets stored

Top-level fields:

- `schema_version`, `created_utc`
- `bank_id` — *optional, since 1.1.* Stable artifact id for the noise
  bank this sidecar describes (e.g. `nbank_iafdb_2026-06-15`); pattern
  defined once in `common.schema.json`. The design puts the noise bank's
  stable id on this sidecar rather than on the HDF5 bank.
- `source` — identical to the sibling bank's `source` field
- `description` — free-form note about the run
- `fs_hz` — mirrors the bank's `fs_hz` so the record stands alone as
  documentation

Three structured sub-objects:

- **`windowing`** — sliding-window extraction parameters: `window_ms`,
  `window_samples`, `hop_ms`
- **`calibration`** — `method` (open string: `"r_wave_anchoring"`,
  `"none"`, `"fixed_gain"`, etc.) and `target_qrs_pp_mv` (nullable
  when the method has no target)
- **`selection`** — `threshold_mode` (`"absolute"` or `"percentile"`)
  and `threshold_value`

Plus one flat field:

- `source_records` — the list of upstream record names that
  contributed at least one segment

And optionally:

- **`per_trace_provenance`** — parallel arrays aligned to the bank's
  traces (index `i` here corresponds to bank traces row `i`). Each
  array has length N matching the bank's trace count. Producers
  SHOULD write this for any bank intended for paper-citable use;
  smaller test fixtures may omit it. Contains: `patient_id`,
  `start_sample`, `peak_to_peak_mv`, `calibration_scalar`.

## Producer contract

The producer is responsible for:

- Stamping `source` identically in the bank and the record.
- Stamping `fs_hz` identically in the bank and the record.
- Stamping `calibration.method` honestly. `"none"` is a valid value;
  when set, `per_trace_provenance.peak_to_peak_mv` is in raw signal
  units rather than mV.
- Keeping `per_trace_provenance` arrays aligned to the bank's `traces`
  ordering. Producers that skip the per-trace block forfeit
  patient-aware sampling and mV-aware mixing for downstream consumers
  of this bank.

## Cross-field invariant

`windowing.window_samples == round(windowing.window_ms * 1e-3 * fs_hz)`.
The validator enforces this since JSON Schema can't express it directly.

## Threshold semantics

- `"absolute"` — segments kept where peak-to-peak ≤ `threshold_value` mV.
  Requires `calibration.method` ≠ `"none"` for the mV interpretation to
  be meaningful.
- `"percentile"` — segments kept in the bottom `threshold_value`% of the
  pooled per-record peak-to-peak distribution. Scale-invariant so it
  works on raw signal too.
