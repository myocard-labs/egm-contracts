# egm-contracts — roadmap

Future work only — shipped history lives in [`CHANGELOG.md`](../CHANGELOG.md). Internal
doc; public users read the README + `docs/schemas/`.

This is the *what's coming next* companion to [`project/schema_evolution.md`](schema_evolution.md)
(the *how do we version it* reference — which changes force a minor vs major bump, the X.Y
`schema_version` format). Because this repo is the head of the cascade, most items below carry a
downstream tail (egm-data reader/writer → producers → consumers); the fixed
[cascade order](#schema-bumps-to-coordinate-cascade-order) is spelled out at the bottom and is
referenced by the egm-data + iafdb-pipeline roadmaps.

Work lands here as it's identified, sits in the **Backlog** until a phase-planning session
promotes it, then moves to the CHANGELOG once shipped. Items scheduled into cross-cutting Phase
work carry a `→ tracked at intracardiac-platform Phase X` annotation.

## Phase 1.5 — sim-realism

### `iafdb_bank` 1.3 — audit-report sidecar pointer

Add an optional `run_record_path` field to `iafdb_bank` attrs so the healthy bank can carry a
paired JSON sidecar of per-record diagnostics, symmetric with how `noise_bank` already pairs
with `noise_bank_run_record`. The sidecar schema itself is either a new top-level
`iafdb_bank_run_record` or a reuse of the `noise_bank_run_record` structure — decide during
implementation. (`iafdb_bank` 1.2 was consumed by the v0.5.0 `bank_id` field, so this is 1.3.)

> → Tracked at `intracardiac-platform/project/project_plan.md` Phase 1.5. Ships with
> iafdb-pipeline's per-record audit reports + the egm-data sidecar reader/writer.

### `noise_bank` 1.1 — `calibration_scalar` per-trace column (+ `bank_id` attr)

Add an optional `calibration_scalar` per-trace column so iafdb-pipeline's opt-in noise-side
calibration can be expressed without breaking older readers (default NaN = uncalibrated;
explicit scalar = gain applied before extraction). Batch in the **`bank_id` HDF5 attr** (+ a
link to the run record) here too, so egm-studio's Noise view can read a noise bank's stable id
from the `.h5` itself instead of the sibling run-record sidecar.

> → Tracked at `intracardiac-platform/project/project_plan.md` Phase 1.5. Pairs with
> iafdb-pipeline's opt-in noise calibration; the `bank_id`-attr half is a refactor-cleanup
> batch item (below).

### `noise_bank_run_record` 1.2 — `per_trace_provenance.lead`

Add a `lead` field to the per-trace provenance dict recording which surface lead won the
calibration's priority-order selection (when noise-side calibration is on). Ships with the
`calibration_scalar` work. (1.1 was consumed by the v0.5.0 `bank_id` field, so this is 1.2.)

> → Tracked at `intracardiac-platform/project/project_plan.md` Phase 1.5.

## Phase 2 — multiclass severity

### Polymorphic `stimulation` schema (replace `stim_edge`)

`synthetic_bank` carries `stim_edge` as a single enum — fine for v1's one `PlanarEdgeStimulus`,
but it doesn't extend to the richer activation sources scheduled into Phase 1.5 / 2 / 4
(`PointStimulus`, `S1S2Protocol`, `PacingTrain`, multi-edge). Replace it with a polymorphic
`stimulation` object (type discriminator + per-type params). **Coordinated release** —
egm-contracts v0.6.0 + egm-data cascade + synthetic-egm-pipeline — bundled at the Phase 2
first-publish inflection so the work doesn't fragment across releases (v0.5.0 was taken by the
linkage wave). Migration noted in `schema_evolution.md`.

> → Tracked at `intracardiac-platform/project/project_plan.md` Phase 2. Producer-side scope is
> in synthetic-egm-pipeline's roadmap under "Additional activation sources."

## Phase 4 — feature banks (egm-features / Refactor Step 4)

### `egm_features_bank` schema

When egm-features emits per-trace feature bundles, the output needs a contract. Likely shape:
an HDF5 bank with one column per feature + a feature-name list in attrs + a hash of the source
bank for traceability (same convention as the other banks). **Don't land the schema until the
producer's feature list stabilizes** — otherwise it churns.

> → Tracked at `intracardiac-platform/project/refactor_checklist.md` Phase 4 (egm-features).

## Phase 6 — C++ / TensorRT deployment

### C++ codegen activation

Fill in the `codegen/gen_cpp.py` stub — likely `quicktype` or `nlohmann/json-schema-codegen`
emitting headers into `_generated/cpp/`, with a parallel C++ codegen-drift check in CI. The
consumer is the C++/TensorRT runtime that loads `egm_class_model_metadata.json` and applies the
documented preprocessing.

