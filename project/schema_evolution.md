# Evolving a schema (internal — developer-facing)

This document is for **developers working on egm-contracts**: how to safely
change a `.schema.json` file, how versions move, and how CI enforces it.
External consumers of the schemas can ignore this file; they read
`docs/schemas/` for what each schema *is*.

---

## The rule (one sentence)

**If you change a schema, bump `schema_version`.** Minor bump on
`development`; major bump at release time. If you forget, CI fails.

---

## Version format

Every schema's version is stored in a `schema_version` property as a plain
`X.Y` string:

- `X` — major version. Bumps on the merge from `development` → `release`.
- `Y` — minor version. Bumps on every dev-time structural change to the
  schema while on `development`.

Examples: `"1.0"`, `"1.7"`, `"2.0"`. The schema itself is identified by its
filename (and JSON Schema `$id`); the version string only tracks the version.

`metrics` is the one exception — it has no `schema_version` field because
CSV can't easily embed one. Its versioning piggybacks on the sibling
`run_record`'s `schema_version` (they're always written as a pair).

---

## When to bump

### Bump minor (on `development`)

For any structural change:

- Required vs optional change for an existing field.
- Type change (string → integer, etc.).
- Range / enum / format constraint change.
- Field rename (== add + remove, both breaking).
- Adding a new field (required OR optional — see "Why optional fields bump too" below).
- Removing a field.
- Changing the meaning of a field (same name, different semantics).
- `$defs` changes that affect the consumer-visible Pydantic / C++ output.
  (The codegen-drift CI job verifies this; if the generated code didn't
  change, you can debate-skip the bump via label.)

### Bump major (at release time)

When opening a PR from `development` → `release`, sweep every schema with
minor changes since the last release tag and bump them to the next major
with minor reset to 0:

- `1.2` → `2.0`
- `1.7` → `2.0`
- `1.0` (no minor changes since last release) → stays `1.0`

The major bump is the consumer-visible signal that "things have changed
since you last pinned." Downstream consumers bump their pinned
egm-contracts version in their own PRs after this lands.

### Don't bump

- Description / docstring edits (typos, clarifications, added examples).
- Whitespace / formatting changes.
- Internal `$defs` reshuffling that the codegen-drift check verifies
  doesn't change consumer-visible Pydantic output.

For these cases the schema-version-bump CI check fires incorrectly.
Bypass by adding the PR label `skip-schema-bump`. Use sparingly; the
label is auditable. Reviewers should check that the label is justified
before merging.

### Why optional fields bump too

Adding an *optional* field is debatable: technically backward-compatible
(old consumers ignore it), so by strict semver it's a minor bump and no
contract break. But: any consumer that wants the new field has to know
it exists. The bump is the discovery mechanism. Treat optional-field
additions as minor bumps too.

---

## Why pre-release schemas start at 1.0, not 0.x

Software pre-1.0 uses `0.x.y` to signal "API not stable." We don't
mirror that for schemas, because:

- The schema version string is per-schema, not per-package. egm-contracts
  the package may be at `v0.1.0`, but each schema's contract is the unit
  that consumers depend on; we want a clean `X.Y` string from day one.
- The major-bump-at-release rule already telegraphs instability: schemas
  changing rapidly are visible by their minor numbers climbing fast.
- Starting at `1.0` matches reviewer expectations on the eventual paper.

---

## Mechanics of a minor bump (dev-time)

1. **Edit the schema** in `src/myocard_egm_contracts/schemas/<name>.schema.json`.

2. **Bump the minor inside the same file.** It's an `enum` of one value at
   the top:

   ```json
   "schema_version": {
     "type": "string",
     "enum": ["1.1"]   // was "1.0"
   }
   ```

3. **Update the description** with what changed and a PR/issue link.

4. **Regenerate Pydantic models:**

   ```bash
   python codegen/gen_python.py
   ```

5. **Update validators** if the schema change affects the HDF5↔JSON-Schema
   mapping. Most structural changes don't (validators are mostly format
   plumbing).

