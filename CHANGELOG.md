# Changelog

All notable changes to `myocard-egm-contracts` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the **package** version aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Two version planes coexist: this package version, and the per-schema `schema_version` (X.Y)
carried inside each schema. Which schema changes force which bump is governed by
[`project/schema_evolution.md`](project/schema_evolution.md); this log records what actually
changed per release and names the affected `schema_version`s. Entries are per-version from
`v0.5.0` on; the beta that built the seven-schema baseline (`v0.1.0`–`v0.4.1`) is summarized
under [Earlier versions](#earlier-versions).

## [Unreleased]

Phase-1.5 Wave 1 — the coordinated **v0.6.0** schema bump. Accumulating; ships as one release
(the whole constellation re-pins to it, so it lands as a single tag).

### Changed — breaking

- **`synthetic_bank` 2.0 — generation config reorganized by function.** Parameters moved out
  of `traces/` into a new **`simulations/`** group (one row per simulation) holding typed
  polymorphic objects; `generation_params` became the bank-scoped **θ-spec** at root attrs; the
  label became a plain **int** with its policy and `{int: name}` map recorded per simulation.
  `traces/` is now signal + two foreign keys + label + noise provenance, plus the optional
  `activation_position`.

  Each removed column encoded a Phase-1 assumption — a scalar `fibrosis_density` presumes a
  uniform-random draw, a four-value `stim_edge` presumes a planar wave on a 2D patch — so a new
  cell model, substrate or stimulus forced either new columns or a silent change of meaning in
  an existing one. They were also per-trace copies of per-simulation facts.

  **No migration path:** a 1.1 bank is refused rather than partially read, since a partial read
  would drop the generation config. Affordable only because nothing released depends on a 1.1
  bank; the same call after publication would not be available. Resolves the long-standing
  `stim_edge` entry in `known_issues.md`.

### Added

- **`simulation_config.schema.json`** *(new)* — shared `$defs` for the per-simulation generation
  config: seven `type`-discriminated unions (geometry / cell_model / substrate / activation /
  electrodes / backend / label_policy) whose discriminators mirror the producer's `specs.py`
  exactly. A new substrate type or stimulus protocol extends a union rather than touching the
  bank. Label policies take an ascending `thresholds[]` array, so multiclass severity needs no
  new variant.

- **`generation_params.schema.json`** *(new)* — shared `$defs` for the bank-scoped θ-spec
  (`TunedParam` + `GenerationParams`): which knobs a sweep varied, over what ranges, in which
  structural regime. Kept separate from `simulation_config` because one describes a single
  simulation and the other a whole sweep. A `TunedParam` stores no value — it points into the
  per-simulation config by an opaque dotted `path`, so there is never a second source of truth
  for the same number.

- **`common.ActivationPosition`** — the shared `[0,1]` activation-position fraction (`idx =
  round(frac * (T - 1))`), defined once in `common.schema.json` and `$ref`'d by both
  `iafdb_bank` and `synthetic_bank`, so the synthetic↔IAFDB position distributions are compared
  stored-vs-stored without the two corpora being able to drift apart. Optional-in-schema /
  required-on-write in activation mode: Wave-1 banks are written before the splitters populate
  it.

- **`training_metrics` — six nullable `train_*` CSV columns.** `train_auroc` / `train_accuracy`
  / `train_precision` / `train_recall` / `train_f1` / `train_ece`, mirroring their `val_*`
  twins, with `x-csv-column-order` rewritten to **pair** the blocks (`epoch, lr, train_loss,
  train_*, val_loss, val_*, epoch_seconds`) rather than append train at the end — the point of
  carrying both is reading their divergence, which only reads clearly when the pairs are
  adjacent. The schema is `additionalProperties: false`, so an un-bumped validator actively
  rejects a CSV carrying these columns; they had to land before any producer could emit them,
  which is why this is in v0.6.0 rather than with the emit (CL-037). No `schema_version` — a
  CSV row has nowhere to put one. `train_reliability` bins stay out of scope (FB-10).

- **`training_run_record` 1.2 — per-epoch `train_metrics` + `HeldOutTest` parity.**
  `EpochRecord.train_metrics` mirrors `val_metrics`, making train-vs-val divergence readable
  from the record (with validation metrics alone, overfitting and a hard task look the same).
  Optional-in-schema / required-on-write: the migration lands before the emit, so records
  written in between stay valid. `HeldOutTest.metrics` moved from flat-scalars-only to
  `additionalProperties: true`, matching `val_metrics` — it previously rejected the very
  bundle the producer already wrote per epoch, because that bundle carries a nested
  `confusion` (B18). The block's producer semantic is now stated: test metrics come from the
  **best** epoch's weights, not the last. Two conventions ride along with no structural
  expression: `host` left the well-known `run` keys (B15) and config artifact paths are
  repo-relative (B14).

- **`phase_manifest` — `produced_by_*` optional; `path` is phase-folder-relative.** The
  producer fields left every entry type's `required` array (B19), so the curator can index a
  hand-added or externally-produced artifact instead of stamping `"unknown"` / `"0"` sentinels
  that read like real provenance; `id` + `path` stay required. The `path` descriptions were
  corrected across all seven entry types — `EgmBankEntry` claimed "relative to the meta repo",
  which phase-storage made wrong, and the other six had no description (B17 / CL-051). Both
  changes are backward-compatible, so `schema_version` stays `"1"`.

- **`iafdb_bank` 1.3 — `run_record_path` + per-trace `activation_position`.** The first is a
  relative pointer to a sibling JSON run record of extraction diagnostics (B11), shipped unset
  in Wave 1 — the generator that fills it is Wave-2 work, and the record's own schema stays
  deliberately unformalized until the methods paper settles its shape. The second is the
  realized `[0,1]` activation position per window (CL-052), `$ref`ing the shared
  `common.ActivationPosition`; the column lands unpopulated and IAF1's splitter fills it in
  Wave 2. Both optional, so existing banks validate unchanged.

- **`noise_bank` 1.1 — root `bank_id`** (B20). Optional in-schema, stamped on write by
  egm-data. The id previously lived only on the sibling run record, so a consumer had to
  find and parse the sidecar before it could tell which bank it had opened; the bank is now
  self-identifying. Both copies stay, and egm-data checks they agree.

### Changed

- **`ArtifactId` now validates the role prefix** — the pattern took any `[a-z]+_` prefix; it
  now carries an explicit alternation of the eight known artifact roles (`tbank_` / `ptbank_` /
  `lpred_` / `upred_` / `nbank_` / `run_` / `model_` / `obs_`). `fig_` / `paper_` stay out:
  those are `FigureId` / `PaperId`. **Narrowing** — an id with an invented or mistyped prefix
  now fails validation instead of surfacing downstream as an unclassifiable artifact; every id
  in use is unaffected. The vocabulary remains single-sourced in `codegen/roles.json`, with a
  test asserting the pattern's alternation matches it. **Common-only bump — no per-schema
  `schema_version` change** (all models regenerate, since they inline the pattern).

## [0.5.3] — 2026-07-07

### Changed

- **`ArtifactId` date suffix is now optional** — `<role>_<name>[_YYYY-MM-DD][_vN]`.
  Auto-derived ids still stamp the creation date, but a hand-set id (e.g. a config `bank_id`
  override) may omit it. A one-line pattern relaxation in `common.schema.json`; every model
  that inlines the pattern regenerated (9 files). Backward-compatible — every existing dated
  id still validates. **Common-only bump — no per-schema `schema_version` change.**

## [0.5.2] — 2026-07-01

### Added

- **Artifact-role vocabulary** — a generated `Role` enum + id-prefix → role map
  (`ROLE_PREFIXES`), single-sourced in `codegen/roles.json` and emitted to
  `_generated/python/roles.py` by `gen_python.py` (C++ to follow, same source), plus a
  hand-written `role_of()` classifier. Consumers derive an artifact's role from its id one
  way instead of re-hardcoding prefixes. New codegen input; **no schema change.**

## [0.5.1] — 2026-06-27

### Added

- Public export of the `common` module (`ArtifactId` / `FigureId` / `PaperId`) so consumers
  (egm-data, the producers) validate ids via the shared types. **Export-only — no schema or
  codegen change.**

## [0.5.0] — 2026-06-27

Cross-artifact linkage — the schemas for organizing a phase's artifacts. See
`intracardiac-platform/project/cross_artifact_linkage_design.md`.

### Added

- **Three JSON schemas** — `phase_manifest` (a per-phase shallow index of every artifact, with
  `egm_banks` + `noise_banks` sections), `observation` (a recorded discovery, optionally
  pinning traces), `figure_spec` (a declarative spec for one publication figure).
- **`common` shared-`$defs` schema** holding the stable cross-artifact id patterns
  (`ArtifactId` / `FigureId` / `PaperId`), referenced cross-file so each pattern is defined
  exactly once; the validators gained a `referencing.Registry` to resolve those refs.

### Changed

- **Optional stable-id fields** added to five existing schemas (all optional in-schema;
  egm-data enforces them on new writes): `synthetic_bank` → 1.1 (`+bank_id`), `iafdb_bank` →
  1.2 (`+bank_id`), `noise_bank_run_record` → 1.1 (`+bank_id`), `training_run_record` → 1.1
  (`+run_id` / `+trained_on_bank_id` / `+produced_model_id`), `egm_class_model_metadata` → 1.2
  (`+model_id`).

No new runtime dependency — the linkage formats are JSON.

## Earlier versions

Pre-linkage beta (`v0.1.0` – `v0.4.1`, 2026-06-16 → 2026-06-26) — where the seven-schema
contract and its codegen/validation tooling took shape, tracked here in summary:

- **v0.1.0 – v0.1.2** — the first schemas plus the `schema_info` API (v0.1.1): schema-level
  metadata (default `fs_hz` constants, version strings, field names) consumers import instead
  of redefining locally.
- **v0.2.0 – v0.3.0** — schema renames + shape churn as the bank formats settled.
- **v0.4.0** (2026-06-23) — the stable seven-schema baseline: `synthetic_bank`, `iafdb_bank`,
  `noise_bank`, `noise_bank_run_record`, `training_run_record`, `training_metrics`,
  `egm_class_model_metadata`; `datamodel-code-generator` Python codegen (`codegen/gen_python.py`)
  with the CI codegen-drift check; the `validators/` package (each `validate_*(path)` opens the
  real HDF5/CSV/JSON, validates, returns a typed `ValidationResult`); and the `gen_cpp.py` stub
  (raises `NotImplementedError` pending the Phase 6 deployment chat). v0.4.0's own change was
  redesigning `egm_class_model_metadata` for per-trace normalization (`zscore` / `zero2one` /
  `none`), dropping the per-channel mean/std arrays as ill-suited to the classifier's per-trace
  gain-invariance.
- **v0.4.1** (2026-06-26) — removed the `hybrid_eval_metrics` schema (untenable label-free eval
  on unlabeled IAFDB; see `project/known_issues.md`).

[0.5.3]: https://github.com/myocard-labs/egm-contracts/releases/tag/v0.5.3
[0.5.2]: https://github.com/myocard-labs/egm-contracts/releases/tag/v0.5.2
[0.5.1]: https://github.com/myocard-labs/egm-contracts/releases/tag/v0.5.1
[0.5.0]: https://github.com/myocard-labs/egm-contracts/releases/tag/v0.5.0
