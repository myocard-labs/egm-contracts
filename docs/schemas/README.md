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
| [synthetic_bank](synthetic_bank.md) | HDF5 | Labeled synthetic intracardiac EGM bank |
| [iafdb_healthy_bank](iafdb_healthy_bank.md) | HDF5 | Calibrated healthy segments extracted from PhysioNet IAFDB |
| [run_record](run_record.md) | JSON | Full versioned record of one training run |
| [metrics](metrics.md) | CSV | Flat per-epoch training metrics |
| [predictions](predictions.md) | CSV + JSON | Per-trace predictions interchange |
| [hybrid_eval_metrics](hybrid_eval_metrics.md) | JSON | Aggregate metrics for a hybrid (mixed sim + real) evaluation |
| [model_metadata](model_metadata.md) | JSON | Preprocessing + inference constants paired with a model artifact |

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

- **"Hybrid"** — follows the cardiac-ML convention from Sánchez et al. 2021 (Frontiers in Physiology 12, 699291), where a "hybrid in silico + in vivo" dataset mixes simulated and real recordings. In our schemas, "hybrid" specifically refers to **evaluations** that mix synthetic positives with real IAFDB negatives. A synthetic bank with IAFDB-noise conditioning is *not* called hybrid — the labels are still 100% synthetic.
- **"Bank"** — a single-file collection of pre-extracted traces ready for training or evaluation. Both synthetic_bank and iafdb_healthy_bank are bank formats; both ship as HDF5 with a top-level `traces/` group containing aligned per-trace columns.

For evolution rules and developer-facing details on how to safely change a schema, see `project/schema_evolution.md`.
