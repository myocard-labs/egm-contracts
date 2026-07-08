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
