# egm-contracts — Phase 1.5 implementation plan

**Repo:** egm-contracts · **Phase:** 1.5
**Phase design doc:** `intracardiac-platform/phases/phase_1_5/design.md`
**Status:** in progress · **Progress:** 7/13 steps done (S1–S6, S6b) — **egm-data's S10 is
unblocked** (the `train_*` CSV columns landed); the `synthetic_bank` restructure (S7–S11) is what
remains
**Repo estimate:** **14–29.5 h** active (Cx **15** points) — the project-lead reads this into design §6;
this chat does not edit the design doc.

This repo is Wave 1 of the phase: the whole constellation is gated on the coordinated
**v0.6.0** bump, so everything here lands before egm-data (v0.5.x) and the producers/consumers re-pin.

---

## Scope — what this plan covers

The design's §3 rows for this repo are **CON1** and **CON3**, but the coordinated bump is the *union*
of the core §3 work **and** four backlog-driven schema touches (the coverage note in
`intracardiac-platform/project/cross_artifact_linkage_design.md`). All six groups ship in one PR and
one tag, so all six are estimated here.

| Phase item | Proposed-changes group | What it needs from this repo | Steps |
|---|---|---|---|
| CON1 | P2 | `synthetic_bank` **2.0** restructure — new `simulation_config` schema (7 per-function polymorphic objects), `TunedParam` / `generation_params` θ-spec, `simulations/` group, `traces/` collapse, int label, **per-trace `activation_position`** (CL-060/CL-062) | S7–S11 |
| CON3 | P1 | `training_run_record` **1.2** — `EpochRecord.train_metrics`; `HeldOutTest` ↔ val-bundle parity (B18); documented conventions for dropped `hostname` (B15) + relative paths (B14) | S6 |
| CON3 | P1 (7th line item) | `training_metrics` — six nullable `train_*` CSV columns + paired `x-csv-column-order` (CL-037 → CL-024; **blocks egm-data S10**) | S6b |
| B16 | P3 (contracts half) | `common.schema.json` `ArtifactId` **role-prefix validation**, single-sourced against `codegen/roles.json` | S2 |
| B19 · B17 | P4 | `phase_manifest` — `produced_by_package` / `produced_by_version` out of every entry's `required`; **`path` descriptions** across all 7 entries corrected to relative-to-phase-folder (CL-051) | S5 |
| B20 | P5 | `noise_bank` **1.1** — root `bank_id` (`$ref ArtifactId`, optional-in-schema / required-on-write) | S3 |
| B11 · IAF3 | P6 | `iafdb_bank` **1.3** — optional root `run_record_path` sidecar pointer **+ per-trace `activation_position`** (`[0,1]`, optional; CL-052/CL-053) | S4 |
| — | — | Repo housekeeping + phase-exit docs (CHANGELOG, roadmap trim, README, pre-PR run) | S1, S12 |

**Not this repo:** P3's other half — now just the egm-data id-content check, since the `ClassifierBank`
`split` / `prediction` columns turn out to be already shipped (CL-037 item 4) — plus every
reader/writer (DAT1 / DAT3) and all producer/consumer adoption. `CLF4b`'s
predictions format stays egm-classifier-owned — there is no `classifier_predictions` JSON Schema here,
and this plan does not add one. **B17** (phase-storage: copying artifacts into `phases/<type>/` +
relative manifest paths) is **egm-studio's**, not ours — see the open item on S5. The egm-studio
θ-escalation likewise adds no issue here: the θ-spec is already CON1, and putting θ into
`ClassifierTrace.trace_metadata` is egm-data behavior on an existing `dict[str, Any]`, not a schema
change.

## Dependencies — what this repo's issues wait on

egm-contracts sits at the **root of the dependency DAG**, so this table is empty by construction: no
step here waits on another repo. The traffic runs the other way — every Wave-1 adoption (DAT1 · DAT3 ·
SEP12 · STU6 · IAF3 · CLF5) waits on the v0.6.0 tag, which is why this repo goes first in §7 Track A.

| This repo's issue/step | Depends on (repo · issue / artifact) | Why | Status |
|---|---|---|---|
| — | none | root of the DAG; nothing upstream of the schemas | n/a |

