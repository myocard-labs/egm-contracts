# egm-contracts — known issues + planned evolutions

Internal tracker for limitations and intentional simplifications in the current
schemas, plus the planned resolution for each. When a Phase 1 schema bumps to
Phase 2, this file is where to look first.

---

## Active (will need a schema bump to resolve)

### `synthetic_bank` — `stim_edge` is too narrow for Phase 2

**Current state (Phase 1).** `traces/stim_edge` is an enum of 4 string values:
`top` / `bottom` / `left` / `right`. This describes a planar wave propagating
from one edge of the 2D patch, which is the only stimulation protocol the
Phase 1 synthetic pipeline produces.

**Why this is a problem for Phase 2.** Phase 2 of the synthetic-egm-pipeline
roadmap introduces:

- Point-source stimulation (focal pacing from a single mesh location).
- Multi-beat steady-state pacing (drive the tissue to a fixed CL before
  sampling) — Phase 2 alongside Courtemanche.
- S1–S2 extra-stimulus protocols — Phase 4, when AF rhythm modelling lands.

None of these fit in a 4-value edge enum.

**Resolution plan.** When Phase 2 lands, bump `synthetic_bank` schema version
to `2`, **replace** `stim_edge` with a richer
`stimulation` object:

```json
"stimulation": {
  "type": "object",
  "oneOf": [
    { "properties": { "type": { "const": "planar_wave" },
                      "edge": { "enum": ["top", "bottom", "left", "right"] }}},
    { "properties": { "type": { "const": "point_source" },
                      "location_mm": { "type": "array", "items": "number",
                                       "minItems": 2, "maxItems": 2 }}},
    { "properties": { "type": { "const": "s1_s2" },
                      "s1_location_mm": "...", "s1_s2_interval_ms": "number" }}
  ]
}
```

Phase 1 producers wrote `stim_edge: "top"`; Phase 2 producers write
`stimulation: {"type": "planar_wave", "edge": "top"}`. Schema version bump
disambiguates. Consumers branch on schema_version.

**Trigger.** The egm-classifier Phase 2 work (Courtemanche cell model +
multi-beat pacing) will hit this first. The synthetic-egm-pipeline refactor
chat that adds those features should also do this schema bump in egm-contracts
as part of the same change.

---

## Resolved / closed

### `predictions` schema retired (v0.1.2)

The standalone `predictions` schema (CSV+JSON pair) was retired in
contracts v0.1.2. Per-trace prediction outputs now live inside the
producing `ClassifierBank` in egm-data; the `hybrid_eval_metrics`
schema (bumped to v2.0) records only the aggregate scores. Existing
v1 prediction files from v1_baseline / v1.5 / v1_iafdb investigations
are kept as-is in their checkpoint dirs as historical artifacts.

### `iafdb_healthy_bank` → `iafdb_bank` rename + label removal (v0.1.2)

The schema was renamed and its `traces/label` column removed. The IAFDB
bank is now just a calibrated, band-passed, threshold-selected segment
collection — labeling decisions move to ClassifierBank conversion time
via a consumer-supplied `label_fn`. Existing iafdb_healthy_bank files
are obsolete; regenerate via the iafdb-pipeline once it's refactored.

### `format_version` vs `schema_version` field name inconsistency (2026-06-15)

Earlier the bank schemas used `format_version` (matching the HDF5 root attr
name on the existing producers) while the JSON/CSV schemas used
`schema_version` with the `package.format/N` prefix pattern. Resolved by
unifying on `schema_version` everywhere and dropping the prefix — all 7
schemas now carry `schema_version: "X.Y"`. Existing on-disk producer files
that still write `format_version` as an HDF5 attr will need to be updated
when their producers (`iafdb-pipeline`, `synthetic-egm-pipeline`) are
refactored; the validator does NOT translate the old name. Regenerate any
legacy banks as part of the producer refactor.

### Schema version string format inconsistency (2026-06-15)

Earlier the JSON/CSV schemas used `<package>.<format>/X.Y` (e.g.,
`1.0`) while the bank schemas used a plain `X.Y`. Resolved
by simplifying all schemas to a plain `X.Y` string. Each schema is uniquely
identified by its filename + JSON Schema `$id`; the version string only
needs to track the version.
