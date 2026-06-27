# phase_manifest

## What it is

A **per-phase shallow index** of every artifact that belongs to one
project science-phase (Phase 1.5, Phase 2, …). One JSON file per phase,
living at `intracardiac-platform/project/phases/phase_X/manifest.json`.

Schema version: `1`.

## Why it exists

A research phase produces a sprawl of artifacts — training banks,
models, prediction banks, observations, figures, and eventually a paper —
scattered across several repos and the local filesystem. The manifest is
the one place that records *what exists*, *what produced it*, and *what it
relates to*, so that:

- nothing load-bearing gets forgotten between the day it was made and the
  day the paper is written;
- a reader (or a reproducibility script) can walk from a paper figure back
  to the exact bank + model that produced it;
- `scripts/validate_manifest.py` can scan the phase folder for drift.

The manifest deliberately stays a **shallow index**: entries are pointers,
not content. The graph of relationships is recorded with field names that
map 1:1 onto edge types if the project ever upgrades to a real provenance
graph (`trained_on_bank` → `TRAINED_ON`, etc.).

**Phase membership lives here, not on the artifacts.** An observation or
figure file does not declare which phase it belongs to — the manifest that
points at it is what places it in a phase. The link is one-directional.

## Entries are pointers, not content

Every entry carries only:

- `id` — the artifact's stable cross-artifact id (the ArtifactId /
  FigureId / PaperId patterns, defined once in `common.schema.json`).
- `path` — where the artifact lives, relative to the meta repo.
- `produced_by_package` + `produced_by_version` — provenance, on **every**
  entry type (even observations/figures, whose producer is egm-studio —
  the version matters if the saved view-state format changes).
- relationship references to other artifacts, as id strings.
- optional `usage_tag` / `usage_notes` (observations + figures).
- optional `download_url` (banks + models), filled at **release time**,
  not write time.

Everything else — titles, descriptions, embedded traces, view-state,
training metrics, figure layout — lives inside the standalone file the
entry points at, never in the manifest.

## Field walkthrough

Top level: `schema_version`, `phase` (numeric, e.g. `1.5`), `status`
(`in_progress` / `shipped` / `abandoned`), and a free-text
`phase_summary`. Then the artifact sections, in pipeline order:

- **`egm_banks`** — banks of EGM traces: training (`tbank_`), pretraining
  (`ptbank_`), and prediction (`lpred_` / `upred_`) banks. The id prefix
  tells the role; a prediction bank is just an entry that also fills
  `model` + `source_bank` (a ClassifierBank whose traces carry
  predictions), so predictions are not a privileged separate section.
- **`noise_banks`** — `nbank_` banks of additive noise the synthetic
  mixer adds to EGM data. Separate from `egm_banks` because the content
  (noise, not EGM) and role (additive source, not classified data) differ.
- **`training_runs`** — `run_` records, with `trained_on_bank` +
  `produced_model` pointers.
- **`models`** — `model_` artifacts, with a `trained_from_run` pointer.
- **`observations`** — `obs_` entries, with an optional `usage_tag`.
- **`figures`** — `fig_` entries, with `consumes_banks` /
  `consumes_models` / `consumes_observations` lists and an optional
  `usage_tag`.
- **`papers`** — `paper_` entries, with a `figures` list.

Every section is empty-list-OK.

## Versioning

Version `1`. A bump would follow any structural change — a new artifact
section, a new relationship field, a changed entry shape. The relationship
field names are chosen for graph-upgrade compatibility, so adding the
graph is *not* itself a manifest schema change.

## Example

```json
{
  "schema_version": "1",
  "phase": 1.5,
  "status": "in_progress",
  "phase_summary": "Synthetic-data realism for Phase 1.5.",
  "egm_banks": [
    {
      "id": "tbank_synthetic_courtemanche_v1_5_2026-06-25",
      "path": "banks/tbank_synthetic_courtemanche_v1_5.h5",
      "produced_by_package": "synthetic-egm-pipeline",
      "produced_by_version": "v0.2.0"
    },
    {
      "id": "upred_iafdb_v1_5_2026-06-25",
      "path": "predictions/upred_iafdb_v1_5.h5",
      "produced_by_package": "egm-classifier",
      "produced_by_version": "v0.2.0",
      "model": "model_egm_classifier_v1_5_2026-06-25",
      "source_bank": "tbank_iafdb_v1_2026-06-15"
    }
  ],
  "noise_banks": [
    {
      "id": "nbank_iafdb_2026-06-15",
      "path": "banks/nbank_iafdb.h5",
      "produced_by_package": "iafdb-pipeline",
      "produced_by_version": "v0.2.0"
    }
  ],
  "models": [
    {
      "id": "model_egm_classifier_v1_5_2026-06-25",
      "path": "models/best.pt",
      "produced_by_package": "egm-classifier",
      "produced_by_version": "v0.2.0",
      "trained_from_run": "run_v1_5_courtemanche_2026-06-25"
    }
  ],
  "figures": [
    {
      "id": "fig_feature_distributions_synth_vs_iafdb",
      "path": "figure_specs/fig_feature_distributions_synth_vs_iafdb.json",
      "produced_by_package": "egm-studio",
      "produced_by_version": "v0.1.0",
      "consumes_banks": ["tbank_synthetic_courtemanche_v1_5_2026-06-25"],
      "usage_tag": "in_paper_main"
    }
  ]
}
```

See `intracardiac-platform/project/cross_artifact_linkage_design.md`
sections 3 and 8 for the full design and the scan-and-validate checks.
