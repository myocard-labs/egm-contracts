"""Tests for the cross-artifact-linkage additions (egm-contracts v0.5.0).

Covers the three new JSON schemas (phase_manifest / observation /
figure_spec) and their validators, the single-sourced stable-ID patterns
in common.schema.json (referenced cross-file), and the "optional for
legacy, present for new" behaviour of the bank_id field on the existing
bank schemas.

See intracardiac-platform/project/cross_artifact_linkage_design.md.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import h5py

from myocard_egm_contracts.schema_info import current_version, get_schema, supported_versions
from myocard_egm_contracts.validators import (
    validate_figure_spec,
    validate_noise_bank,
    validate_observation,
    validate_phase_manifest,
    validate_synthetic_bank,
)

# ---------------------------------------------------------------------------
# Good example docs (JSON)
# ---------------------------------------------------------------------------

GOOD_MANIFEST: dict[str, Any] = {
    "schema_version": "1",
    "phase": 1.5,
    "status": "in_progress",
    "phase_summary": "Synthetic-data realism for Phase 1.5.",
    "egm_banks": [
        {
            "id": "tbank_synthetic_courtemanche_v1_5_2026-06-25",
            "path": "banks/tbank.h5",
            "produced_by_package": "synthetic-egm-pipeline",
            "produced_by_version": "v0.2.0",
        },
        {
            "id": "upred_iafdb_v1_5_2026-06-25",
            "path": "preds/upred.h5",
            "produced_by_package": "egm-classifier",
            "produced_by_version": "v0.2.0",
            "model": "model_egm_classifier_v1_5_2026-06-25",
            "source_bank": "tbank_iafdb_v1_2026-06-15",
        },
    ],
    "noise_banks": [
        {
            "id": "nbank_iafdb_2026-06-15",
            "path": "banks/nbank_iafdb.h5",
            "produced_by_package": "iafdb-pipeline",
            "produced_by_version": "v0.2.0",
        }
    ],
    "training_runs": [
        {
            "id": "run_v1_5_courtemanche_2026-06-25",
            "path": "runs/run.json",
            "produced_by_package": "egm-classifier",
            "produced_by_version": "v0.2.0",
            "trained_on_bank": "tbank_synthetic_courtemanche_v1_5_2026-06-25",
            "produced_model": "model_egm_classifier_v1_5_2026-06-25",
        }
    ],
    "models": [
        {
            "id": "model_egm_classifier_v1_5_2026-06-25",
            "path": "models/best.pt",
            "produced_by_package": "egm-classifier",
            "produced_by_version": "v0.2.0",
            "trained_from_run": "run_v1_5_courtemanche_2026-06-25",
        }
    ],
    "observations": [
        {
            "id": "obs_courtemanche_high_entropy_tail_2026-06-25",
            "path": "observations/obs.json",
            "produced_by_package": "egm-studio",
            "produced_by_version": "v0.1.0",
            "usage_tag": "informed_paper",
        }
    ],
    "figures": [
        {
            "id": "fig_feature_distributions_synth_vs_iafdb",
            "path": "figure_specs/fig.json",
            "produced_by_package": "egm-studio",
            "produced_by_version": "v0.1.0",
            "consumes_banks": ["tbank_synthetic_courtemanche_v1_5_2026-06-25"],
            "usage_tag": "in_paper_main",
        }
    ],
    "papers": [
        {
            "id": "paper_phase_1_5_realism",
            "path": "../../../intracardiac-papers/papers/phase_1_5_realism/",
            "produced_by_package": "intracardiac-papers",
            "produced_by_version": "latest",
            "figures": ["fig_feature_distributions_synth_vs_iafdb"],
        }
    ],
}

GOOD_OBSERVATION: dict[str, Any] = {
    "schema_version": "1",
    "id": "obs_courtemanche_high_entropy_tail_2026-06-25",
    "date": "2026-06-25",
    "title": "Courtemanche synthetic produces a high-entropy tail",
    "description": (
        "The synthetic sample_entropy distribution has a long tail above 1.5 "
        "that IAFDB never reaches."
    ),
    "traces": [{"bank": "tbank_synthetic_courtemanche_v1_5_2026-06-25", "index": 1247}],
    "view_state": {
        "banks_loaded": ["tbank_synthetic_courtemanche_v1_5_2026-06-25"],
        "filter": "sample_entropy > 1.5",
    },
}

GOOD_FIGURE: dict[str, Any] = {
    "schema_version": "1",
    "id": "fig_feature_distributions_synth_vs_iafdb",
    "description": "Overlay of per-feature distributions, synthetic v1.5 vs IAFDB.",
    "recipe": "feature-distribution-overlay",
    "inputs": {
        "groups": [
            {"name": "Synthetic v1.5", "bank_id": "tbank_synthetic_courtemanche_v1_5_2026-06-25"},
            {"name": "IAFDB", "bank_id": "tbank_iafdb_v1_2026-06-15"},
        ]
    },
    "output": {
        "format": "pdf",
        "path": "../../../intracardiac-papers/papers/phase_1_5/figures/fig.pdf",
    },
    "illustrates_observations": ["obs_courtemanche_high_entropy_tail_2026-06-25"],
}


def _write_json(tmp_path: Path, name: str, doc: Any) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Positive cases
# ---------------------------------------------------------------------------


def test_phase_manifest_validates(tmp_path: Path) -> None:
    result = validate_phase_manifest(_write_json(tmp_path, "manifest.json", GOOD_MANIFEST))
    assert result.ok, result.issues


def test_observation_validates(tmp_path: Path) -> None:
    result = validate_observation(_write_json(tmp_path, "obs.json", GOOD_OBSERVATION))
    assert result.ok, result.issues


def test_figure_spec_validates(tmp_path: Path) -> None:
    result = validate_figure_spec(_write_json(tmp_path, "fig.json", GOOD_FIGURE))
    assert result.ok, result.issues


# ---------------------------------------------------------------------------
# Negative cases
# ---------------------------------------------------------------------------


def test_observation_missing_description_fails(tmp_path: Path) -> None:
    doc = copy.deepcopy(GOOD_OBSERVATION)
    del doc["description"]
    result = validate_observation(_write_json(tmp_path, "obs.json", doc))
    assert not result
    assert any("description" in i for i in result.issues), result.issues


def test_figure_spec_missing_description_fails(tmp_path: Path) -> None:
    """description is now required on figure_spec (review comment 4)."""
    doc = copy.deepcopy(GOOD_FIGURE)
    del doc["description"]
    result = validate_figure_spec(_write_json(tmp_path, "fig.json", doc))
    assert not result
    assert any("description" in i for i in result.issues), result.issues


def test_observation_rejects_unknown_phase_field(tmp_path: Path) -> None:
    """phase was removed (review comment 2); additionalProperties:false rejects it."""
    doc = copy.deepcopy(GOOD_OBSERVATION)
    doc["phase"] = 1.5
    result = validate_observation(_write_json(tmp_path, "obs.json", doc))
    assert not result


def test_figure_spec_rejects_unknown_inventory_ref(tmp_path: Path) -> None:
    """inventory_ref was removed (review comment 3); additionalProperties:false rejects it."""
    doc = copy.deepcopy(GOOD_FIGURE)
    doc["inventory_ref"] = "F-1.5.2"
    result = validate_figure_spec(_write_json(tmp_path, "fig.json", doc))
    assert not result


def test_manifest_bad_artifact_id_fails(tmp_path: Path) -> None:
    doc = copy.deepcopy(GOOD_MANIFEST)
    doc["egm_banks"][0]["id"] = "TBANK_not_lowercase"
    result = validate_phase_manifest(_write_json(tmp_path, "manifest.json", doc))
    assert not result
    assert any("does not match" in i or "pattern" in i.lower() for i in result.issues), (
        result.issues
    )


def test_manifest_bad_usage_tag_fails(tmp_path: Path) -> None:
    doc = copy.deepcopy(GOOD_MANIFEST)
    doc["figures"][0]["usage_tag"] = "totally_made_up"
    result = validate_phase_manifest(_write_json(tmp_path, "manifest.json", doc))
    assert not result


def test_manifest_unknown_top_level_key_fails(tmp_path: Path) -> None:
    doc = copy.deepcopy(GOOD_MANIFEST)
    doc["bogus_key"] = 1
    result = validate_phase_manifest(_write_json(tmp_path, "manifest.json", doc))
    assert not result


def test_figure_spec_non_fig_id_fails(tmp_path: Path) -> None:
    doc = copy.deepcopy(GOOD_FIGURE)
    doc["id"] = "obs_not_a_figure_2026-06-25"
    result = validate_figure_spec(_write_json(tmp_path, "fig.json", doc))
    assert not result


def test_missing_file_fails(tmp_path: Path) -> None:
    result = validate_phase_manifest(tmp_path / "nope.json")
    assert not result
    assert "file not found" in result.issues[0]


def test_malformed_json_fails(tmp_path: Path) -> None:
    p = tmp_path / "manifest.json"
    p.write_text("{not valid json", encoding="utf-8")
    result = validate_phase_manifest(p)
    assert not result
    assert any("JSON parse failed" in i for i in result.issues), result.issues


# ---------------------------------------------------------------------------
# Single-sourced stable-ID patterns (common.schema.json)
# ---------------------------------------------------------------------------

_ID_SCHEMAS = (
    "synthetic_bank",
    "iafdb_bank",
    "noise_bank_run_record",
    "training_run_record",
    "egm_class_model_metadata",
    "phase_manifest",
    "observation",
    "figure_spec",
)


def test_common_defines_the_id_patterns() -> None:
    defs = get_schema("common").get("$defs", {})
    for name in ("ArtifactId", "FigureId", "PaperId"):
        assert name in defs and "pattern" in defs[name], f"common.$defs.{name} missing"


def _collect_id_refs(node: Any, out: list[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if (
                key == "$ref"
                and isinstance(value, str)
                and ("ArtifactId" in value or "FigureId" in value or "PaperId" in value)
            ):
                out.append(value)
            else:
                _collect_id_refs(value, out)
    elif isinstance(node, list):
        for item in node:
            _collect_id_refs(item, out)


def test_no_schema_redefines_id_patterns_locally() -> None:
    """The ID patterns must be single-sourced in common.schema.json — no
    other schema may carry a local copy, and every ID $ref must point at
    common (review comment 9)."""
    for name in _ID_SCHEMAS:
        schema = get_schema(name)
        local_defs = schema.get("$defs", {})
        for forbidden in ("ArtifactId", "FigureId", "PaperId"):
            assert forbidden not in local_defs, f"{name} still defines {forbidden} locally"
        refs: list[str] = []
        _collect_id_refs(schema, refs)
        assert refs, f"{name} declares no ID $ref (expected at least one)"
        for ref in refs:
            assert ref.startswith("common.schema.json#"), f"{name} has non-common ID $ref: {ref}"


def test_new_schemas_advertise_version_one() -> None:
    for name in ("phase_manifest", "observation", "figure_spec"):
        assert supported_versions(name) == ("1",)
        assert current_version(name) == "1"


# ---------------------------------------------------------------------------
# bank_id is optional for legacy banks, validated when present (via registry)
# ---------------------------------------------------------------------------


def test_synthetic_bank_without_bank_id_still_validates(valid_synthetic_bank: Path) -> None:
    """A legacy bank has no bank_id attr; the field is optional, so the bank
    must still validate (the backfill decision: new artifacts only)."""
    with h5py.File(valid_synthetic_bank, "r") as f:
        assert "bank_id" not in f.attrs
    result = validate_synthetic_bank(valid_synthetic_bank)
    assert result.ok, result.issues


def test_synthetic_bank_with_valid_bank_id_validates(valid_synthetic_bank: Path) -> None:
    """A present bank_id must resolve the cross-file $ref into common and pass."""
    with h5py.File(valid_synthetic_bank, "r+") as f:
        f.attrs["bank_id"] = "tbank_synthetic_courtemanche_v1_5_2026-06-25"
    result = validate_synthetic_bank(valid_synthetic_bank)
    assert result.ok, result.issues


def test_synthetic_bank_with_malformed_bank_id_fails(valid_synthetic_bank: Path) -> None:
    with h5py.File(valid_synthetic_bank, "r+") as f:
        f.attrs["bank_id"] = "NOT-a-valid-id"
    result = validate_synthetic_bank(valid_synthetic_bank)
    assert not result
    assert any("bank_id" in i or "does not match" in i for i in result.issues), result.issues


def test_noise_bank_without_bank_id_still_validates(valid_noise_bank: Path) -> None:
    """Same optional-in-schema / required-on-write treatment as the other banks:
    a bank written before 1.1 has no id and must still validate."""
    with h5py.File(valid_noise_bank, "r") as f:
        assert "bank_id" not in f.attrs
    result = validate_noise_bank(valid_noise_bank)
    assert result.ok, result.issues


def test_noise_bank_with_valid_bank_id_validates(valid_noise_bank: Path) -> None:
    """The point of 1.1: egm-studio reads the id off the .h5 instead of the sidecar."""
    with h5py.File(valid_noise_bank, "r+") as f:
        f.attrs["bank_id"] = "nbank_iafdb_2026-06-15"
    result = validate_noise_bank(valid_noise_bank)
    assert result.ok, result.issues


def test_noise_bank_with_malformed_bank_id_fails(valid_noise_bank: Path) -> None:
    with h5py.File(valid_noise_bank, "r+") as f:
        f.attrs["bank_id"] = "NOT-a-valid-id"
    result = validate_noise_bank(valid_noise_bank)
    assert not result
    assert any("bank_id" in i or "does not match" in i for i in result.issues), result.issues


def test_noise_bank_with_unknown_role_prefix_fails(valid_noise_bank: Path) -> None:
    """B16 reaching a real field: a well-shaped id with an invented role prefix
    used to validate here, and only became a problem downstream. The bank's role
    is NOT checked against the prefix (an nbank_ vs tbank_ mismatch is egm-data's
    content check) — this asserts only that the prefix is a known role at all."""
    with h5py.File(valid_noise_bank, "r+") as f:
        f.attrs["bank_id"] = "noisebank_iafdb_2026-06-15"
    result = validate_noise_bank(valid_noise_bank)
    assert not result
    assert any("bank_id" in i or "does not match" in i for i in result.issues), result.issues


def test_synthetic_bank_with_dateless_bank_id_validates(valid_synthetic_bank: Path) -> None:
    """S8-3: the ArtifactId ``_YYYY-MM-DD`` suffix is now optional — a hand-set
    bank_id without a date (with or without a ``_vN`` suffix) must validate.
    Auto-derived ids still stamp a date; user-supplied ids aren't forced to."""
    for dateless in ("tbank_synthetic_courtemanche_handrolled", "tbank_synth_v3"):
        with h5py.File(valid_synthetic_bank, "r+") as f:
            f.attrs["bank_id"] = dateless
        result = validate_synthetic_bank(valid_synthetic_bank)
        assert result.ok, (dateless, result.issues)