6. **Update tests.** At minimum, the round-trip test should construct a
   new-version document and write+read it.

7. **Update `docs/schemas/<name>.md`** if a field changed or was added.

8. **Commit and push.** CI runs:

   - **codegen-drift** — re-runs `gen_python.py`, fails if regenerated
     code differs from what you committed.
   - **schema-version-bump** — diffs your `.schema.json` against the base
     branch, fails if the file changed but the version constant did not.

---

## Mechanics of a major bump (release-time sweep)

When opening a PR from `development` → `release`:

1. **Identify schemas with minor changes since the last release tag.**
   Run:

   ```bash
   git log --pretty=format:"%H" $(git describe --tags --abbrev=0)..HEAD -- src/myocard_egm_contracts/schemas/
   ```

   to see which schema files were touched. (A future
   `tools/promote_to_major.py` will automate this; manual for now.)

2. **Bump each touched schema from `X.Y` → `(X+1).0`.** Update the
   schema's version constant and the description's "Last changed" notes.

3. **Regenerate Pydantic models.** `python codegen/gen_python.py`.

4. **Open the release PR.** Title: "Release egm-contracts vA.B.0 — schema
   majors: <list>". The CI guard sees the bumps; codegen-drift sees the
   regeneration; downstream consumers can read the PR title to know what
   to update.

5. **After merge, tag the release branch.** `git tag vA.B.0` per the
   package versioning convention.

---

## When NOT to add a new schema

Schemas are expensive to maintain. Add a new one only when:

- The format is **stable enough** that consumers want to depend on it.
- The format is **cross-component** — produced by one repo, read by
  another.
- The format is **on-disk** — survives the producer's process.

Don't promote to schema:

- In-process Python objects (use Pydantic models inside a consumer repo
  without committing them to egm-contracts).
- Producer-internal config files that nothing else reads.
- One-off intermediate files that get rewritten every run.

If unsure, write the format as a non-schema'd file first; promote to a
schema once a second component starts reading it.

---

## Bypassing the version-bump CI check

The CI job `schema-version-bump` is skipped when the PR carries the label
`skip-schema-bump`. Intended for:

- Description / docstring edits.
- Whitespace / formatting changes.
- Internal `$defs` reshuffling that the codegen-drift check verifies
  didn't break consumer-visible Pydantic output.

Reviewers must check that the label is justified before merging. If the
schema change *is* user-visible, ask the author to remove the label and
bump the version.

---

## Schema change log

Per-schema version history. Add a one-line entry under the relevant
schema each time you bump its `schema_version`. Each entry records
*what changed* and *why* — the actual mechanics (codegen, tests,
docs) are covered in the "Mechanics" sections above.

Schemas only appear here once they've had their first bump beyond
`1.0`; an absence from this list means the schema is still at its
introduction version.

### common

- **(v0.6.0)** — two changes, both Phase-1.5 Wave 1:
  - **`ArtifactId` role-prefix validation (B16)** — pattern tightened from
    `^[a-z]+_...` to an explicit alternation of the eight known artifact roles
    (`tbank|ptbank|lpred|upred|nbank|run|model|obs`). `fig_` / `paper_` are
    excluded deliberately: figures and papers carry `FigureId` / `PaperId`.
    **A narrowing, not a relaxation** — an id with an invented or typo'd prefix
    that used to validate now fails, which is the point (previously it surfaced
    downstream as an unclassifiable artifact instead). Every id in use still
    validates. The vocabulary stays single-sourced in `codegen/roles.json`; the
    schema remains hand-written, with `tests/test_roles.py` asserting the
    alternation matches that source so the two can't drift.
  - **`ActivationPosition` added** — the `[0,1]` activation fraction shared by
    `iafdb_bank` and `synthetic_bank`, defined once here and `$ref`'d by both so
    the two corpora cannot diverge (their position distributions get compared to
    each other; a per-schema copy is exactly how that comparison would silently
    go wrong).
  - Common-only: no document schema's `schema_version` changes on account of
    these, though all regenerate since they inline the patterns.
