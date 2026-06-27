# synthetic_bank

## What it is

A bank of labeled synthetic intracardiac EGM traces. One HDF5 file
holding many simulated bipolar EGM waveforms with continuous
fibrosis-density labels plus the simulation provenance needed to
reproduce them.

The on-disk layout: bank-level HDF5 root attrs carry the simulation
metadata; a `traces/` group holds the per-trace columns. All columns
inside `traces/` share a first dimension N (the trace count) and are
aligned.

Schema version: `1.1`. `1.1` added the optional `bank_id` stable-artifact
identifier (cross-artifact linkage, egm-contracts v0.5.0); `1.0` banks
remain valid because the field is optional.

## Why it exists

This is the primary training artifact for a fibrosis-detection
classifier. The simulator emits many traces per simulation (one per
electrode pair in an electrode grid), and each trace carries: the
waveform itself, the continuous fibrosis-density label, the spatial
pair index, and enough provenance (seed, electrode height, stim edge,
noise mixing parameters) to either reproduce the simulation or to
investigate per-axis shortcut features in a trained classifier.

The continuous-density-label choice is load-bearing: storing the
realized density as a float lets downstream training threshold it into
binary / multi-class / regression targets without regenerating data.

## Field walkthrough

### Bank-level (HDF5 root attrs)

- **`schema_version`** — schema version constant, currently
  `"1.1"`.
- **`created_utc`** — ISO-8601 timestamp at write time.
- **`bank_id`** — *optional, since 1.1.* Stable cross-artifact
  identifier for this bank (e.g.
  `tbank_synthetic_courtemanche_v1_5_2026-06-25`). The pattern is defined
  once in `common.schema.json` and referenced here. Absent on legacy
  banks; egm-data stamps it on every new bank.
- **`description`** — free-text human-readable label for the bank.
- **`fs_hz`** — sampling rate in Hz.
- **`trace_duration_ms`** — per-trace duration in milliseconds.
- **`simulator`** / **`cell_model`** — backend + cellular EP model
  identifiers (e.g. `"finitewave"` + `"aliev_panfilov"`).
- **`patch_size_mm`**, **`patch_dr_mm`**, **`ap_time_unit_ms`** —
  tissue geometry and discretization parameters.
- **`fibrosis_strategy_name`** — identifier for the substrate
  generation strategy (e.g. `"uniform_random"`).
- **`fibrosis_params`**, **`electrode_config`**, **`mixer_config`**,
  **`experiment_config`** — four JSON-encoded sub-config objects. The
  JSON Schema describes their full structure; HDF5 stores them as
  JSON-stringified attrs (`fibrosis_params_json`, etc.). The
  validator/writer handles the stringification so the schema stays
  declarative.
- **`noise_bank_source`** — identifier of the real-noise bank that the
  mixer drew from (when noise mixing is enabled).

### Per-trace columns (HDF5 `traces/` group)

All columns are aligned, length N:

- **`signal`** — `(N, T)` float32, the bipolar EGM waveform. T =
  `trace_duration_ms * 1e-3 * fs_hz`.
- **`simulation_id`** — int64 patient/simulation identifier. The
  patient-aware split unit: all traces from the same simulation go to
  the same split to avoid leakage.
- **`pair_index`**, **`electrode_row`** — int64 indices identifying
  which bipolar pair within the electrode grid produced this trace.
- **`fibrosis_density`** — float64 requested density (0.0 = healthy).
  The label.
- **`fibrosis_density_realized`** — float64 actual fraction of
  non-conductive nodes after the substrate draw. Differs from
  `fibrosis_density` due to grid-size discretization.
- **`electrode_height_mm`** — float64 height above the tissue surface
  for this electrode pair.
- **`seed`** — int64 RNG seed used for this simulation.
- **`snr_db`** — float64 target SNR at which real noise was mixed in;
  NaN when the mixer was off.
- **`stim_edge`** — UTF-8 enum (`top` / `bottom` / `left` / `right`):
  the edge of the patch from which the planar activation wave
  originated. This field is Phase-1-specific and will be replaced by a
  richer `stimulation` object in a future schema version (see
  `project/known_issues.md`).
- **`noise_record`**, **`noise_channel`** — UTF-8 identifiers of the
  noise segment that was mixed in (`""` when mixer off).

## Versioning

Currently `1.1` (`1.1` added the optional `bank_id`). Known triggers for
future bumps:

- The `stim_edge` enum being replaced by a richer `stimulation` object
  to support point-source or S1-S2 protocols.
- Switching to a different cell electrophysiology model that brings
  new per-trace columns (e.g., action-potential duration).
- Adding new per-trace columns required by future simulator features per the
  evolution roadmap.

## Where this is used

The producer is a synthetic-data generation pipeline that wraps a
cardiac electrophysiology simulator. Consumers include training
pipelines, model-evaluation tools, and inspection GUIs that need to
walk individual traces.

## Example

A minimal valid bank payload:

```json
{
  "schema_version": "1.1",
  "created_utc": "2026-06-15T20:30:00Z",
  "bank_id": "tbank_synthetic_courtemanche_v1_5_2026-06-25",
  "description": "Phase 1 bank — 100 sims × 20 traces/sim",
  "fs_hz": 1000.0,
  "trace_duration_ms": 200.0,
  "simulator": "finitewave",
  "cell_model": "aliev_panfilov",
  "patch_size_mm": 40.0,
  "patch_dr_mm": 0.25,
  "ap_time_unit_ms": 1.0,
  "fibrosis_strategy_name": "uniform_random",
  "fibrosis_params": {"density_range": [0.0, 0.5]},
  "electrode_config": {"grid_shape": [5, 5], "pair_spacing_mm": 2.0},
  "mixer_config": {"enabled": true, "snr_db_range": [10, 25]},
  "experiment_config": {"n_simulations": 100},
  "noise_bank_source": "iafdb_noise_v1.h5",
  "traces": {
    "signal": [[0.0, 0.1, "..."]],
    "simulation_id": [0],
    "pair_index": [0],
    "electrode_row": [0],
    "fibrosis_density": [0.3],
    "fibrosis_density_realized": [0.29],
    "electrode_height_mm": [0.5],
    "seed": [42],
    "snr_db": [20.0],
    "stim_edge": ["top"],
    "noise_record": ["iaf1_afw"],
    "noise_channel": ["CS12"]
  }
}
```