One **inbound** dependency is worth naming even though it isn't mine to track: egm-data's DAT1 writer +
reader, the four producer/consumer migrations, and everything in Waves 2–3 that touches a changed type
are all gated on the tag. That makes S12 (the pre-PR run) the wave's real bottleneck, not S1.

## Work remaining / open items

| Item | Kind | Blocked on | Status |
|---|---|---|---|
| S3–S12 not started (S1 landed with the plan commits; S2 done 2026-07-30) | step | — | open |
| Confirm the polymorphic `oneOf` + `const` discriminator codegens cleanly through datamodel-code-generator | open-question | — (resolved inside S7; fallback noted in Design notes) | open |

No cross-chat blockers: B17 was answered (CL-051), the join key needs no CON change (CL-012 → CL-024
§3), and both `activation_position` flow-downs are folded in (CL-053, CL-062). Nothing here waits on
another chat.

## Design notes

- **One `simulation_config.schema.json`** *(Daniel, 2026-07-28)*. The seven per-function polymorphic
  objects (`geometry` / `cell_model` / `substrate` / `activation` / `electrodes` / `backend` /
  `label_policy`) plus `TunedParam` + `generation_params` live as `$defs` in a single new schema file;
  `synthetic_bank.schema.json` reaches them by cross-file `$ref`, the same mechanism
  `common.schema.json` already uses (the validators' `referencing.Registry` resolves it). Rationale:
  codegen emits one importable module for egm-data / synthetic-egm-pipeline / egm-studio to share,
  `synthetic_bank.schema.json` stays readable, and the objects are reusable if a later schema needs
  them — without eight new files, modules, and docs pages for objects that only appear inside a bank.
  Like `common`, it is a `$defs` library, not a document format: no document validator, nothing on disk
  in that shape.
- **Polymorphism encoding.** Each function is `oneOf` over per-variant subschemas, each pinned by a
  `type` `const`. S7 verifies this codegens to a clean discriminated union through
  datamodel-code-generator before the shape is committed everywhere; fallback is the JSON Schema
  `discriminator` annotation or plain per-variant `$defs` + a `Union` alias.
- **Role-prefix single-sourcing without generating a schema.** The JSON Schema stays hand-written
  truth (JSON-Schema-first), so `ArtifactId`'s pattern carries an explicit prefix alternation and a
  unit test asserts that alternation matches `codegen/roles.json`. That keeps the vocabulary in one
  place without making a schema file a codegen output. `fig_` / `paper_` are deliberately excluded
  from the `ArtifactId` alternation — they have their own `FigureId` / `PaperId` patterns — so the
  consistency test asserts the intended 8-of-10 subset, not blind equality.
- **`x-hdf5-mapping` grows a `simulations_group`.** The HDF5 validator currently reads root attrs +
  the `traces/` group; it gains the `simulations/` group and decodes each `*_json` column **per row**
  (a handful of rows per bank) before validating.
- **No back-compat.** `synthetic_bank` `schema_version` enum becomes `["2.0"]` only — no 1.1 reader,
  no migration path (design investigation §8.2: nothing released is load-bearing). A 1.1 bank simply
  fails validation, which is the intended signal.
- **Conventions vs fields.** B14 (relative paths), B15 (drop `hostname`), and B17 (relative in-phase
  `path`) are *producer conventions*, not schema fields — this repo's deliverable for them is the
  documented well-known-key list and description text, and nothing else.

## Steps

Ordered so the shared `common.schema.json` change lands **first**: it re-generates the ArtifactId
pattern into nine model files, and doing it before the restructure means the new `synthetic_bank` /
`simulation_config` models are generated against the final pattern instead of being regenerated twice.
S2–S6 are otherwise independent of each other and of S7–S11.

Every step ends green: `ruff format src tests` → `ruff check src tests` → `mypy src` → `pytest`, plus
`python codegen/gen_python.py` with a clean drift check whenever a schema changed.

### S1 — Clean the working tree ☐ (~10 m)
- **Change:** commit the already-edited `project/roadmap.md` note (the `stimulation` schema pulled
  forward from Phase 2 to 1.5) as its own `[Documentation]` commit so the phase work starts from a
  clean tree.
- **Verify:** `git status` clean on `development`.
- **Depends on:** none.

### S2 — `common.schema.json` — role-prefix validation (B16 / P3) + shared `ActivationPosition` ✅ (1.5–3 h)
- **Change:** tighten the `ArtifactId` pattern from `^[a-z]+_` to an explicit alternation of the eight
  known artifact roles (`tbank_` / `ptbank_` / `lpred_` / `upred_` / `nbank_` / `run_` / `model_` /
  `obs_`); update the description. Re-run codegen (nine model files inline the pattern). New test
  asserting the alternation is exactly the `codegen/roles.json` roles minus `fig_` / `paper_`, so the
  two can't drift.
- **Also add a shared `$defs.ActivationPosition`** — number, `minimum: 0`, `maximum: 1`, with the
  fraction convention (`idx = round(frac·(T−1))`) and the optional-in-schema / required-on-write note in
  its description. `iafdb_bank` (S4) and `synthetic_bank` (S9) both `$ref` it rather than declaring the
  field twice. **Why:** CL-057/CL-060 want STU5 comparing **stored-vs-stored** across the two corpora,
  which only holds if both sides mean exactly the same thing by the number — that's a single definition's
  job, and it's the same argument that put `ArtifactId` here in the first place. Divergent copies of a
  "same" field is precisely how the `sim_id` / `simulation_id` split happened.
- **Verify:** new unit test (valid ids per role pass; `xbank_foo` / `bank_foo` now rejected; every
  existing fixture id still validates); codegen drift check clean; `tests/test_roles.py` still green.
- **Depends on:** S1.

### S3 — `noise_bank` 1.1 — `bank_id` (B20 / P5) ✅ (1–2 h)
- **Change:** add optional root `bank_id` (`$ref common.schema.json#/$defs/ArtifactId`) +
  `x-hdf5-mapping.root_attrs`; `schema_version` enum → `["1.1"]`; regen; `schema_evolution.md`
  `noise_bank` change-log entry.
- **Verify:** fixture noise bank gains a `nbank_…` id and round-trips; a bank *without* `bank_id`
  still validates (optional-in-schema); a bad-prefix id fails (S2's tightened pattern).
- **Depends on:** S2.

### S4 — `iafdb_bank` 1.3 — `run_record_path` + `activation_position` (B11 · IAF3 / P6) ✅ (0.75–2 h)
- **Change:** add optional root `run_record_path` (string, relative sidecar pointer, mirroring the
  `noise_bank` ↔ `noise_bank_run_record` convention) + `root_attrs`. **Also add per-trace
  `activation_position`** to `traces/` — `$ref` to S2's shared `ActivationPosition` (`[0,1]`),
  **optional in-schema / required-on-write in activation mode**, the realized activation position
  within each IAFDB window (the IAFDB counterpart of SIG1's `AnchoredWindow.realized_position`). `schema_version` enum → `["1.3"]`; regen; `schema_evolution.md` entry. **Not** in scope:
  a formal `iafdb_bank_run_record` schema — deferred per the P6 flag, recorded in `roadmap.md` as the
  trigger.
- **Why the position field is here:** without it STU5 compares a *measured* synthetic distribution
  against an *assumed* real one, and T1's central claim stops being checkable from the artifacts
  (CL-052 → CL-053). The field lands **unpopulated in Wave 1**; IAF1 fills it in Wave 2, which is
  exactly why it's optional rather than required.
- **Verify:** fixture bank with and without the pointer both validate; a trace column of positions in
  `[0,1]` validates and one outside the range is rejected; a bank with **no** `activation_position`
  still validates (the Wave-1 case); docs page updated.
- **Depends on:** S2.

### S5 — `phase_manifest` — `produced_by_*` optional (B19) ✅ (0.5–1.5 h)
- **Change:** remove `produced_by_package` + `produced_by_version` from the `required` array of all
  seven entry `$defs` (`EgmBankEntry`, `NoiseBankEntry`, `TrainingRunEntry`, `ModelEntry`,
  `ObservationEntry`, `FigureEntry`, `PaperEntry`), keeping them as optional properties.
  `schema_version` stays `"1"` (loosening `required` is backward-compatible). **Also fix the `path`
  descriptions on all seven entries** — `EgmBankEntry.path` currently reads "relative to the meta repo
  (or absolute)", which is wrong under phase-storage; give all seven the same relative-to-the-phase-folder
  one-liner so the convention lives in the contract rather than only in egm-studio's implementation.
  `path` stays an unconstrained `type: string` — no structural change. Regen.
- **B17 answered (CL-049 → CL-051):** phase-storage needs **nothing structural** here, and this step
  does **not** gate egm-studio's S12 — the description fix is a free rider on v0.6.0 (or a harmless
  v0.6.1). That closes the only open question this plan was carrying.
- **Verify:** an entry omitting both `produced_by_*` validates; one supplying them still validates;
  existing manifest fixtures unchanged and green.
- **Depends on:** S2.
- **CI note:** this is the one changed schema whose `schema_version` does *not* move, so the
  `schema-version-bump` job will flag it as DRIFT — the PR needs the `skip-schema-bump` label. In a
  single combined PR that label switches the job off for **all six** schemas, so S12 runs the checker
  locally instead and records its output (see below). Justification for the reviewer: loosening a
  `required` array is backward-compatible, and `phase_manifest` is a major-only enum-of-one.

### S6 — `training_run_record` 1.2 (CON3 / P1) ✅ (1.5–3 h)
- **Change:** add `$defs.EpochRecord.train_metrics` — object, **optional in-schema** (deliberately
  *not* in `required`), mirroring `val_metrics` (auroc / accuracy / precision / recall / f1 / ece +
  optional nested `confusion`, `additionalProperties: true`). **Optional-in-schema /
  required-on-write**, the same convention the bank ids use: Wave-1 (CLF5) has to write valid records
  before CLF2's emit exists, so a hard-required field would drag the emit into Wave 1 and collapse the
  migration/feature wave split. The write-time requirement is enforced downstream (producer +
  egm-data) when CLF2 lands in Wave 2 — the docs page states that explicitly so the optionality isn't
  read as "nice to have". Bring `$defs.HeldOutTest` to parity with the val bundle (`metrics`
  keyset mirrors `val_metrics` incl. nested `confusion`; `reliability` mirrors `val_reliability`) —
  a description/validator tightening, no new fields (B18), with the "test metrics come from the
  **best** epoch, not the last" producer semantic written into the description. Drop `host` from the
  documented well-known `run` keys (B15) and record artifact paths as repo-relative in the `config`
  description (B14) — both convention-only, `additionalProperties: true` unchanged. `schema_version`
  enum → `["1.2"]`; regen; `schema_evolution.md` entry. **Out of scope:** `train_reliability` bins
  (FB-10).
- **Verify:** a record carrying per-epoch `train_metrics` round-trips; a record **omitting** it still
  validates (the Wave-1 CLF4 case — this is the assertion that protects the wave split, so it gets its
  own named test); a malformed `train_metrics` (wrong type) is rejected; a `HeldOutTest` in the
  aligned shape validates. Existing run-record fixtures stay valid unchanged — one fixture gains the
  field to cover the populated path.
- **Depends on:** S2.

### S6b — `training_metrics` — the six `train_*` CSV columns ✅ (0.5–1.5 h)
- **Change:** add `train_auroc` / `train_accuracy` / `train_precision` / `train_recall` / `train_f1` /
  `train_ece` — all `["number", "null"]`, optional, mirroring their `val_*` twins' bounds and
  null-semantics — and rewrite `x-csv-column-order` **paired** (`epoch, lr, train_loss,
  train_auroc…train_ece, val_loss, val_auroc…val_ece, epoch_seconds`) rather than appending the train
  block at the end: T5 exists to make train-vs-val divergence readable. No `train_reliability` (the
  CSV carries scalars only; FB-10 stands). Regen; docs page updated.
- **Why it's here and not optional:** the schema is `additionalProperties: false`, so an un-bumped
  validator actively **rejects** the new CSV — this blocks egm-data's S10, and missing v0.6.0 slips it
  a whole release (CL-037 item 1, adjudicated in CL-024).
- **Verify:** a row with all `train_*` populated validates; a row with them absent still validates
  (the pre-CLF2 Wave-1 case); a row with an out-of-range value is rejected; `x-csv-column-order`
  matches the property set exactly (worth a test — the two drift silently otherwise).
- **Version note:** `training_metrics` carries **no `schema_version` property** (it's a CSV row), so
  there's nothing to bump and `check_schema_versions.py` classifies it as NEW rather than DRIFT — it
  won't add to S5's label problem.
- **Depends on:** S2.

### S7 — `simulation_config.schema.json` — the per-function objects ☐ (2.5–5 h)
- **Change:** new schema file holding the seven `type`-discriminated `$defs` with their Phase-1.5
  variants: `geometry.patch2d {size_mm, dr_mm}`; `cell_model.courtemanche {params}` +
  `aliev_panfilov {ap_time_unit_ms, …}`; `substrate.uniform_random {density}`;
  `activation.planar_edge {edges[], voltage, time_model_units, strip_thickness}` / `point
  {position_mm[], voltage, time_model_units}` / `s1s2 {s1_interval_ms, s2_interval_ms, site}`;
  `electrodes.centered_grid_2d {rows, cols, spacing_mm, height_mm_range, pairs:[{pair_index,
  electrode_row, height_mm, midpoint_mm[]}]}`; `backend.finitewave {…}`;
  `label_policy.global_density {threshold}` / `local_density {radius_mm, threshold}`. Position arrays
  are coordinate arrays sized by the active geometry — nothing hard-codes 2. Codegen wired in.
- **Verify:** each variant validates a hand-written example and rejects a wrong-`type` payload;
  generated models import and discriminate on `type` (the fallback in Design notes if the union is
  ugly); drift check clean.
- **Depends on:** S2.

### S8 — `TunedParam` + `generation_params` θ-spec ☐ (1–2 h)
- **Change:** add to `simulation_config.schema.json`: `TunedParam {path, bounds[2], transform:
  identity|log|logit, role: label_param|nuisance, nominal?}` and `generation_params {regime,
  knobs:[TunedParam]}` — membership deliberately open (set per sweep by the §8.2 screening), shape
  typed. **`path` stays a plain string — no grammar, no pattern** (CL-024 §2 defers the path grammar
  out of v0.6.0 along with the generic resolver); it's an opaque pointer this phase, and constraining
  it later is additive. Regen.
- **Verify:** a trivial θ-spec (regime only, empty `knobs`) validates — that's what SEP12 writes in
  Wave 1; a multi-knob spec validates; a bad `transform` / `role` is rejected.
- **Depends on:** S7.

### S9 — `synthetic_bank` 2.0 restructure ☐ (1.5–3 h)
- **Change:** `schema_version` enum → `["2.0"]`. Root attrs reduce to `schema_version`,
  `created_utc`, `bank_id`, `description`, `fs_hz`, `trace_duration_ms`, `noise_bank_source` +
  `generation_params_json` (the θ-spec). New `simulations` group — `simulation_id`, `seed`, and the
  `*_json` columns (`geometry`, `cell_model`, `substrate`, `activation`, `electrodes`, `backend`,
  `label_policy`, `label_names`, `substrate_summary`), each `$ref`-ing S7's `$defs`. `traces/`
  collapses to `signal`, `simulation_id`, `pair_index`, `label` (int), `snr_db`, `noise_record`,
  `noise_channel` — dropping `electrode_row`, `electrode_height_mm`, `fibrosis_density`,
  `fibrosis_density_realized`, `seed`, `stim_edge`. **Plus `activation_position`** — the same `$ref`
  to S2's shared `ActivationPosition`, **optional**: absent in Wave 1 (SEP12 has no controlled crop
  yet), populated by SEP2 in Wave 2 (CL-060 → CL-062). `x-hdf5-mapping` gains `simulations_group`.
  Regen.
- **Why the position column is free now and expensive later:** `synthetic_bank` is *the* breaking
  change this phase, so it costs nothing while 1.1 → 2.0 is already open; adding it after the tag means
  breaking a schema we just broke.
- **Verify:** the schema self-validates; a v2.0 document validates; a 1.1-shaped document is rejected;
  a v2.0 bank **without** `activation_position` validates (the Wave-1 SEP12 case) and one with a value
  outside `[0,1]` is rejected — the same pair of assertions as S4, so the two corpora can't drift apart;
  drift check clean.
- **Depends on:** S8.

### S10 — v2.0 validator + fixtures ☐ (1.5–3 h)
- **Change:** `validators/synthetic_bank.py` reads the `simulations/` group and decodes its per-row
  `*_json` columns (extend `_hdf5.py` if the per-row decode is reusable); drop the old
  `_JSON_ENCODED_ATTRS` root mapping except `generation_params_json`. Rewrite the `valid_synthetic_bank`
  fixture in `tests/conftest.py` to the v2.0 shape (2 sims × a few pairs), plus negative cases.
- **Verify:** `pytest` green including a full HDF5 round-trip of a v2.0 bank; negative cases (missing
  `simulations/`, unknown `activation.type`, `label` as float, an orphan `simulation_id` FK) each fail
  with a useful message.
- **Depends on:** S9.

### S11 — `synthetic_bank` docs ☐ (1–2 h)
- **Change:** rewrite `docs/schemas/synthetic_bank.md` for 2.0 (structure, the per-sim / per-trace
  split, the FK join, the θ-spec); add `docs/schemas/simulation_config.md`; `schema_evolution.md`
  `synthetic_bank` entry recording the breaking 2.0 restructure + the deliberate no-migration
  decision; retire the `stim_edge` migration note in `project/known_issues.md`.
- **Verify:** `docs/schemas/README.md` index lists the new page; every field in the docs exists in the
  schema (read the diff against the schema side by side).
- **Depends on:** S10.

### S12 — Phase-exit docs + PR ☐ (1–2 h)
- **Change:** `CHANGELOG.md` `[Unreleased]` → the v0.6.0 entry naming all six groups and the
  `schema_version`s; `roadmap.md` trimmed of everything shipped (the `iafdb_bank` 1.3 section, the
  `bank_id` half of `noise_bank` 1.1, the pulled-forward `stimulation` section, the `HeldOutTest`
  align backlog item, and the two shipped refactor-cleanup-batch bullets) with the deferred remainder
  restated (noise-side `calibration_scalar`, `noise_bank_run_record` 1.2 `lead`, the `observation`
  `view_state` active-tab field, the `iafdb_bank_run_record` trigger); README schema table refreshed;
  this plan's step statuses updated.
- **Cleanup note:** `release_checklist.md` gates deleting this plan on rolling up its Effort section
  first. With actuals dropped for 1.5 (see Estimates), that gate is moot here — the plan's shipped work
  summarizes into `CHANGELOG.md` and nothing outlives it that needs preserving.
- **Verify:** the full `intracardiac-platform/project/pr_checklist.md` run, top to bottom, including
  the codegen-drift and code-placement passes. Plus `BASE_REF=release python
  tools/check_schema_versions.py` locally — its `BUMPED` lines go in the PR description as the
  human-verified substitute for the CI job that the `skip-schema-bump` label (needed for S5) turns
  off.
- **Depends on:** all prior steps.

**Post-merge (Daniel, web UI + local):** merge `development` → `release`, tag **v0.6.0**, push the tag,
sync branches. Then egm-data is unblocked (v0.5.x), and the four producer/consumer adoptions follow per
design §7 Wave 1.

## Estimates

> **Actuals are not tracked this phase** (Daniel, 2026-07-29). Flow-down tracking, organization, and
> effort measurement were missed for Phase 1.5 across the chats; Daniel + the project-lead will design
> the methodology for **future** phases rather than retrofit this one. So: no session log, no `Actual` /
> `Elapsed` columns, and **no `estimation_ledger.csv` append at cleanup** for egm-contracts. The
> estimates below stand as planning figures for design §6 — they just won't get a measured counterpart.
> The half-inferred session log that was here has been removed rather than left to imply data that will
> never arrive.

Complexity per the §8 rubric (XS 1 · S 2 · M 3 · L 5 · XL 8). The ledger is empty, so these are
cold-start **by-analogy** estimates with deliberately wide ranges — implied rate ≈ **1.0–2.0 h/point**
for schema work.

| Issue | Task-type | Cx | Estimate | Steps |
|---|---|---|---|---|
| CON1 (P2) `synthetic_bank` 2.0 | schema-restructure | 5 (L) | 7.5–15 h | S7–S11 |
| CON3 (P1) run-record 1.2 + `training_metrics` | schema-additive | 3 (M) | 2–4.5 h | S6, S6b |
| B16 (P3) `ArtifactId` role validation | schema-additive | 2 (S) | 1.5–3 h | S2 |
| B20 (P5) `noise_bank` 1.1 | schema-additive | 2 (S) | 1–2 h | S3 |
| B11 · IAF3 (P6) `iafdb_bank` 1.3 | schema-additive | 1 (XS) | 0.75–2 h | S4 |
| B19 (P4) `phase_manifest` | schema-additive | 1 (XS) | 0.5–1.5 h | S5 |
| Housekeeping + phase-exit docs | docs | 1 (XS) | 1–2 h | S1, S12 |
| **Repo total** | | **15** | **14.25–30 h** | |

Reference anchors used: CON1 sits at the same L as the design's SEP12 anchor (breaking restructure,
wave-coupled, but schema-side rather than producer-side); B20 *is* the rubric's S anchor.

**One thing worth carrying into the future methodology:** these estimates are still falsifiable without
a stopwatch. Each row maps to named steps that end in commits, so at cleanup the git history gives
calendar spans and step counts per issue — coarse, but enough to say whether an L-sized schema
restructure really did dwarf the XS additive ones. Worth a look when the method gets designed.

## Notes / decisions log

- **2026-07-28** — Plan drafted. Two forks settled by Daniel: single `simulation_config.schema.json`
  for the per-function objects; all six groups in **one PR**, one v0.6.0 tag.
- **2026-07-28** — *For the project-lead:* design §6's egm-contracts row reads `CON1 · CON3`, but this
  estimate covers **six** groups (P1–P6) per the linkage doc's coverage note — the four backlog-driven
  touches have no §3 issue yet still land in this PR. Worth reflecting in the §6 row so the phase total
  isn't short.
- **2026-07-28** — *Project-lead correction (CON3):* `EpochRecord.train_metrics` is
  **optional-in-schema / required-on-write**, not `required` — a hard-required field would force
  CLF2's emit into Wave 1 and break the migration/feature wave split; enforcement moves downstream to
  the producer + egm-data in Wave 2. S6 updated. **Flag back:** the P1 field-level detail in
  `cross_artifact_linkage_design.md` still reads "object, **required**" and now contradicts this —
  that doc is project-lead-owned, so it needs the edit there. Estimate unchanged (Cx 2, 1.5–3 h); the
  optionality removes fixture churn but adds the wave-protecting negative test.
- **2026-07-29** — *CL-024 batch adjudication + CL-037, applied here.* (1) **CON3 grew a seventh P1 line
  item** — `training_metrics` gains six nullable `train_*` columns + paired column order → new **S6b**;
  CON3 Cx 2 → **3**, 1.5–3 h → **2–4.5 h**, repo total 14 → **15 pts / 14–29.5 h**. It blocks egm-data's
  S10, so it can't slip to v0.6.1. (2) **No `TunedParam.path` grammar in v0.6.0** — S8's `path` stays an
  opaque string. (3) **Join key: no CON change** (CL-012 upheld); producer renames `sim_id` →
  `simulation_id`, egm-data adds a writer check. (4) **P3's egm-data half is already shipped**, so P3 is
  the B16 validator here + a content check there. (5) **Effort rule (§5b):** planning sessions count
  toward issue Actuals — **superseded same day, see below.**
- **2026-07-30** — *S3 review (Daniel) → two backlog items, neither fixed in 1.5.* (1) **Codegen
  emits unused `common` `$defs`** into every model module (`noise_bank.py` carries `FigureId` /
  `PaperId` / `ActivationPosition`). Cause: one generator run per schema file, each re-emitting
  common's defs. Verified fix = one run over the schemas directory; deferred because it rewrites all
  eleven generated files mid-bump and would rename the modules the public API re-exports. (2)
  **noise bank ↔ run record pairing** — `bank_id` now sits in both files with neither authoritative;
  needs a design pass, not another field. Both in `roadmap.md`; (2) raised as **CL-086** since it
  spans egm-data + iafdb-pipeline.
- **2026-07-29** — *CL-062 folded in (from CL-060):* `synthetic_bank` 2.0 `traces/` gains the same
  optional per-trace **`activation_position`** — absent in Wave 1, populated by SEP2 in Wave 2 (S9).
  **Repo-internal call while doing it:** the field is now defined **once** as
  `common.schema.json#/$defs/ActivationPosition` and `$ref`'d by both `iafdb_bank` and `synthetic_bank`
  (S2), because STU5's stored-vs-stored comparison only holds if both corpora mean the same thing by the
  number — two hand-copied definitions are how `sim_id` / `simulation_id` happened. No estimate change:
  one optional column in a schema S9 is rewriting anyway.
- **2026-07-29** — *CL-053 folded in (from CL-052):* `iafdb_bank` 1.3 gains a per-trace
  **`activation_position`** (`[0,1]`, optional-in-schema / required-on-write in activation mode) beside
  `run_record_path` — S4, estimate 0.5–1.5 → **0.75–2 h**, repo total **14.25–30 h**, Cx unchanged. The
  field ships unpopulated in Wave 1; IAF1 fills it in Wave 2.
- **2026-07-29** — *B17 closed (CL-049 → CL-051):* no structural `phase_manifest` change, and nothing of
  mine gates egm-studio's S12. Picked up the free rider instead: the `path` description on all seven
  entry `$defs` (the `EgmBankEntry` one is actively wrong under phase-storage) → S5. **This plan now
  carries no open questions.**
- **2026-07-29** — *Effort tracking dropped for Phase 1.5* (Daniel). Flow-down tracking, organization,
  and effort measurement were missed phase-wide; the methodology gets designed for future phases instead
  of being retrofitted here. The Effort section became **Estimates** — no session log, no actuals, no
  ledger append at cleanup. This also retires CL-024 §5b's effort rule for 1.5 (it stands as intent for
  the next phase) and closes my open ask for how much of 07-28 was this chat.
