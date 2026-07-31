# synthetic_bank

## What it is

A bank of **simulated bipolar EGM traces**, optionally mixed with real
noise, produced by the synthetic-EGM pipeline. One HDF5 file holds the
waveforms, the configuration that generated them, and the labels derived
from that configuration.

Schema version: `2.0`.

A 2.0 file has three levels:

```
bank.h5
├── root attrs        ← what the whole bank is: id, rate, duration, θ-spec
├── simulations/      ← one row per simulation: how it was generated
└── traces/           ← one row per bipolar pair: the signal + its label
```

## Why it exists

The classifier trains on labelled EGM traces, and real intracardiac data
carries no fibrosis label — so the training set is simulated, where the
substrate is known by construction. The bank is the handoff: the
producer writes it, egm-data reads it, the classifier consumes traces
from it, and the analysis tooling reads back the parameters that made
each trace.

That last consumer is why the bank stores configuration at all. A trace
on its own is a waveform; what makes it scientifically useful is knowing
the density, cell model, electrode height and stimulus that produced it.

## What changed in 2.0, and why

**1.1 stored generation parameters as flat per-trace columns:**
`fibrosis_density`, `fibrosis_density_realized`, `stim_edge`,
`electrode_row`, `electrode_height_mm`, `seed`.

Each of those columns silently encoded a Phase-1 assumption:

- `fibrosis_density` — a single scalar — presumes the substrate is a
  uniform random draw. It says almost nothing about a patchy or
  interstitial substrate, and nothing at all about a heterogeneous one.
- `stim_edge`, an enum of four edge names, presumes a planar wave on a
  2D patch. A point source needs a coordinate; a paced protocol needs
  timings; a 3D geometry needs three axes.
- `electrode_height_mm` presumes a flat grid at one height.

So every new cell model, substrate type or stimulus protocol forced
either **new trace columns** or a **silent change of meaning** in
existing ones — and the second is worse, because a bank would keep
validating while meaning something different.

They were also **per-trace copies of per-simulation facts**. A
simulation has one substrate and one stimulus; storing them once per
trace repeated the same value twenty times and invited the reading that
traces from one simulation differ in those respects.

**2.0 reorganizes by the generation functions that don't change** —
geometry, cell model, substrate, activation, electrodes, backend, label
policy. Each is a typed, `type`-discriminated object stored once per
simulation. A new substrate type or a 3D geometry becomes a new
*variant* of its function, extending the union without touching the
trace columns or the bank's top-level shape.

**There is no migration path.** A 1.1 bank is refused by a 2.0 reader
rather than partially read — a partial read would silently drop the
generation config, which is the thing worth keeping. This was affordable
precisely because no released work depended on a 1.1 bank and banks
regenerate from config in hours; the same choice after publication would
not have been available.

## Field walkthrough

### Bank-level (HDF5 root attrs)

- `schema_version` — `"2.0"`.
- `created_utc` — ISO-8601 timestamp at write time.
- `bank_id` — optional stable artifact id; pattern defined once in
  `common.schema.json`. Optional in-schema, stamped on every new bank by
  egm-data.
- `description` — free text: what this bank is for.
- `fs_hz` — sample rate of the stored traces. 1000 Hz in Phase 1, to
  match IAFDB; the two corpora must share a rate for lag-based features
  to be comparable at all.
- `trace_duration_ms` — per-trace duration. Coupled across the pipeline:
  the same value drives the simulator's capture window, the IAFDB
  splitter and the classifier's input length.
- `noise_bank_source` — which noise bank the mixer drew from; empty when
  the bank is clean.
- `generation_params` — the **θ-spec** (stored JSON-encoded as
  `generation_params_json`): which knobs this bank's sweep varied and in
  which structural regime. See [generation_params](generation_params.md).
  Required even for an unswept bank, where it records the regime with an
  empty knob list — "nothing varied" is worth stating explicitly.

### Per-simulation columns (HDF5 `simulations/` group)

M rows, one per simulation. `simulation_id` and `seed` are plain integer
columns; the rest are stored as JSON strings (`geometry_json`,
`activation_json`, …) and decode to the typed objects defined in
[simulation_config](simulation_config.md).

- `simulation_id` — the simulation's identifier, unique in the bank, and
  the join key traces reference.
- `seed` — the RNG seed that drove this simulation's substrate draw and
  height sample.
- `geometry` — the tissue domain.
- `cell_model` — the electrophysiology model **and its parameters**. 1.1
  had only a bank-level model *name*, which couldn't carry parameters at
  all.