> → Tracked at `intracardiac-platform/project/project_plan.md` Phase 6.

## Phase 7 — 3D geometry

### 3D geometry schema

When synthetic-egm-pipeline grows `AtrialMesh3D`, `synthetic_bank` needs to express which mesh
produced a simulation — likely a `mesh_path` (relative reference to a `.pts/.elem/.lon` triple)
+ a content hash. Bigger question: a dedicated `atrial_mesh_3d` schema for the mesh format
itself, or delegate to openCARP's native format. Decide at Phase 7 kickoff.

> → Tracked at `intracardiac-platform/project/project_plan.md` Phase 7.

## Backlog (unscheduled — promoted into a phase at a planning session)

### Align `HeldOutTest.metrics` to `EpochRecord.val_metrics`

The `training_run_record` schema's `HeldOutTest.metrics` shape drifted slightly from
`EpochRecord.val_metrics` during the v0.3.x training-side rewrite; both should carry the same
scalar bundle (auroc, accuracy, f1, precision, recall, ece, confusion, reliability) so
consumers render them with one code path. Additive alignment, no consumer breakage expected.
Component-internal (was task #275); doesn't gate a phase.

### Refactor-cleanup batch (from the egm-studio B10g review)

Three small, backward-compatible schema changes egm-studio deferred, to land together:

- Make `produced_by_package` / `produced_by_version` **optional** on `phase_manifest` entries,
  so egm-studio can index a manually-added producer artifact without sentinel values
  (`"unknown"` / `"0"`).
- Add an **active view / tab** field to the `observation` `view_state`, so *Open observation*
  can restore the active flow + sub-tab, not just banks + filter + selection.
- The `noise_bank` **`bank_id` attr** (grouped with the `noise_bank` 1.1 work above).

### Normalization-scheme expansion (`robust_zscore`, `meanvar`)

`egm_class_model_metadata` currently admits `zscore` / `zero2one` / `none`. Future classifier
work might want `robust_zscore` (median + MAD) or `meanvar` (stored per-channel stats once
multi-channel). Add when a real model needs it — speculative until then (see egm-classifier's
"Open architectural questions").

## Schema bumps to coordinate (cascade order)

When any schema in this repo changes, the downstream cascade is fixed:

1. **egm-contracts** ships the new schema version. Tag + push.
2. **egm-data** updates its readers + writers to satisfy the new shape and bumps its pinned
   `myocard-egm-contracts`. Tag + push.
3. **Producers** (iafdb-pipeline, synthetic-egm-pipeline) bump their `myocard-egm-data` +
   `myocard-egm-contracts` pins, update producer-side code, round-trip-test via the validators.
   Tag + push.
4. **Consumers** (egm-classifier, egm-studio) bump their pins and update any code that reads the
   changed fields.

This sequence holds regardless of which schema changes. It is the canonical reference the
egm-data and iafdb-pipeline roadmaps point back to instead of re-listing bumps.

## Won't-do (out of scope, but documented to save the question)

- **No HDF5 / CSV / JSON I/O code in this repo.** Schemas + validators + codegen scripts only;
  every read and write goes through `myocard-egm-data` (or the producers). An `h5py` import
  outside the validators is a smell.
- **No torch dependency.** Pydantic, jsonschema, numpy, h5py are the runtime deps — the
  no-torch schema layer is exactly what makes a C++ deployment runtime able to read the model
  metadata sidecar without Python's ML stack.
- **No producer- or consumer-specific helpers.** "Build the Pydantic model from a dict" is the
  API surface; conversion helpers belong in egm-data.
- **No new schemas for one-off experiments.** Each schema is a stable cross-component
  interface; if only one consumer needs it, the data lives inside that consumer until a second
  materializes.

## Open architectural questions for later

- **Should `synthetic_bank` and `iafdb_bank` converge on a shared base schema?** Both carry
  per-trace signal + metadata; a JSON-Schema `allOf` could factor out the shared shape. They
  stay separate today because the producers' code paths differ enough that schema-side
  composition isn't yet load-bearing.
- **Should the validators ship as a separate distribution** (`myocard-egm-contracts-validators`)
  so the C++ deployment doesn't pull `jsonschema`? Speculative; revisit if C++ runtime packaging
  gets painful.
- **Should `schema_info` grow a typed schema-version comparison API** (`is_compatible(declared,
  requested) -> bool`) so consumers don't roll their own SemVer parsing? Add when a third
  consumer re-implements it.
