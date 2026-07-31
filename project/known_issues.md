# egm-contracts — known issues + planned evolutions

Internal tracker for limitations and intentional simplifications in the current
schemas, plus the planned resolution for each. When a Phase 1 schema bumps to
Phase 2, this file is where to look first.

---

## Active (will need a schema bump to resolve)

### `observation` — trace references use a fragile integer index

**Current state (v0.5.0).** The `observation` schema's `TraceRef` addresses
a trace as `{ "bank": <ArtifactId>, "index": <int> }` — the integer position
of the trace inside the bank. This is the v0.1 trace-ID scheme shared with
the manifest / figure-linkage design.

**Why this is a problem.** The index is only stable as long as the bank is
never re-extracted or re-ordered. If a producer regenerates a bank, a saved
observation's pinned traces can silently point at different signals.

**Resolution plan.** Introduce stable per-trace IDs (synthetic:
`<sim_id>_<electrode_pair_id>`; IAFDB:
`<record>_<channel>_<segment_start_ms>`) and bump `observation` (the
`TraceRef.index` field becomes `trace_id`). Deferred — the integer-index
hybrid was the locked-in v0.1 decision; see "Open follow-ups" in
`intracardiac-platform/project/cross_artifact_linkage_design.md`.

**Trigger.** First time a re-extracted bank invalidates a saved trace-list
observation in a painful way.

---

## Resolved / closed

### `synthetic_bank` `stim_edge` → per-simulation `activation` object (v0.6.0)

**Resolved 2026-07-30** by the `synthetic_bank` 2.0 restructure, which went
further than this entry anticipated. `stim_edge` is gone, replaced by a
polymorphic `activation` object stored **per simulation** rather than per trace
(`planar_edge` with a list of edges, `point`, `s1s2`), defined in
`simulation_config.schema.json`.

Two things this entry got right, and one it did not. It correctly predicted the
enum would not survive point sources or paced protocols, and correctly called
for a `oneOf` on a `type` discriminator. What it missed is that `stim_edge` was
not a lone problem: `fibrosis_density`, `electrode_row` and
`electrode_height_mm` each encoded a Phase-1 assumption in exactly the same way,
and all four were per-trace copies of a per-simulation fact. Fixing the stimulus
alone would have left the same failure mode in three other columns and cost a
second breaking bump to find that out.

The trigger also arrived earlier than expected — Phase 1.5, not Phase 2 — because
the restructure was cheapest while no released work depended on a 1.1 bank.

### `hybrid_eval_metrics` schema removed (v0.4.1)

The `hybrid_eval_metrics` JSON format was deleted. It persisted aggregate
classifier scores over a mixed synthetic + IAFDB set, including AUROC / FPR /
confusion computed against IAFDB rows treated as healthy negatives. That
framing is untenable: IAFDB has no fibrosis ground truth, so any
label-dependent metric scores the model against an extraction assumption
rather than truth (see `feedback-iafdb-unlabeled-no-ml-validation` /
`project-iafdb-eval-catch22`).

Going forward, rigorous labeled evaluation stays on synthetic data (captured
in `training_run_record` / `training_metrics`); IAFDB is used only as a
label-free **sanity check** on the model's probability/label distribution,
computed at analysis time in `egm-studio` from the `ClassifierBank` (no
persisted contract). A true Sánchez-style hybrid evaluation remains possible
only if labeled real EGM data becomes available — `ClassifierBank` can hold
the combined set, but IAFDB (our only open real source) is unlabeled. The
removal dropped the schema, its validator, the generated model, and the
`egm-data` reader/writer; `docs/schemas/hybrid_eval_metrics.md` is kept as a
tombstone. The nominal producer (`egm-classifier`) never shipped a writer for
it, so no producer code changed.

### `noise_bank` + `noise_bank_run_record` schemas added; `iafdb_bank` "none" filter mode (v0.2.0)

Three related changes shipped together to support Phase 3 of the polyrepo
refactor:

- `noise_bank/1.0` — new minimal HDF5 schema for low-amplitude (quiet)
  bipolar EGM segments. **Intentionally lean**: carries only the fields
  the synthetic mixer actually consumes (signal, source_record,
  source_channel per trace; schema_version / created_utc / source /
  fs_hz at root). The producer is `iafdb-pipeline` today, but the
  schema is dataset-agnostic so any future real EGM source slots in
  without a schema bump.
- `noise_bank_run_record/1.0` — new JSON sidecar schema that captures
  extraction provenance (calibration scheme, threshold strategy,
  windowing parameters, optional per-trace audit arrays). Written by
  the same producer that writes the bank, paired with the bank by
  name-stem convention (same pattern as `metrics.csv` ↔ `run.json` in
  egm-classifier). The mixer never opens the sidecar; debuggers,
  reproducibility audits, and the white paper's methods section do.
  Factoring decision (per Daniel 2026-06-17): the original noise_bank
  draft tried to combine data + methods in one HDF5 file; auditing
  showed the v1 mixer math uses 1 of 23 fields and the rest is
  provenance. Splitting into bank + run record matches the existing
  project pattern and keeps each schema honest about its job.
- `iafdb_bank/1.1` — added `"none"` to the `threshold_mode` enum and
  made `threshold_value` nullable. Enables the unfiltered-export path
  for pretraining banks where every windowed segment is retained.
  Old `1.0` files no longer validate (pre-1.0 of egm-contracts; no
  back-compat needed since iafdb-pipeline hasn't shipped a tagged
  release yet).

**Future work flagged but deferred:** `iafdb_bank` has the same
data + provenance bloat issue as the original noise_bank draft (only a
few of its fields are consumed by egm-data's converter; the rest is
extraction provenance). Daniel decided not to refactor iafdb_bank now —
the ClassifierBank pipeline already highlights the useful subset, and
further restructuring would delay the science. Revisit when motivation
strikes.

### `predictions` schema retired (v0.1.2)

The standalone `predictions` schema (CSV+JSON pair) was retired in
contracts v0.1.2. Per-trace prediction outputs now live inside the
producing `ClassifierBank` in egm-data; the `hybrid_eval_metrics`
schema (then bumped to v2.0) recorded only the aggregate scores — it
was itself removed in 0.4.1 (see above). Existing
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