- **(v0.5.3)** — `ArtifactId` date suffix made optional: pattern relaxed from
  `^[a-z]+_[a-z0-9_]+_\d{4}-\d{2}-\d{2}(_v\d+)?$` to
  `^[a-z]+_[a-z0-9_]+(_\d{4}-\d{2}-\d{2})?(_v\d+)?$` so a hand-set id (e.g. a
  config `bank_id` override) needn't carry a date; auto-derived ids still stamp
  one. Backward-compatible relaxation — every previously valid id still
  validates. Common-only: no document schema's `schema_version` changed (they
  inline the pattern via codegen, so all regenerate, but their contracts only
  widen). egm-contracts package -> v0.5.3.
- **(introduced v0.5.0)** — new shared-`$defs` schema holding the stable
  cross-artifact id patterns (ArtifactId / FigureId / PaperId), referenced
  cross-file by every schema that carries an id. Single source of truth:
  update a pattern here and all schemas inherit it. Not a document format
  (no document validator; nothing is written to disk in this shape).

### egm_class_model_metadata

- **1.2** — egm-contracts v0.5.0. Added the optional `model_id`
  stable-artifact identifier (the model's own ID; what a run.json's
  `produced_model_id` points at). Optional in-schema; egm-classifier
  enforces it on new writes. The model→run link is intentionally NOT
  stored in this deployment sidecar — the run record owns that pointer.
  Part of the cross-artifact linkage wave (see
  `intracardiac-platform/project/cross_artifact_linkage_design.md`).
- **1.1** — egm-contracts v0.4.0. Dropped per-channel `mean` /
  `std` arrays from `preprocessing.normalization`; switched the
  `normalization.scheme` enum from `{zscore, minmax, none}` to
  `{zscore, zero2one, none}`, all computed per-trace. Rationale:
  the v1 classifier consumes one bipolar trace per forward pass,
  so per-channel statistics aren't a meaningful concept; any
  sensor- or hardware-level calibration is expected upstream of
  this contract.
- **1.0** — egm-contracts v0.3.0. Initial release of this schema
  (renamed from `model_metadata`).

### iafdb_bank

- **1.2** — egm-contracts v0.5.0. Added the optional `bank_id`
  stable-artifact identifier (HDF5 root attr). Cross-artifact
  linkage wave.
- **1.1** — egm-contracts v0.2.x. Added `'none'` to `threshold_mode`
  + made `threshold_value` nullable, for the unfiltered-export path
  (every window, no healthy threshold). (Backfilled change-log
  entry — the bump predated this log section.)

### noise_bank_run_record

- **1.1** — egm-contracts v0.5.0. Added the optional `bank_id`
  stable-artifact identifier for the noise bank (the design puts the
  noise bank's stable ID on this sidecar rather than the HDF5).
  Cross-artifact linkage wave.

### synthetic_bank

- **1.1** — egm-contracts v0.5.0. Added the optional `bank_id`
  stable-artifact identifier (HDF5 root attr). Cross-artifact
  linkage wave.

### training_run_record

- **1.1** — egm-contracts v0.5.0. Added the optional stable-artifact
  pointer fields `run_id` (this run's own ID), `trained_on_bank_id`
  (pointer to the training bank), and `produced_model_id` (pointer to
  the exported model). Cross-artifact linkage wave.

---

## Post-1.0 of egm-contracts (deferred)

When egm-contracts the package hits its own v1.0, schema-version
conventions tighten:

- Bumping the major in `schema_version` (`1.x` → `2.0`) becomes a
  *contract break* affecting all consumers; the release PR must call this
  out explicitly.
- Backward-compat for the previous major is supported for one major
  egm-contracts version (e.g., contracts v1 reads schemas `/1.x` and
  `/2.x`; contracts v2 drops `/1.x`).
- This file gets a "post-1.0" section spelling out the deprecation
  policy.

Pre-1.0 today; the rules above are the pre-1.0 rules.
