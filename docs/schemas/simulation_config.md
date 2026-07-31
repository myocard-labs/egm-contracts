# simulation_config

## What it is

The typed description of **how one synthetic simulation was generated**,
organized by generation function: geometry, cell model, substrate,
activation, electrodes, backend, label policy.

Not a document format. Like `common.schema.json`, this file is a library
of shared `$defs` — there is no `simulation_config.json` on disk and no
document validator. `synthetic_bank` `$ref`s these definitions and
stores one JSON-encoded object per column in its `simulations/` group.

## Why it exists

Simulated data is only useful if you can say what produced it, and the
parameters that matter change as the simulator grows. The problem this
schema solves is how to record them without the record needing a
redesign each time.

`synthetic_bank` 1.1 stored them as flat per-trace columns —
`fibrosis_density`, `stim_edge`, `electrode_height_mm` — and each column
baked in an assumption about the Phase-1 setup. Adding a substrate type
or a stimulus protocol meant adding columns or quietly changing what an
existing one meant.

The observation behind 2.0 is that the *parameters* churn but the
*functions* don't. There is always a geometry, always a substrate,
always something that starts the wave. So the schema is organized by
those functions, and each one is a `type`-discriminated union: a new
substrate type is a new variant of `Substrate`, and nothing outside
`Substrate` changes.

Each object mirrors the corresponding strategy Protocol in
synthetic-egm-pipeline's `simulate/specs.py`, and the discriminator
values match that module's `Literal`s exactly. The producer's dataclass
and this schema are two views of one contract — a rename in either is a
coordinated change.

## The seven functions

| Function | Phase-1.5 variants | Replaces (1.1) |
|---|---|---|
| `Geometry` | `patch_2d` | `patch_size_mm`, `patch_dr_mm` root attrs |
| `CellModel` | `courtemanche`, `aliev_panfilov` | `cell_model` name string |
| `Substrate` | `uniform_random_fibrosis` | `fibrosis_density` per-trace column |
| `Activation` | `planar_edge`, `point`, `s1s2` | `stim_edge` per-trace enum |
| `Electrodes` | `centered_grid_2d` | `electrode_row`, `electrode_height_mm` |
| `Backend` | `finitewave` | `simulator` name string |
| `LabelPolicy` | `global_density`, `local_density` | *(implicit — density was the label)* |

Plus three supporting definitions: `SubstrateSummary` (what the draw
realized, as against what was requested), `LabelNames` (`{int: name}`),
and `BipolarPair` (the realized per-pair detail a trace indexes into).

## Field walkthrough — the parts worth explaining

Precise field definitions live in the schema file. What follows is the
reasoning that the field list alone doesn't carry.

**Requested vs realized.** `Substrate` holds what was *asked for*
(density 0.35); `SubstrateSummary` holds what the draw *produced*
(realized density 0.352). They differ through grid discretization, and
the label is computed from the realized value. 1.1 carried both as
sibling float columns with nearly identical names, which made it easy to
read the wrong one.

**`planar_edge.edges` is a list.** The producer's Phase-1 dataclass has
a single `edge`. Today's behavior is the one-element list, which means
multi-edge stimulation — more propagation-direction variety, closer to
how the reference literature stimulated — needs no schema change when it
arrives.

**`S1S2Activation` nests a real activation.** An S1-S2 protocol needs a
*place* to stimulate, and that place is an ordinary single-shot
activation (an edge or a point). Rather than defining parallel "site"
objects duplicating those fields, the protocol references
`SingleShotActivation`; its nested activation's timing field is ignored,
since protocol timing comes from the intervals. Excluding protocol
variants from that union is what stops a protocol nesting a protocol.
This variant is marked **provisional** in the schema — it exists so the
producer can implement it without a contracts bump, but its field set
hasn't yet been validated against an implementation.

**Label policies take `thresholds[]`, not a single threshold.** N
thresholds give N+1 classes, so the binary healthy/fibrotic policy is a
one-element array and multiclass severity is several — no new variant,
no schema bump. Policies deliberately do **not** name their classes:
`LabelNames` already maps any number of labels, and carrying names in
both places meant two sources for one fact, free to disagree.

**Electrode detail is per simulation, indexed per trace.** The realized
`pairs` list carries each pair's row, height and midpoint; a trace
stores only `pair_index`. `pair_index` is explicit inside each entry
rather than implied by array position, so a filtered or reordered view
can't silently renumber pairs.

**`Edge` and `PositionMm` are defined once.** Every variant naming an
edge `$ref`s the same enum, and every coordinate `$ref`s the same
2-or-3-element array. Two inline copies of an edge vocabulary is how a
single-shot stimulus and a paced protocol end up disagreeing about what
"top" means — a disagreement that would surface only as a wrong-looking
wavefront in a figure.

## Scope boundary

Everything here describes **one simulation**. What a multi-simulation
*sweep* varied — the θ-spec — is bank-scoped and lives in
[generation_params](generation_params.md), referenced from
`synthetic_bank`'s root attrs rather than its per-simulation group.

The link between the two is `TunedParam.path`, a dotted pointer into
these objects (`substrate.density`). It is an opaque string, not a
`$ref`, so the two schemas stay independent.

## Versioning

No `schema_version` of its own — it is a `$defs` library, versioned with
the package and through the `synthetic_bank` version that references it.

Adding a **variant** to a union is additive: existing banks still
validate, and consumers that don't know the new variant will fail on it
loudly rather than misread it. Adding a **required field to an existing
variant** is breaking, and would need the referencing bank schema to
bump.

## Example

A complete per-simulation config, as stored (decoded from the `*_json`
columns):

```json
{
  "geometry": {"type": "patch_2d", "size_mm": 40.0, "dr_mm": 0.25, "anisotropy_ratio": 2.0},
  "cell_model": {"type": "courtemanche", "params": {"g_CaL_scale": 0.8}},
  "substrate": {"type": "uniform_random_fibrosis", "density": 0.35},
  "substrate_summary": {"realized_density": 0.352, "n_fibrotic_nodes": 9012},
  "activation": {"type": "planar_edge", "edges": ["top"], "voltage": 1.0, "strip_thickness": 3},
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

A point stimulus and an S1-S2 protocol, for contrast:

```json
{"type": "point", "position_mm": [20.0, 20.0], "radius_mm": 0.5, "voltage": 1.0}
```

```json
{
  "type": "s1s2",
  "site": {"type": "point", "position_mm": [20.0, 20.0]},
  "s1_interval_ms": 400.0,
  "s2_interval_ms": 250.0,
  "n_s1": 5
}
```