- **2026-07-29** — *CL-041 applied:* `ci.yml` ruff install pinned `>=0.6.0` → **`==0.15.17`**. No
  pre-commit change needed — this repo was already on `v0.15.17` (only egm-features + python-template
  carried the old `v0.6.9`). Did **not** run the 0.16 reformat, per the instruction. Reply posted as a
  new log entry; per CL-025 the status flip on CL-041 is the project-lead's to make, not mine.
- **2026-07-28** — *Cross-chat channel:* escalations now go in
  `intracardiac-platform/phases/phase_1_5/coordination_log.md` (append-only; on resume grep it for
  `[OPEN]` + `TO **egm-contracts**` and `TO **all**`). Filed **CL-012** (join key: `simulation_id` +
  `pair_index` are already required columns in CON1, so CL-005 costs us nothing either way; re CL-008,
  `simulation_id` is the contractual name and contracts can't pin the ClassifierBank's since it has no
  schema here) and **CL-013** (ruff: this repo is clean under 0.15.17 *and* 0.16.0). The B17 question
  on S5 and the two project-lead handoffs below should move into the log if they aren't answered in
  conversation — that's what makes them durable.
- **2026-07-28** — *Project-lead scope fix (P4):* our `phase_manifest` change is **B19 only**; B17 is
  egm-studio's phase-storage issue, and §7's earlier "B17/B19" bundling was an error. Bump list
  unchanged otherwise: CON1 · CON3 · B16 · B19 · B20 · B11. **Open dependency:** if egm-studio's B17
  scoping turns up a `path`-relative touch on this side, it folds into S5 + v0.6.0 (still Wave 1) —
  needs an answer before the tag. Also confirmed: the egm-studio θ-escalation creates no CON issue.
- **2026-07-28** — *One-PR consequence found during planning:* P4 (`phase_manifest`) changes a schema
  without bumping its `schema_version`, which trips the `schema-version-bump` CI job. The
  `skip-schema-bump` label is the sanctioned bypass, but on a combined PR it disables the guard for
  all six schemas — hence the local checker run recorded in S12. Splitting P4 into its own labeled PR
  is the alternative if that trade stops feeling right.
- **2026-07-28** — *For the project-lead:* once P3 ships, `cross_artifact_linkage_design.md` §1's
  Constraints note ("validates the prefix + shape, not that the prefix is a known role") becomes
  false and needs flipping at the fold-in — that doc is project-lead-owned, so it's flagged, not
  edited here.
- **2026-07-28** — *Repo-doc gap:* the per-repo chat charter names `project/architecture.md`, which
  this repo has never had (its role is covered by `README.md` + `project/schema_evolution.md`). Not
  blocking Phase 1.5; flagging rather than inventing one mid-phase.
