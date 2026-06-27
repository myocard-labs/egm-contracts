# Schema overview

This folder holds **human-readable explanations** of every schema in
egm-contracts. The `.schema.json` files in
`src/myocard_egm_contracts/schemas/` are the master truth; the docs here
are the prose companion — explanation, motivation, examples — that the
JSON Schema alone doesn't carry.

Read the schema file when you need precise field definitions. Read the
doc here when you need to understand *why* the schema looks the way it
does or want a narrative walkthrough of the fields.

The docs here are intentionally **abstract**. They describe what each
schema represents, what its fields mean, and how versioning works. They
do *not* describe specific producer or consumer implementations — that
information lives in the consuming/producing components' own
documentation.

---

## The schemas at a glance

| Schema | Document type | One-line role |
|---|---|---|
| [synthetic_bank](synthetic_bank.md) | HDF5 | Synthetic intracardiac EGM bank |
| [iafdb_bank](iafdb_bank.md) | HDF5 | Calibrated bipolar EGM segments extracted from PhysioNet IAFDB |
| [noise_bank](noise_bank.md) | HDF5 | Quiet bipolar EGM segments extracted from any real EGM dataset, used as additive noise by the synthetic mixer. Minimal: only what the mixer consumes. |
| [noise_bank_run_record](noise_bank_run_record.md) | JSON | Provenance sidecar for a noise_bank: calibration, threshold, windowing, per-trace audit. Paired with a noise_bank by name-stem convention. |
| [training_run_record](training_run_record.md) | JSON | Full versioned record of one ML training run |
| [training_metrics](training_metrics.md) | CSV | Flat per-epoch training metrics |
| [egm_class_model_metadata](egm_class_model_metadata.md) | JSON | Preprocessing + inference constants paired with a deployed 1-D EGM-classifier model artifact |
| [phase_manifest](phase_manifest.md) | JSON | Per-phase shallow index of every artifact in a project phase (cross-artifact linkage) |
| [observation](observation.md) | JSON | A recorded discovery during signal exploration / ML diagnostics, optionally pinning traces |
| [figure_spec](figure_spec.md) | JSON | Declarative spec for one publication figure; the spec is git-tracked, the image is build output |

The last three (`phase_manifest` / `observation` / `figure_spec`) are the
cross-artifact-linkage schemas added in v0.5.0. They are JSON, matching the
other on-disk record formats in this package. Their files live in
`intracardiac-platform/project/phases/`, but egm-contracts owns the schema
+ the path-based validators. The stable cross-artifact id patterns
(ArtifactId / FigureId / PaperId) they share with the bank, run, and model
schemas are defined once in `common.schema.json` and referenced cross-file
(it is a shared-`$defs` file, not a document format). See
`intracardiac-platform/project/cross_artifact_linkage_design.md`.

---

## How to read each doc

Each schema doc follows the same shape:

1. **What it is** — what data this format represents.
2. **Why it exists** — what need it serves.
3. **Field walkthrough** — narrative description of every field, grouped by purpose.
4. **Versioning** — current version and what would trigger a bump.
5. **Example** — a small, working example payload.

For the canonical contract (types, constraints, required fields, etc.), always go to the corresponding `.schema.json` file. The docs here are for getting up to speed, not for codegen.

---

## A note on terminology

Two terms recur across the schemas:

- **"Hybrid"** — follows the cardiac-ML convention from Sánchez et al. 2021 (Frontiers in Physiology 12, 699291), where a "hybrid in silico + in vivo" dataset mixes simulated and real recordings. A *hybrid evaluation* in that sense — scoring a model against mixed synthetic positives and labeled real negatives — would require **labeled** real EGM data, which the project does not have (IAFDB, our only open real source, carries no fibrosis labels). The dedicated `hybrid_eval_metrics` schema that once persisted such scores was **removed in 0.4.1** as untenable (see [hybrid_eval_metrics.md](hybrid_eval_metrics.md)); the term is retained only for that future, label-gated possibility. A synthetic bank with IAFDB-noise conditioning is *not* called hybrid — the labels are still 100% synthetic.
- **"Bank"** — a single-file collection of pre-extracted traces ready for training or evaluation. synthetic_bank, iafdb_bank, and noise_bank are all bank formats; each ships as HDF5 with a top-level `traces/` group containing aligned per-trace columns. noise_bank is the lean variant: it stores only the fields its consumer (the synthetic mixer) reads at run time; extraction methods live in a companion `noise_bank_run_record.json` sidecar.

For evolution rules and developer-facing details on how to safely change a schema, see `project/schema_evolution.md`.
