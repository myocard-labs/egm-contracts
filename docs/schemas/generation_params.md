# generation_params

## What it is

The **θ-spec**: a record of which generation knobs a bank's sweep
varied, over what ranges, and within which structural regime.

Not a document format. Like `common.schema.json` and
`simulation_config.schema.json`, this file is a library of shared
`$defs`; the object is stored JSON-encoded in `synthetic_bank`'s
`generation_params_json` root attr.

## Scope — and why it isn't in simulation_config

The two schemas answer different questions:

| | [simulation_config](simulation_config.md) | generation_params |
|---|---|---|
| Scope | one simulation | one bank / one sweep |
| Answers | "this run used density 0.31" | "density was varied over [0, 0.5] in logit space" |
| Stored in | `simulations/` group, one row per sim | root attrs, one per bank |

Keeping them apart matters because conflating a per-simulation fact with
a per-sweep fact is the same class of mistake the whole `synthetic_bank`
2.0 restructure exists to remove.

They connect through `TunedParam.path` — a dotted pointer into the
per-simulation config (`substrate.density`). It is an opaque string, not
a `$ref`, so neither schema depends on the other.

## Why it exists

The parameter-estimation work asks: which generation settings make
synthetic EGMs look like real ones? Answering that means sweeping knobs,
measuring features, and fitting a surrogate — and all of that needs the
bank to say what it swept.

The obvious design is a fixed field set: a column per knob. It fails for
a specific reason — **which knobs are worth calibrating is itself an
experimental result**. The screening study that decides membership runs
*inside* the phase, and its answer will change as the simulator gains
physics. A fixed field set would need a schema bump every time the
answer changed.

So θ is a **selection over the config** rather than a copy of it. The
per-simulation objects stay the single source of truth for what each
simulation was; the θ-spec says which of those values were varied and
how. Adding or removing a knob is one list entry and zero schema churn.

## Field walkthrough

### `GenerationParams`

- `regime` — the structural discriminators held fixed across the sweep,
  as `{function: type}`: `{"cell_model": "courtemanche", "substrate":
  "uniform_random_fibrosis"}`. This is what makes a recovered parameter
  region interpretable. "The realistic conduction velocity is X" is a
  claim about *Courtemanche on uniform-random fibrosis*, not about
  atrial tissue in general — a different regime is a different θ-space
  by design, not a wider one. Open key set, so a future strategy axis
  becomes a regime key without a schema change.
- `knobs` — the `TunedParam` list, in a **stable order**. An emulator's
  input vector is positional, so reordering the list silently
  reinterprets every stored design point.

  **It may be empty**, and that is meaningful rather than missing: a
  bank generated at one fixed parameter set has a regime and no swept
  knobs. That is exactly what a migration-wave bank records.

### `TunedParam`

- `path` — the dotted pointer identifying the knob, and the axis label
  in a feature-vs-θ plot. **Deliberately unconstrained** — no pattern,
  no enum. Resolving a path against a config is a resolver's job, and
  both the resolver and a formal path grammar are deferred; constraining
  this later is additive, whereas guessing the grammar now would bake in
  a shape nothing has tested.
- `bounds` — `[lo, hi]`, the sweep range and the emulator's input
  domain. Expressed in the knob's **natural units**, not transformed
  space, so a reader doesn't need to know the transform to know what was
  swept. Ascending by convention — JSON Schema cannot compare two items
  of one array, so `lo <= hi` is the producer's to enforce.
- `transform` — `identity` / `log` / `logit`: the space the sweep and
  any surrogate model work in. `log` suits a strictly-positive scale
  knob whose effect is multiplicative; `logit` suits a knob bounded to
  (0,1) such as a fibrosis density, keeping samples off the boundary.
  Recorded rather than inferred, because the same bounds sampled in
  different spaces give different designs — a result only reproduces if
  the space is known.
- `role` — `label_param` or `nuisance`. A `label_param` determines the
  trace's label (fibrosis density under a density policy) and is the
  thing the classifier is meant to detect; a `nuisance` changes the
  signal without changing the label (electrode height, conduction
  velocity, SNR). The distinction is what makes a feature-vs-θ
  relationship interpretable: a feature tracking a label parameter is
  signal, and the same feature tracking a nuisance knob is a confound.
- `nominal` — optional; the value the knob is pinned to when it is *not*
  in the active sweep. Without it, a one-at-a-time screening bank says
  which knob varied but not what the others were held at, and two
  screenings are then not comparable.

### What it deliberately doesn't store

**Values.** A `TunedParam` has no `value` field. The value a given
simulation used lives in its per-function config, reachable by `path`.
Storing it here too would be a second source of truth for the same
number.

## Versioning

No `schema_version` of its own — a `$defs` library, versioned with the
package and through the `synthetic_bank` version that references it.

Adding an optional field to `TunedParam` is additive. Adding a
`transform` or `role` value is additive for producers but breaking for
consumers that exhaustively match on the enum, so it is worth a
coordinated bump.

## Example

A migration-wave bank — regime recorded, nothing swept:

```json
{
  "regime": {
    "geometry": "patch_2d",
    "cell_model": "courtemanche",
    "substrate": "uniform_random_fibrosis",
    "activation": "planar_edge",
    "electrodes": "centered_grid_2d",
    "backend": "finitewave",
    "label_policy": "global_density"
  },
  "knobs": []
}
```

A two-knob sweep — one label parameter, one nuisance knob:

```json
{
  "regime": {"cell_model": "courtemanche", "substrate": "uniform_random_fibrosis"},
  "knobs": [
    {
      "path": "substrate.density",
      "bounds": [0.0, 0.5],
      "transform": "logit",
      "role": "label_param"
    },
    {
      "path": "electrodes.height_mm",
      "bounds": [0.2, 1.0],
      "transform": "identity",
      "role": "nuisance",
      "nominal": 0.6
    }
  ]
}
```
