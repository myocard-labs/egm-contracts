# hybrid_eval_metrics (removed in 0.4.1)

**Status: removed.** This schema was deleted in egm-contracts 0.4.1. This
page is kept only so existing references resolve and so the reasoning is
preserved.

## What it was

A JSON format (`hybrid_eval_metrics.json`) that persisted aggregate
classifier-evaluation scores over a "hybrid" set — synthetic-fibrotic
positives mixed with real IAFDB segments treated as healthy negatives. It
carried a `mixed` block (AUROC / accuracy / precision / recall / F1 /
confusion across the combined set) and an `iafdb_only` block (mean
P(fibrotic), a false-positive rate at 0.5, and probability percentiles).

## Why it was removed

The format proved **untenable**. Computing AUROC, FPR, precision/recall, or a
confusion matrix on the IAFDB rows requires treating those rows as **labeled**
negatives — but IAFDB has no fibrosis ground truth. Its "healthy" label is an
extraction assumption, not a measurement, so every label-dependent score
scored the model against an assumption rather than against truth. (See the
`feedback-iafdb-unlabeled-no-ml-validation` / `project-iafdb-eval-catch22`
reasoning and `intracardiac-platform`'s IAFDB investigation write-up.)

## What replaces it

- **Rigorous, labeled evaluation** stays entirely on **synthetic** data,
  where labels exist by construction. Those metrics live in the training
  records (`training_run_record` / `training_metrics`), not here.
- **IAFDB** is used only as a **label-free sanity check** on the trained
  model — inspecting the model's **label / probability distribution** on
  IAFDB segments alone (e.g. "does the decision function saturate?"). This is
  a qualitative gut-check, *not* a validation, performed at analysis time in
  **egm-studio** directly from the `ClassifierBank`, with nothing persisted as
  a contract.
- A genuine **hybrid evaluation** in the Sánchez et al. 2021 sense remains
  possible in principle — `egm-data`'s `ClassifierBank` can already hold a
  combined synthetic + real set — but only once **labeled** real EGM data is
  available. IAFDB is currently the only open real intracardiac EGM source we
  have found, and it is unlabeled, so that evaluation cannot be run today.