- `substrate` — the **requested** substrate pattern.
- `substrate_summary` — what the draw **realized** (e.g. realized
  density). Kept separate because the two genuinely differ through grid
  discretization, and the label is computed from the realized one.
- `activation` — how the wave was initiated.
- `electrodes` — the placement plus the realized per-pair list
  (`pairs`), each entry carrying the row, height and midpoint that 1.1
  repeated per trace.
- `label_policy` — the rule that turned the realized substrate into the
  integer labels this simulation's traces carry.
- `label_names` — `{int: name}`, giving each label value its meaning.

### Per-trace columns (HDF5 `traces/` group)

N rows, one per bipolar pair per simulation.

- `signal` (N, T) float32 — the waveform.
- `simulation_id` — foreign key into `simulations/`. Also the
  patient-aware split unit: traces from one simulation share a
  substrate, so splitting across them leaks.
- `pair_index` — foreign key into that simulation's `electrodes.pairs`.
- `label` — the class label, as a **plain integer**. The polymorphism
  lives entirely in the producer-side policy, so the classifier's input
  contract is an int today, at multiclass severity, and under any future
  label family. Its meaning comes from the simulation's `label_names`.
- `activation_position` — **optional**; the realized `[0,1]` activation
  position when a controlled crop was applied. Absent on Wave-1 banks
  (no crop yet) and on multi-beat traces. Shares its definition with
  `iafdb_bank`'s identical column so synthetic and real position
  distributions compare stored-vs-stored. Absence means *unknown*, never
  0.0.
- `snr_db`, `noise_record`, `noise_channel` — the trace's own noise
  provenance; NaN and empty strings when the mixer was off. Per trace
  because the mixer draws an SNR per trace.

### The two foreign keys

`simulation_id` and `pair_index` are what make the normalization work,
and neither is expressible in JSON Schema — it cannot reference between
two sibling groups. The validator therefore checks the trace →
simulation key directly: an orphan id is a trace whose generation config
can't be recovered, which is exactly the failure the restructure exists
to prevent.

## Versioning

`2.0` is a **major** bump because fields moved rather than being added.
Consumers must refuse a 1.x bank outright.

A minor bump (`2.1`) would cover an additive change — a new optional
column, or a new variant inside one of the per-function unions. Adding a
substrate type or a stimulus protocol is explicitly *not* a bank-schema
change under 2.0; it extends a union in
[simulation_config](simulation_config.md).

## Example

Root attrs (JSON view; on disk these are HDF5 attrs, with
`generation_params` stored as the `generation_params_json` string):

```json
{
  "schema_version": "2.0",
  "created_utc": "2026-07-30T22:00:00Z",
  "bank_id": "tbank_synthetic_courtemanche_v1_5_2026-07-30",
  "description": "100 sims, 20 traces/sim, clean",
  "fs_hz": 1000.0,
  "trace_duration_ms": 192.0,
  "noise_bank_source": "",
  "generation_params": {
    "regime": {
      "geometry": "patch_2d",
      "cell_model": "courtemanche",
      "substrate": "uniform_random_fibrosis"
    },
    "knobs": []
  }
}
```

One row of `simulations/` (each column decoded from its `*_json`
string):

```json
{
  "simulation_id": 0,
  "seed": 42,
  "geometry": {"type": "patch_2d", "size_mm": 40.0, "dr_mm": 0.25},
  "cell_model": {"type": "courtemanche", "params": {"g_CaL_scale": 0.8}},
  "substrate": {"type": "uniform_random_fibrosis", "density": 0.35},
  "substrate_summary": {"realized_density": 0.352},
  "activation": {"type": "planar_edge", "edges": ["top"], "voltage": 1.0},
  "electrodes": {
    "type": "centered_grid_2d",
    "n_rows": 5, "n_cols": 5, "spacing_mm": 2.0, "height_mm": 0.6,
    "pairs": [
      {"pair_index": 0, "electrode_indices": [0, 1], "electrode_row": 0,
       "height_mm": 0.6, "midpoint_mm": [17.0, 16.0]}
    ]
  },
  "backend": {"type": "finitewave", "output_fs_hz": 1000.0, "capture_oversample": 4},
  "label_policy": {"type": "global_density", "thresholds": [0.1]},
  "label_names": {"0": "healthy", "1": "fibrotic"}
}
```

One row of `traces/`:

```json
{
  "signal": [0.01, -0.03],
  "simulation_id": 0,
  "pair_index": 0,
  "label": 1,
  "snr_db": null,
  "noise_record": "",
  "noise_channel": ""
}
```

Reading that trace's generation config means joining on `simulation_id`;
reading its electrode geometry means indexing `electrodes.pairs` by
`pair_index`.
