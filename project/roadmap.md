# egm-contracts — roadmap

What's planned for future releases. Internal doc — public users see the
README and `docs/schemas/`. The schema-evolution rules (which changes
trigger minor vs major bumps, the X.Y format) are in
`project/schema_evolution.md`; this doc is the *what's coming next*
companion to that *how do we version it* reference.

Items scheduled into cross-cutting Phase work in the meta repo's
`project_plan.md` carry a `→ tracked at intracardiac-platform Phase X`
annotation; the rest are component-internal — driven by schema audits
or downstream-consumer needs.

## v0.4.0 — current release (shipped)

Scope (recap; see `docs/schemas/` for the per-schema human-readable
contract and `project/schema_evolution.md` for the versioning policy):

- Seven schemas in `src/myocard_egm_contracts/schemas/`:
  `synthetic_bank` (HDF5 bank of simulated traces),
  `iafdb_bank` (HDF5 bank of IAFDB-derived calibrated segments),
  `noise_bank` (HDF5 bank of IAFDB-derived noise segments),
  `noise_bank_run_record` (JSON sidecar capturing noise extraction
  provenance), `training_run_record` (`run.json` schema for training
  runs), `training_metrics` (CSV column contract for per-epoch
  metrics + the in-memory metric bundle), `hybrid_eval_metrics`
  (sim-to-real evaluation results), `egm_class_model_metadata`
  (deployment-time sidecar paired with each exported ONNX).
- `datamodel-code-generator` Python Pydantic codegen wired into
  `codegen/gen_python.py`; CI runs the script and asserts a clean
  diff against the committed `_generated/python/` so schema-vs-code
  drift can't slip through.
- C++ codegen stub at `codegen/gen_cpp.py` — raises
  `NotImplementedError` referencing [[feedback-schemas-json-schema-first]];
  wired up when the C++ deployment chat lands (Phase 6 TensorRT).
- `validators/` package — `validate_synthetic_bank(path)`,
  `validate_iafdb_bank(path)`, etc. Each opens the actual file
  (HDF5 / CSV / JSON), maps to the JSON-Schema-shape envelope, runs
  `jsonschema` validation, returns a typed `ValidationResult`.
- `schema_info` API (added v0.1.1) — consumers like egm-data import
  schema-level metadata (default fs_hz constants, version strings,
  field names) rather than redefining them locally.
- Most recent change (v0.4.0): redesigned `egm_class_model_metadata`
  for per-trace normalization (`zscore` / `zero2one` / `none`). The
  earlier per-channel mean/std arrays were dropped as ill-suited to
  the per-trace gain-invariance the v1 classifier wants.

## v0.4.x — planned additive bumps (minor / fix)

### v0.4.1 — align HeldOutTest.metrics to EpochRecord.val_metrics — component-internal

The `training_run_record` schema's `HeldOutTest.metrics` field shape
drifted slightly from `EpochRecord.val_metrics` during the v0.3.x
training-side rewrite — both should carry the same scalar bundle
shape (auroc, accuracy, f1, precision, recall, ece, confusion,
reliability) so consumers (egm-viewer, future egm-studio) can render
them with one code path. Additive alignment; no consumer breakage
expected.

