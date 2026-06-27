# observation

## What it is

A **recorded discovery** made during signal exploration or ML
diagnostics — "I noticed something worth keeping." One JSON file per
observation, living at
`intracardiac-platform/project/phases/phase_X/observations/<id>.json`.

Schema version: `1`.

## Why it exists

The gap between noticing something interesting and writing it into a paper
can be months. Observations close that gap: they capture the prose
description of a finding, optionally pin the exact traces that show it, and
optionally record the egm-studio view-state needed to reproduce the view.
Later, a figure can reference the observation by id, and the
scan-and-validate script can confirm that every observation flagged as
`informed_paper` is actually backed by a figure.

The single most important rule: the free-text **`description` is
required**. A pinned trace list with no prose is data without context —
not an observation. Trace sets are modeled as part of the observation (not
a separate artifact type) precisely so there is one home for "something
interesting", carrying prose, traces, or both.

The observation does not record which phase it belongs to — that
membership is held by the phase manifest that points at it.

## Field walkthrough

- **`schema_version`, `id`, `date`, `title`** — identity. `id` uses the
  `obs_` prefix (the ArtifactId pattern, defined once in
  `common.schema.json`).
- **`description`** (required) — the prose. The discovery itself; lets
  someone returning cold understand the finding and decide whether it
  still matters.
- **`references`** — structured pointers to *other* artifact types:
  `models` and parent `observations`. Bank references are deliberately
  **not** listed here — they would duplicate (and risk drifting from)
  `view_state.banks_loaded` + `traces[].bank`. The validate-manifest
  script derives an observation's bank set as the union of those two.
- **`traces`** (optional) — pinned traces of interest, each a
  `{bank, index}` pair. The v0.1 trace address is `(bank id, integer
  index)`; stable per-trace ids are a deferred upgrade.
- **`view_state`** (optional) — what to reload in egm-studio to recreate
  the view: `banks_loaded`, `filter`, `sort`,
  `selected_trace_indices_within_filter`. egm-studio owns the exact shape,
  so additional keys are allowed.

## Versioning

Version `1`. A bump would follow any structural change to the observation
shape (e.g. promoting trace addressing from integer index to stable
per-trace ids).

## Example

```json
{
  "schema_version": "1",
  "id": "obs_courtemanche_high_entropy_tail_2026-06-25",
  "date": "2026-06-25",
  "title": "Courtemanche synthetic produces high-entropy traces IAFDB doesn't show",
  "description": "The synthetic sample_entropy distribution has a long tail above 1.5 that IAFDB never reaches. ~5% of synthetic traces exceed 1.5; 0% of IAFDB does.",
  "traces": [
    {"bank": "tbank_synthetic_courtemanche_v1_5_2026-06-25", "index": 1247},
    {"bank": "tbank_iafdb_v1_2026-06-15", "index": 89}
  ],
  "view_state": {
    "banks_loaded": [
      "tbank_synthetic_courtemanche_v1_5_2026-06-25",
      "tbank_iafdb_v1_2026-06-15"
    ],
    "filter": "sample_entropy > 1.5",
    "sort": "sample_entropy desc"
  }
}
```

See `intracardiac-platform/project/cross_artifact_linkage_design.md`
section 4.
