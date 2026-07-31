"""Validator tests — positive cases (round-trip) and a few targeted negatives.

The positive fixtures live in conftest.py; here we exercise the validators
against them and against deliberately-malformed variants.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import h5py
import numpy as np

from myocard_egm_contracts.validators import (
    validate_egm_class_model_metadata,
    validate_iafdb_bank,
    validate_noise_bank,
    validate_noise_bank_run_record,
    validate_synthetic_bank,
    validate_training_metrics,
    validate_training_run_record,
)

# ---------------------------------------------------------------------------
# Positive cases — fixtures from conftest should all validate cleanly
# ---------------------------------------------------------------------------


def test_iafdb_bank_validates(valid_iafdb_bank: Path) -> None:
    result = validate_iafdb_bank(valid_iafdb_bank)
    assert result.ok, result.issues


def test_iafdb_bank_validates_with_none_threshold(valid_iafdb_bank: Path) -> None:
    """v1.1 added 'none' to threshold_mode and made threshold_value nullable
    so producers can export every windowed segment without a healthy filter.
    Mutate the fixture into the new mode and confirm it still passes the
    schema. HDF5 doesn't have a native null, so producers using mode='none'
    stamp NaN for threshold_value; the schema accepts NaN as a number and
    the validator round-trips it via json.loads."""
    with h5py.File(valid_iafdb_bank, "r+") as f:
        f.attrs["threshold_mode"] = "none"
        del f.attrs["threshold_value"]
        f.attrs["threshold_value"] = float("nan")
    result = validate_iafdb_bank(valid_iafdb_bank)
    assert result.ok, result.issues


def test_iafdb_bank_without_activation_position_validates(valid_iafdb_bank: Path) -> None:
    """1.3 adds the column; nothing populates it until IAF1 ships in Wave 2.

    This is the assertion that keeps the migration/feature wave split intact —
    if the column ever becomes required, Wave-1 banks stop validating and the
    splitter work gets dragged forward into the schema wave.
    """
    with h5py.File(valid_iafdb_bank, "r") as f:
        assert "activation_position" not in f["traces"]
    result = validate_iafdb_bank(valid_iafdb_bank)
    assert result.ok, result.issues


def test_iafdb_bank_with_activation_position_validates(valid_iafdb_bank: Path) -> None:
    """Endpoints included: an activation may land on the first or last sample."""
    with h5py.File(valid_iafdb_bank, "r+") as f:
        n = f["traces"]["signal"].shape[0]
        f["traces"].create_dataset(
            "activation_position", data=np.linspace(0.0, 1.0, n, dtype=np.float32)
        )
    result = validate_iafdb_bank(valid_iafdb_bank)
    assert result.ok, result.issues


def test_iafdb_bank_with_out_of_range_activation_position_fails(valid_iafdb_bank: Path) -> None:
    """A value outside [0,1] means the splitter mis-anchored, or a producer wrote
    a sample index where a fraction belongs — the failure the bounds exist for."""
    with h5py.File(valid_iafdb_bank, "r+") as f:
        n = f["traces"]["signal"].shape[0]
        f["traces"].create_dataset("activation_position", data=np.full(n, 42.0, dtype=np.float32))
    result = validate_iafdb_bank(valid_iafdb_bank)
    assert not result
    assert any("activation_position" in i for i in result.issues), result.issues


def test_iafdb_bank_with_run_record_path_validates(valid_iafdb_bank: Path) -> None:
    """The sidecar pointer is a plain relative string; absence is legal, and is
    covered by every other iafdb fixture since none of them set it."""
    with h5py.File(valid_iafdb_bank, "r+") as f:
        f.attrs["run_record_path"] = "iafdb_healthy_v1_run_record.json"
    result = validate_iafdb_bank(valid_iafdb_bank)
    assert result.ok, result.issues


def test_noise_bank_validates(valid_noise_bank: Path) -> None:
    result = validate_noise_bank(valid_noise_bank)
    assert result.ok, result.issues


def test_noise_bank_run_record_validates(valid_noise_bank_run_record: Path) -> None:
    """The slim noise_bank carries only what the mixer consumes; extraction
    provenance lives in this sibling JSON. Round-trip the fixture through
    the validator."""
    result = validate_noise_bank_run_record(valid_noise_bank_run_record)
    assert result.ok, result.issues


def test_synthetic_bank_validates(valid_synthetic_bank: Path) -> None:
    result = validate_synthetic_bank(valid_synthetic_bank)
    assert result.ok, result.issues


def test_training_run_record_validates(valid_training_run_record: Path) -> None:
    result = validate_training_run_record(valid_training_run_record)
    assert result.ok, result.issues


def test_run_record_without_train_metrics_validates(valid_training_run_record: Path) -> None:
    """1.2 adds `train_metrics` optional-in-schema, and this is the assertion
    that keeps it that way.

    Wave 1 (CLF5) adopts the schema; Wave 2 (CLF2) adds the emit. If this field
    were required, every record written in between would fail validation and
    the emit work would be pulled into the migration wave — collapsing exactly
    the split the wave structure exists to protect.
    """
    doc = json.loads(valid_training_run_record.read_text())
    assert "train_metrics" not in doc["epochs"][0]
    result = validate_training_run_record(valid_training_run_record)
    assert result.ok, result.issues


def test_run_record_with_train_metrics_validates(valid_training_run_record: Path) -> None:
    """The populated path: the same bundle shape as val_metrics, nested
    confusion included."""
    doc = json.loads(valid_training_run_record.read_text())
    doc["epochs"][0]["train_metrics"] = {
        "auroc": 0.93,
        "accuracy": 0.9,
        "precision": 0.91,
        "recall": 0.88,
        "f1": 0.89,
        "ece": 0.04,
        "confusion": {"tp": 45, "fp": 5, "tn": 40, "fn": 10},
    }
    valid_training_run_record.write_text(json.dumps(doc))
    result = validate_training_run_record(valid_training_run_record)
    assert result.ok, result.issues


def test_held_out_test_accepts_the_val_metrics_bundle(valid_training_run_record: Path) -> None:
    """B18 parity, stated as the case that used to fail.

    Before 1.2, HeldOutTest.metrics admitted only flat scalars, so a producer
    writing the *same* bundle it writes per-epoch — which carries a nested
    `confusion` — had its test block rejected while its epochs passed. Feeding
    the val bundle straight into the test block is therefore the sharpest test
    of the alignment.
    """
    doc = json.loads(valid_training_run_record.read_text())
    bundle = {
        "auroc": 0.87,
        "accuracy": 0.83,
        "f1": 0.81,
        "ece": 0.05,
        "confusion": {"tp": 40, "fp": 8, "tn": 38, "fn": 14},
    }
    doc["epochs"][0]["val_metrics"] = bundle
    doc["test"] = {
        "loss": 0.42,
        "metrics": bundle,
        "reliability": doc["epochs"][0]["val_reliability"],
    }
    valid_training_run_record.write_text(json.dumps(doc))
    result = validate_training_run_record(valid_training_run_record)
    assert result.ok, result.issues


def test_training_metrics_csv_validates(valid_training_metrics_csv: Path) -> None:
    result = validate_training_metrics(valid_training_metrics_csv)
    assert result.ok, result.issues


def test_training_metrics_csv_without_train_columns_validates(
    valid_training_metrics_csv: Path,
) -> None:
    """The fixture predates the train_* block, which is the Wave-1 case: a CSV
    written before the producer emits them is still valid."""
    header = valid_training_metrics_csv.read_text().splitlines()[0]
    assert "train_auroc" not in header
    result = validate_training_metrics(valid_training_metrics_csv)
    assert result.ok, result.issues


def test_training_metrics_csv_with_train_columns_validates(tmp_path: Path) -> None:
    """The populated path, written in the contract's own column order.

    Uses csv_column_order() rather than a hand-typed header, so the test can't
    drift from the schema — and a row of empty cells covers the nullable case
    (a metric undefined for that epoch writes an empty cell, not a zero).
    """
    from myocard_egm_contracts.schema_info import csv_column_order

    columns = csv_column_order("training_metrics")
    values = {
        "epoch": 1,
        "lr": 0.001,
        "train_loss": 0.5,
        "train_auroc": 0.91,
        "train_accuracy": 0.88,
        "train_precision": 0.87,
        "train_recall": 0.86,
        "train_f1": 0.865,
        "train_ece": 0.03,
        "val_loss": 0.45,
        "val_auroc": 0.85,
        "val_accuracy": 0.8,
        "val_precision": 0.81,
        "val_recall": 0.78,
        "val_f1": 0.79,
        "val_ece": 0.05,
        "epoch_seconds": 12.3,
    }
    nulled = {
        k: ("" if k.startswith(("train_a", "train_p", "train_r", "train_f", "train_e")) else v)
        for k, v in values.items()
    }

    path = tmp_path / "metrics.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(columns))
        writer.writeheader()
        writer.writerow(values)
        writer.writerow(nulled)

    result = validate_training_metrics(path)
    assert result.ok, result.issues


def test_training_metrics_column_order_pairs_the_blocks() -> None:
    """The order is part of the contract (B18/CL-037): train_* sits between
    train_loss and val_loss, not appended after the val block.

    Appending would have been the smaller diff; it was rejected because the
    reason for carrying both splits is reading their divergence, and a
    spreadsheet only makes that obvious when the pairs are adjacent.
    """
    from myocard_egm_contracts.schema_info import csv_column_order, get_schema

    order = csv_column_order("training_metrics")
    train_block = [c for c in order if c.startswith("train_") and c != "train_loss"]
    val_block = [c for c in order if c.startswith("val_") and c != "val_loss"]

    assert order.index("train_loss") < order.index(train_block[0])
    assert order.index(train_block[-1]) < order.index("val_loss")
    assert order.index("val_loss") < order.index(val_block[0])
    assert order[-1] == "epoch_seconds"
    # Every declared property is in the order, and vice versa — the two drift
    # apart silently otherwise, since nothing else compares them.
    assert set(order) == set(get_schema("training_metrics")["properties"])


def test_training_metrics_rejects_unknown_column(tmp_path: Path) -> None:
    """additionalProperties:false is why the columns had to ship before the
    producer could write them — this is that rejection, made visible."""
    path = tmp_path / "metrics.csv"
    path.write_text(
        "epoch,lr,train_loss,val_loss,epoch_seconds,train_mystery\n1,0.001,0.5,0.45,1.0,0.9\n"
    )
    result = validate_training_metrics(path)
    assert not result
    assert any("train_mystery" in i or "additional" in i.lower() for i in result.issues), (
        result.issues
    )


def test_egm_class_model_metadata_validates(valid_egm_class_model_metadata: Path) -> None:
    result = validate_egm_class_model_metadata(valid_egm_class_model_metadata)
    assert result.ok, result.issues


# ---------------------------------------------------------------------------
# Negative cases — targeted, one per failure mode
# ---------------------------------------------------------------------------


def test_missing_file_fails_with_clear_message(tmp_path: Path) -> None:
    result = validate_training_run_record(tmp_path / "does_not_exist.json")
    assert not result
    assert "file not found" in result.issues[0]


def test_malformed_json_fails(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    result = validate_training_run_record(bad)
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


def test_noise_bank_run_record_window_samples_mismatch_fails(
    valid_noise_bank_run_record: Path,
) -> None:
    """The slim noise_bank no longer carries window parameters; the cross-field
    invariant moved to the run record sidecar. Mutate the run record's
    window_samples to a value inconsistent with window_ms * fs and confirm
    the validator catches it."""
    doc = json.loads(valid_noise_bank_run_record.read_text())
    doc["windowing"]["window_samples"] = 999
    valid_noise_bank_run_record.write_text(json.dumps(doc))

    result = validate_noise_bank_run_record(valid_noise_bank_run_record)
    assert not result
    assert any("window_samples" in issue for issue in result.issues), result.issues


def test_training_run_record_missing_required_field_fails(
    valid_training_run_record: Path,
) -> None:
    """JSON Schema should fail when a required field is dropped."""
    doc = json.loads(valid_training_run_record.read_text())
    del doc["best"]  # required
    valid_training_run_record.write_text(json.dumps(doc))

    result = validate_training_run_record(valid_training_run_record)
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


def test_egm_class_model_metadata_invalid_sha256_fails(
    valid_egm_class_model_metadata: Path,
) -> None:
    """Pattern constraint should reject malformed sha256 strings."""
    doc = json.loads(valid_egm_class_model_metadata.read_text())
    doc["model_artifact"]["sha256"] = "not-a-real-hash"
    valid_egm_class_model_metadata.write_text(json.dumps(doc))

    result = validate_egm_class_model_metadata(valid_egm_class_model_metadata)
    assert not result
    assert any("sha256" in issue for issue in result.issues), result.issues


def test_training_metrics_csv_null_required_field_fails(tmp_path: Path) -> None:
    """epoch_seconds is required and non-null per the v1.0 schema."""
    path = tmp_path / "metrics.csv"
    path.write_text(
        "epoch,lr,train_loss,val_loss,val_auroc,val_accuracy,val_precision,"
        "val_recall,val_f1,val_ece,epoch_seconds\n"
        "1,0.001,0.5,0.45,0.85,0.8,0.81,0.78,0.79,0.05,\n",  # empty epoch_seconds
        encoding="utf-8",
    )

    result = validate_training_metrics(path)
    assert not result
    assert any("epoch_seconds" in issue for issue in result.issues), result.issues
