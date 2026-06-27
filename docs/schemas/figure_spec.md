# figure_spec

## What it is

A **declarative spec for one publication figure** — the git-tracked source
of truth from which egm-studio's headless render CLI regenerates the
actual image. One JSON file per figure, living at
`intracardiac-platform/project/phases/phase_X/figure_specs/<id>.json`.

Schema version: `1`.

## Why it exists

Binary figure files don't belong in version control: they're deterministic
build outputs. The spec is the artifact; the rendered PDF/PNG/SVG is
gitignored and rebuilt at paper-build time. Keeping the spec under version
control means a figure is reproducible, diffable, and traceable to the
banks/models/observations it draws from (via the manifest entry's
`consumes_*` fields), while the heavy image bytes stay out of git.

A **required `description`** records *why* the figure exists. A figure made
during exploration and then forgotten can be revisited months later, its
description read, and a keep-or-discard decision made without re-deriving
its purpose.

The figure does not record which phase it belongs to — that membership is
held by the phase manifest that points at it.

## Field walkthrough

- **`schema_version`, `id`** — identity. `id` uses the `fig_` prefix (the
  FigureId pattern, defined once in `common.schema.json`); it is
  slug-based, allows hyphens, and carries no date, so it does **not**
  match the dated ArtifactId pattern.
- **`description`** (required) — human-readable explanation of what the
  figure shows and why it was generated.
- **`recipe`** — the name of the egm-studio figure recipe that renders
  this figure. A free-form string: the recipe vocabulary (and the
  validation of recipe-specific inputs) is owned by egm-studio, not
  hardcoded into the contract.
- **`inputs`** — recipe-specific. Kept permissive (additional keys
  allowed) because the schema discriminates on `recipe` at the egm-studio
  layer. The one well-known key is `groups` — an array of
  `{name, bank_id}` for overlay/comparison recipes.
- **`layout`, `styling`** — recipe-specific, permissive (panel grid, sizes,
  palette, fonts, dpi, …).
- **`output`** — `format` (`pdf` / `png` / `svg`, vector PDF the default)
  and `path`, which typically points OUT of the meta repo into the paper
  repo. The destination file is gitignored and regenerated.
- **`illustrates_observations`** — optional observation ids this figure
  illustrates; drives the manifest entry's `consumes_observations`.
  Optional because not every figure illustrates a specific observation.

## Versioning

Version `1`. A bump would follow a structural change to the spec envelope
(new top-level block, changed `output` shape, …). Note that adding a new
**recipe** is *not* a schema change — recipes are an egm-studio concept and
`recipe` is just a string here.

## Example

```json
{
  "schema_version": "1",
  "id": "fig_feature_distributions_synth_vs_iafdb",
  "description": "Overlay of per-feature distributions, synthetic v1.5 vs IAFDB, with Wasserstein distance annotations.",
  "recipe": "feature-distribution-overlay",
  "inputs": {
    "groups": [
      {"name": "Synthetic v1.5 (Courtemanche)", "bank_id": "tbank_synthetic_courtemanche_v1_5_2026-06-25"},
      {"name": "IAFDB", "bank_id": "tbank_iafdb_v1_2026-06-15"}
    ],
    "feature_subset": "all",
    "distance_annotation": "wasserstein"
  },
  "layout": {"panel_grid": [3, 4]},
  "styling": {"palette": "project_standard", "dpi": 300},
  "output": {
    "format": "pdf",
    "path": "../../../intracardiac-papers/papers/phase_1_5/figures/fig_feature_distributions_synth_vs_iafdb.pdf"
  },
  "illustrates_observations": ["obs_courtemanche_high_entropy_tail_2026-06-25"]
}
```

See `intracardiac-platform/project/cross_artifact_linkage_design.md`
section 5.
