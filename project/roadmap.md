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

### `noise_bank` — `calibration_scalar` per-trace column

Add an optional `calibration_scalar` per-trace column so iafdb-pipeline's opt-in noise-side
calibration can be expressed without breaking older readers (default NaN = uncalibrated;
explicit scalar = gain applied before extraction).

> → Pairs with iafdb-pipeline's opt-in noise calibration, which hasn't been scheduled. The
> `bank_id` attr that used to be batched here **shipped in v0.6.0** (`noise_bank` 1.1); this
> is the remaining half, and it would be `noise_bank` 1.2.

### `noise_bank_run_record` 1.2 — `per_trace_provenance.lead`

Add a `lead` field to the per-trace provenance dict recording which surface lead won the
calibration's priority-order selection (when noise-side calibration is on). Ships with the
`calibration_scalar` work. (1.1 was consumed by the v0.5.0 `bank_id` field, so this is 1.2.)

> → Tracked at `intracardiac-platform/project/project_plan.md` Phase 1.5.

## Phase 2 — multiclass severity

Nothing scheduled. Worth noting what Phase 2 will **not** need: multiclass severity labels
require no schema change, because `LabelPolicy` takes an ascending `thresholds[]` array (N
thresholds give N+1 classes) and `LabelNames` maps any number of labels. That was the point of
generalizing them in v0.6.0 rather than shipping two binary policies.

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

### Codegen emits unused `common` `$defs` into every generated module

Every model file that `$ref`s `common.schema.json` also carries copies of common's
*other* definitions. `_generated/python/noise_bank.py`, for instance, defines `FigureId`,
`PaperId`, and `ActivationPosition` — none of which `noise_bank` uses. (`ArtifactId`
itself is *not* copied: `--collapse-root-models` inlines it into the `bank_id` field as a
pattern constraint. So what's duplicated is precisely the definitions the schema doesn't
reference.)

**Cause:** `codegen/gen_python.py` invokes datamodel-code-generator **once per schema
file**. Each run resolves `common.schema.json` independently and emits every `$def` it
finds there into that run's output module.

**Fix (verified 2026-07-30):** run the generator **once over the schemas directory**
instead of file-by-file. Confirmed in a scratch run — `noise_bank`'s module then contains
only `SchemaVersion` / `Traces` / `NoiseBank`, with the shared definitions living once in
the common module.

**Why it isn't free.** Directory mode names its outputs `<schema>_schema.py`, so either the
generator renames them afterwards or the package `__init__` aliases them; the public API
re-exports each model module by name (`myocard_egm_contracts.noise_bank`), and consumers
import through it, so the mapping has to be preserved or it's a breaking change for
egm-data / egm-studio / egm-classifier. It also rewrites all eleven generated files at once.

**Impact while it stands:** cosmetic plus one small footgun — the copies are *distinct
Python types*, so `isinstance(x, noise_bank.ActivationPosition)` is False for a
`common.ActivationPosition`. The public API exports the canonical ones, so normal use is
unaffected.

> Deliberately **not** fixed during the Phase-1.5 v0.6.0 bump (Daniel, 2026-07-30) — an
> all-files codegen churn in the middle of a coordinated schema migration would obscure the
> schema diff it's meant to verify. Schedule when no bump is in flight.

### Noise bank ↔ run record: how should the two files reference each other?

`bank_id` now exists in **both** `noise_bank` (1.1, v0.6.0) and its sibling
`noise_bank_run_record` (1.1, v0.5.0), with neither authoritative and the equality check
pushed to egm-data because JSON Schema can't compare across files. That's a duplicated
identity with a hand-maintained invariant — it works, but it wasn't designed, it accumulated.

The question isn't only `bank_id`: it's what the pairing *is*. Today it's convention only —
matching name stems in one directory, no field on either side pointing at the other, nothing
that detects a bank paired with the wrong record, or a record whose bank was regenerated.
Options worth weighing: keep the duplication and formalise the check; make the bank
authoritative and have the record reference it (a pointer, mirroring the `run_record_path`
direction `iafdb_bank` 1.3 takes); or make the record authoritative and drop the bank's copy.
Each pushes work to a different place — producer, reader, or validator.

Needs a short investigation rather than a quick edit, and it reaches **egm-data** (writes
both, would own any check) and **iafdb-pipeline** (the producer), so it isn't a
contracts-only decision.

> Raised during S3 review (Daniel, 2026-07-30): worth doing, **not** in Phase 1.5 — planning
> has already cost more than budgeted. Flagged to the project-lead for the platform backlog.

### Reevaluate the stable-ID scheme — which artifacts get which pattern

Today's split is three patterns: `ArtifactId` covers banks / runs / models / observations, while
figures and papers carry `FigureId` / `PaperId`. The boundary is **historical rather than
principled** (Daniel, 2026-07-30) — it grew from figure ids needing hyphenated inventory slugs
(`fig_F-1-5-2_…`) and no date, so they got their own grammar, and papers followed. What's worth
revisiting:

- **The name misleads.** "ArtifactId" reads as "the id of any artifact"; it means "the id of a
  pipeline *data* artifact." A reader reasonably expects `fig_` to validate against it.
- **The grammars disagree.** `FigureId` allows hyphens + uppercase and carries no date/version
  suffix; `ArtifactId` allows hyphens only inside the date and adds `_vN`. The same id can be
  valid under one and invalid under the other, in both directions.
- **`paper_` is under-specified.** Papers aren't yet defined the way figures are; when they are,
  the choice is whether `PaperId` grows date/version semantics or folds into the artifact
  grammar — better decided deliberately than by precedent.

Options to weigh when it's picked up: keep three patterns but **rename** for honesty
(`DataArtifactId`); **unify** on one grammar (breaks existing hyphenated figure ids); or keep them
separate and add an **`AnyStableId`** (`anyOf` of the three) for fields that genuinely accept any
stable id.

> **Not a pure egm-contracts call** — the ID scheme is
> `intracardiac-platform/project/cross_artifact_linkage_design.md` §1, so it needs the
> project-lead; raised to them for the platform backlog. Deliberately **not** fixed in Phase 1.5:
> the v0.6.0 bump narrowed `ArtifactId` to the eight known roles (B16) without touching the
> scheme's shape.

### Refactor-cleanup batch (from the egm-studio B10g review)

One remaining item of the original three — the other two (`phase_manifest`
`produced_by_*` optional, `noise_bank` `bank_id`) **shipped in v0.6.0**:

- Add an **active view / tab** field to the `observation` `view_state`, so *Open observation*
  can restore the active flow + sub-tab, not just banks + filter + selection.

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