> → Component-internal (task #275). Schedule when convenient; doesn't gate a phase.

## v0.5.0+ — concrete next steps

These are sized for "could land in one focused PR each" but several
are gated on downstream consumers' needs landing first. Order is
suggestive; pick by which Phase is closest.

### Polymorphic stimulation schema (replace `stim_edge`) — Phase 2

The current `synthetic_bank` schema carries `stim_edge` as a single
enum field describing how each simulation was stimulated. That works
for v1's single `PlanarEdgeStimulus` but doesn't extend to the
richer activation sources scheduled into Phase 1.5 / Phase 2 / Phase 4
(`PointStimulus`, `S1S2Protocol`, `PacingTrain`, multi-edge stim).

The plan: replace `stim_edge` with a polymorphic `stimulation`
object (type discriminator + per-type params). Coordinated bump:
egm-contracts v0.5.0 + egm-data (cascade) + synthetic-egm-pipeline
in one release. Schema migration noted in
`project/schema_evolution.md`.

> → Tracked at `intracardiac-platform/project/project_plan.md` Phase 2 (first-publish milestone — bundling the schema bump here avoids fragmenting the polymorphic-stimulation work across multiple releases). The producer-side scope is in synthetic-egm-pipeline's roadmap under "Additional activation sources."

### `iafdb_bank` 1.2 — audit-report sidecar pointer — Phase 1.5

Add an optional `run_record_path` field to the `iafdb_bank` schema
attrs so the healthy bank can carry a paired JSON sidecar with
per-record diagnostic data, symmetric with how `noise_bank` already
pairs with `noise_bank_run_record`. The sidecar schema itself is
either a new top-level `iafdb_bank_run_record` schema or a reuse of
the existing `noise_bank_run_record` structure — decide during
implementation.

> → Tracked at `intracardiac-platform/project/project_plan.md` Phase 1.5. Pairs with iafdb-pipeline's per-record audit reports work; ships together.

### `noise_bank` 1.1 — `calibration_scalar` per-trace column — Phase 1.5

Add an optional `calibration_scalar` per-trace column so iafdb-pipeline's
opt-in noise-side calibration can be expressed in the schema without
breaking older readers. Default = NaN means "uncalibrated"; explicit
scalar means "this much gain was applied before the noise segment was
extracted."

> → Tracked at `intracardiac-platform/project/project_plan.md` Phase 1.5. Pairs with iafdb-pipeline's opt-in noise-calibration roadmap item.

### `noise_bank_run_record` 1.1 — `per_trace_provenance.lead` — Phase 1.5

Add a `lead` field to the per-trace provenance dict so the noise sidecar
records which surface lead won the calibration's priority-order
selection (when noise-side calibration is on). Ships with the
calibration_scalar work above.

> → Tracked at `intracardiac-platform/project/project_plan.md` Phase 1.5.

### `egm_features_bank` schema — Refactor Step 4 (egm-features)

When `egm-features` ships and emits per-trace feature bundles, the
output format wants a contract. Likely shape: HDF5 bank with one
column per feature + a feature-name list in attrs + a hash of the
source bank for traceability. Same convention as the other banks
(traces table + per-trace metadata).

> → Tracked at `intracardiac-platform/project/refactor_checklist.md` Phase 4 (egm-features). Don't land the schema until the producer's feature list stabilizes; otherwise the schema churns.

### 3D geometry schema — Phase 7 (3D substrate)

When synthetic-egm-pipeline grows `AtrialMesh3D` for the Phase 7 3D
substrate work, the `synthetic_bank` schema needs to express which
mesh produced the simulation. Likely shape: `mesh_path` (relative
reference to a `.pts/.elem/.lon` triple in an external mesh repo or
local mesh directory) + a content hash for reproducibility. Bigger
question — does the project want a separate `atrial_mesh_3d` schema
defining the mesh format itself, or do we delegate to existing
unstructured-mesh formats (e.g. openCARP's native `.pts/.elem/.lon`)?
Decide during the Phase 7 kickoff.

> → Tracked at `intracardiac-platform/project/project_plan.md` Phase 7.

### C++ codegen activation — Phase 6 (TensorRT deployment)

The `codegen/gen_cpp.py` stub gets filled in here. Likely toolchain:
`quicktype` or `nlohmann/json-schema-codegen` emitting headers into
`_generated/cpp/`. CI gains a parallel C++ drift check. Consumer:
the C++/TensorRT runtime that loads `egm_class_model_metadata.json`
and applies the documented preprocessing pipeline.

> → Tracked at `intracardiac-platform/project/project_plan.md` Phase 6.

### Normalization scheme expansion (`robust_zscore`, `meanvar`) — open question

The `egm_class_model_metadata` schema currently admits
`zscore` / `zero2one` / `none` for per-trace normalization. Future
classifier work might want `robust_zscore` (median + MAD) or
`meanvar` (with stored per-channel stats once we go multi-channel).
Add when a real model needs them — speculative until then. See
egm-classifier roadmap "Open architectural questions for later."

> → Component-internal / deferred. No phase home until a consumer needs it.

## Schema bumps to coordinate (cascade order)

When any schema in this repo changes, the downstream cascade is fixed:

1. **egm-contracts** ships the new schema version. Tag + push.
2. **egm-data** updates its readers + writers to satisfy the new
   shape. Bumps its pinned `myocard-egm-contracts` version. Tag + push.
3. **Producers** (iafdb-pipeline, synthetic-egm-pipeline) bump their
   pinned `myocard-egm-data` + `myocard-egm-contracts` versions,
   update any producer-side code, run round-trip tests via the
   validators. Tag + push.
4. **Consumers** (egm-classifier, future egm-studio) bump their pins,
   update consumer-side code if the schema change affects fields they
   read.

This is the canonical sequence regardless of which schema is
changing. The "Schema bumps to coordinate" section in iafdb-pipeline's
roadmap (which historically listed the iafdb_bank 1.2 / noise_bank 1.1
items) is now redundant — those items live here; iafdb-pipeline's
section will be pruned to just "see egm-contracts roadmap for the
next bumps + cascade order" in the 2026-06-23 audit cleanup.

## Won't-do (out of scope, but documented to save the question)

- **No HDF5 / CSV / JSON I/O code in this repo.** Schemas + validators
  + codegen scripts only. Every read and write goes through
  `myocard-egm-data` (or `myocard-iafdb-pipeline` and
  `myocard-synthetic-egm-pipeline` for producer-side writes). If this
  repo's source tree grows an `h5py` import outside the validators,
  it's a smell.
- **No torch dependency.** Pydantic, jsonschema, numpy, h5py are the
  runtime deps; no PyTorch. The schema layer is what makes a
  no-torch deployment runtime possible (C++ deployment doesn't need
  Python's ML stack to read the model metadata sidecar).
- **No producer- or consumer-specific helpers.** "Build the Pydantic
  model from a dict" is the API surface; if a consumer needs
  conversion helpers, those belong in egm-data, not here.
- **No new schemas for one-off experiments.** Each schema is a stable
  cross-component interface — if only one consumer needs it, the
  data lives inside that consumer until a second consumer
  materializes.

## Open architectural questions for later

- **Should `synthetic_bank` and `iafdb_bank` converge on a shared
  base schema?** Both carry per-trace signal + per-trace metadata;
  the differences are which metadata fields exist. A JSON-Schema
  `allOf` composition could factor out the shared shape. Today the
  two stay separate because the producers' code paths are different
  enough that schema-side composition isn't yet load-bearing.
- **Should the validators ship as a separate distribution
  (`myocard-egm-contracts-validators`) so the C++ deployment doesn't
  pull `jsonschema`?** Today the validators are always installed
  with the schemas. Splitting is speculative; revisit if C++ runtime
  packaging becomes painful.
- **Should `schema_info` grow a typed schema-version comparison API**
  (e.g. `is_compatible(declared, requested) -> bool`) so consumers
  don't roll their own SemVer parsing? Add when a third consumer
  re-implements this.
