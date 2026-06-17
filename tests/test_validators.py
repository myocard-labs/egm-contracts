"""Validator tests — positive cases (round-trip) and a few targeted negatives.

The positive fixtures live in conftest.py; here we exercise the validators
against them and against deliberately-malformed variants.
"""

from __future__ import annotations

import json
from pathlib import Path

import h5py

from myocard_egm_contracts.validators import (
    validate_hybrid_eval_metrics,
    validate_iafdb_bank,
    validate_metrics,
    validate_model_metadata,
    validate_run_record,
    validate_synthetic_bank,
)

# ---------------------------------------------------------------------------
# Positive cases — fixtures from conftest should all validate cleanly
# ---------------------------------------------------------------------------


def test_iafdb_bank_validates(valid_iafdb_bank: Path) -> None:
    result = validate_iafdb_bank(valid_iafdb_bank)
    assert result.ok, result.issues


def test_synthetic_bank_validates(valid_synthetic_bank: Path) -> None:
    result = validate_synthetic_bank(valid_synthetic_bank)
    assert result.ok, result.issues


def test_run_record_validates(valid_run_record: Path) -> None:
    result = validate_run_record(valid_run_record)
    assert result.ok, result.issues


def test_metrics_csv_validates(valid_metrics_csv: Path) -> None:
    result = validate_metrics(valid_metrics_csv)
    assert result.ok, result.issues


def test_hybrid_eval_metrics_validates(valid_hybrid_eval_metrics: Path) -> None:
    result = validate_hybrid_eval_metrics(valid_hybrid_eval_metrics)
    assert result.ok, result.issues


def test_model_metadata_validates(valid_model_metadata: Path) -> None:
    result = validate_model_metadata(valid_model_metadata)
    assert result.ok, result.issues


# ---------------------------------------------------------------------------
# Negative cases — targeted, one per failure mode
# ---------------------------------------------------------------------------


def test_missing_file_fails_with_clear_message(tmp_path: Path) -> None:
    result = validate_run_record(tmp_path / "does_not_exist.json")
    assert not result
    assert "file not found" in result.issues[0]


def test_malformed_json_fails(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    result = validate_run_record(bad)
    assert not result
    assert "JSON parse failed" in result.issues[0]


def test_iafdb_bank_window_samples_mismatch_fails(
    valid_iafdb_bank: Path,
) -> None:
    """The cross-field validator should catch window_samples != fs * ms / 1000."""
    # Mutate the fixture: set window_samples to a wrong value.
    with h5py.File(valid_iafdb_bank, "r+") as f:
        f.attrs["window_samples"] = 999

    result = validate_iafdb_bank(valid_iafdb_bank)
    assert not result
    assert any("window_samples" in issue for issue in result.issues), result.issues


def test_run_record_missing_required_field_fails(
    valid_run_record: Path,
) -> None:
    """JSON Schema should fail when a required field is dropped."""
    doc = json.loads(valid_run_record.read_text())
    del doc["best"]  # required
    valid_run_record.write_text(json.dumps(doc))

    result = validate_run_record(valid_run_record)
    assert not result
    assert any("best" in issue for issue in result.issues), result.issues


def test_synthetic_bank_wrong_schema_version_fails(
    valid_synthetic_bank: Path,
) -> None:
    """The schema_version enum should reject unknown values."""
    with h5py.File(valid_synthetic_bank, "r+") as f:
        f.attrs["schema_version"] = "99.99"

    result = validate_synthetic_bank(valid_synthetic_bank)
    assert not result
    assert any("schema_version" in issue for issue in result.issues), result.issues


def test_model_metadata_invalid_sha256_fails(valid_model_metadata: Path) -> None:
    """Pattern constraint should reject malformed sha256 strings."""
    doc = json.loads(valid_model_metadata.read_text())
    doc["model_artifact"]["sha256"] = "not-a-real-hash"
    valid_model_metadata.write_text(json.dumps(doc))

    result = validate_model_metadata(valid_model_metadata)
    assert not result
    assert any("sha256" in issue for issue in result.issues), result.issues


def test_metrics_csv_null_required_field_fails(tmp_path: Path) -> None:
    """epoch_seconds is required and non-null per the v1.0 schema."""
    path = tmp_path / "metrics.csv"
    path.write_text(
        "epoch,lr,train_loss,val_loss,val_auroc,val_accuracy,val_precision,"
        "val_recall,val_f1,val_ece,epoch_seconds\n"
        "1,0.001,0.5,0.45,0.85,0.8,0.81,0.78,0.79,0.05,\n",  # empty epoch_seconds
        encoding="utf-8",
    )

    result = validate_metrics(path)
    assert not result
    assert any("epoch_seconds" in issue for issue in result.issues), result.issues
