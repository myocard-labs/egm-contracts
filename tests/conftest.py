"""Pytest fixtures shared across the egm-contracts test suite.

Each fixture builds a tiny valid example of one of the on-disk formats
in a temp dir, suitable for round-trip / negative-case validator tests.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import pytest

# ---------------------------------------------------------------------------
# HDF5 bank fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_iafdb_bank(tmp_path: Path) -> Path:
    """Write a tiny valid IAFDB bank to a temp file and return its path."""
    path = tmp_path / "iafdb_v1.h5"
    str_dtype = h5py.string_dtype(encoding="utf-8")
    n = 2
    window_samples = 512

    with h5py.File(path, "w") as f:
        f.attrs["schema_version"] = "1.1"
        f.attrs["created_utc"] = "2026-06-15T22:00:00Z"
        f.attrs["source"] = "iafdb v1.0.0"
        f.attrs["fs_hz"] = 1000.0
        f.attrs["trace_duration_ms"] = 512.0
        f.attrs["calibration_method"] = "r_wave_anchoring"
        f.attrs["calibration_target_qrs_pp_mv"] = 1.0
        f.attrs["threshold_mode"] = "absolute"
        f.attrs["threshold_value"] = 0.5
        f.attrs["band_hz"] = np.array([30.0, 300.0], dtype=np.float64)
        f.attrs["window_ms"] = 512.0
        f.attrs["window_samples"] = window_samples
        f.attrs["hop_ms"] = 256.0
        f.attrs.create(
            "source_records",
            np.asarray(["iaf1_afw"], dtype=object),
            dtype=str_dtype,
        )

        g = f.create_group("traces")
        g.create_dataset("signal", data=np.zeros((n, window_samples), dtype=np.float32))
        g.create_dataset(
            "patient_id",
            data=np.array(["iaf1", "iaf1"], dtype=object),
            dtype=str_dtype,
        )
        g.create_dataset(
            "source_record",
            data=np.array(["iaf1_afw", "iaf1_afw"], dtype=object),
            dtype=str_dtype,
        )
        g.create_dataset(
            "source_channel",
            data=np.array(["CS12", "CS12"], dtype=object),
            dtype=str_dtype,
        )
        g.create_dataset("start_sample", data=np.array([0, 256], dtype=np.int64))
        g.create_dataset("peak_to_peak_mv", data=np.array([0.42, 0.51], dtype=np.float32))
        g.create_dataset("calibration_scalar", data=np.array([0.0035, 0.0035], dtype=np.float32))
    return path


@pytest.fixture
def valid_noise_bank(tmp_path: Path) -> Path:
    """Write a tiny valid (slim) noise bank to a temp file and return its path.

    The noise_bank schema (v1.0) is intentionally minimal: only the fields
    the mixer actually consumes (signal + source_record + source_channel
    per trace, plus schema_version / created_utc / source / fs_hz at root).
    Extraction provenance is tested via the valid_noise_bank_run_record
    fixture below.
    """
    path = tmp_path / "noise_v1.h5"
    str_dtype = h5py.string_dtype(encoding="utf-8")
    n = 2
    window_samples = 512

    with h5py.File(path, "w") as f:
        f.attrs["schema_version"] = "1.0"
        f.attrs["created_utc"] = "2026-06-17T22:00:00Z"
        f.attrs["source"] = "iafdb v1.0.0"
        f.attrs["fs_hz"] = 1000.0

        g = f.create_group("traces")
        g.create_dataset("signal", data=np.zeros((n, window_samples), dtype=np.float32))
        g.create_dataset(
            "source_record",
            data=np.array(["iaf1_afw", "iaf1_afw"], dtype=object),
            dtype=str_dtype,
        )
        g.create_dataset(
            "source_channel",
            data=np.array(["CS12", "CS34"], dtype=object),
            dtype=str_dtype,
        )
    return path


@pytest.fixture
def valid_noise_bank_run_record(tmp_path: Path) -> Path:
    """Write a tiny valid noise_bank_run_record.json and return its path.

    Matches the valid_noise_bank fixture's parameters so the two files
    represent a coherent producer output. Convention is sibling files
    with matching name stem (e.g. noise_v1.h5 + noise_v1_run_record.json);
    the schema doesn't enforce the pairing so we just write the JSON to
    its own path.
    """
    path = tmp_path / "noise_v1_run_record.json"
    doc = {
        "schema_version": "1.0",
        "created_utc": "2026-06-17T22:00:00Z",
        "source": "iafdb v1.0.0",
        "description": "tiny test fixture",
        "fs_hz": 1000.0,
        "windowing": {
            "window_ms": 512.0,
            "window_samples": 512,
            "hop_ms": 256.0,
        },
        "band_hz": [30.0, 300.0],
        "calibration": {
            "method": "r_wave_anchoring",
            "target_qrs_pp_mv": 1.0,
        },
        "selection": {
            "threshold_mode": "percentile",
            "threshold_value": 10.0,
        },
        "source_records": ["iaf1_afw"],
        "per_trace_provenance": {
            "patient_id": ["iaf1", "iaf1"],
            "start_sample": [0, 256],
            "peak_to_peak_mv": [0.05, 0.07],
            "calibration_scalar": [0.0035, 0.0035],
        },
    }
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


@pytest.fixture
def valid_synthetic_bank(tmp_path: Path) -> Path:
    """Write a tiny valid synthetic bank to a temp file and return its path."""
    path = tmp_path / "synthetic_v1.h5"
    str_dtype = h5py.string_dtype(encoding="utf-8")
    n = 2
    T = 200

    with h5py.File(path, "w") as f:
        f.attrs["schema_version"] = "1.0"
        f.attrs["created_utc"] = "2026-06-15T22:00:00Z"
        f.attrs["description"] = "tiny test fixture"
        f.attrs["fs_hz"] = 1000.0
        f.attrs["trace_duration_ms"] = 200.0
        f.attrs["simulator"] = "finitewave"
        f.attrs["cell_model"] = "aliev_panfilov"
        f.attrs["patch_size_mm"] = 40.0
        f.attrs["patch_dr_mm"] = 0.25
        f.attrs["ap_time_unit_ms"] = 1.0
        f.attrs["fibrosis_strategy_name"] = "uniform_random"
        f.attrs["fibrosis_params_json"] = json.dumps({"density_range": [0.0, 0.5]})
        f.attrs["electrode_config_json"] = json.dumps({"grid_shape": [5, 5]})
        f.attrs["mixer_config_json"] = json.dumps({"enabled": False})
        f.attrs["experiment_config_json"] = json.dumps({"n_simulations": 1})
        f.attrs["noise_bank_source"] = ""

        g = f.create_group("traces")
        g.create_dataset("signal", data=np.zeros((n, T), dtype=np.float32))
        g.create_dataset("simulation_id", data=np.array([0, 0], dtype=np.int64))
        g.create_dataset("pair_index", data=np.array([0, 1], dtype=np.int64))
        g.create_dataset("electrode_row", data=np.array([0, 0], dtype=np.int64))
        g.create_dataset("fibrosis_density", data=np.array([0.3, 0.3], dtype=np.float64))
        g.create_dataset(
            "fibrosis_density_realized",
            data=np.array([0.29, 0.31], dtype=np.float64),
        )
        g.create_dataset("electrode_height_mm", data=np.array([0.5, 0.5], dtype=np.float64))
        g.create_dataset("seed", data=np.array([42, 42], dtype=np.int64))
        g.create_dataset("snr_db", data=np.array([float("nan"), float("nan")], dtype=np.float64))
        g.create_dataset("stim_edge", data=np.array(["top", "top"], dtype=object), dtype=str_dtype)
        g.create_dataset("noise_record", data=np.array(["", ""], dtype=object), dtype=str_dtype)
        g.create_dataset("noise_channel", data=np.array(["", ""], dtype=object), dtype=str_dtype)
    return path


# ---------------------------------------------------------------------------
# JSON / CSV fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_run_record(tmp_path: Path) -> Path:
    """Write a tiny valid run.json and return its path."""
    path = tmp_path / "run.json"
    doc: dict[str, Any] = {
        "schema_version": "1.0",
        "created_utc": "2026-06-15T22:00:00Z",
        "run": {"run_id": "test_run", "git_sha": "abc1234"},
        "config": {"model": {}, "data": {}, "training": {}, "eval": {}},
        "epochs": [
            {
                "epoch": 1,
                "lr": 0.001,
                "train_loss": 0.5,
                "val_loss": 0.45,
                "epoch_seconds": 1.0,
                "val_metrics": {"auroc": 0.85},
                "val_reliability": [
                    {
                        "lo": 0.0,
                        "hi": 0.1,
                        "count": 0,
                        "confidence": None,
                        "accuracy": None,
                    }
                ],
            }
        ],
        "best": {"epoch": 1, "metric": "auroc", "value": 0.85},
    }
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


@pytest.fixture
def valid_metrics_csv(tmp_path: Path) -> Path:
    """Write a tiny valid metrics.csv and return its path."""
    path = tmp_path / "metrics.csv"
    columns = [
        "epoch",
        "lr",
        "train_loss",
        "val_loss",
        "val_auroc",
        "val_accuracy",
        "val_precision",
        "val_recall",
        "val_f1",
        "val_ece",
        "epoch_seconds",
    ]
    rows: list[dict[str, Any]] = [
        {
            "epoch": 1,
            "lr": 0.001,
            "train_loss": 0.5,
            "val_loss": 0.45,
            "val_auroc": 0.85,
            "val_accuracy": 0.8,
            "val_precision": 0.81,
            "val_recall": 0.78,
            "val_f1": 0.79,
            "val_ece": 0.05,
            "epoch_seconds": 1.0,
        },
        # Second row exercises nullable val_metrics columns (empty cells).
        {
            "epoch": 2,
            "lr": 0.001,
            "train_loss": 0.42,
            "val_loss": 0.4,
            "val_auroc": "",
            "val_accuracy": 0.82,
            "val_precision": "",
            "val_recall": 0.8,
            "val_f1": "",
            "val_ece": 0.04,
            "epoch_seconds": 1.0,
        },
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return path


@pytest.fixture
def valid_hybrid_eval_metrics(tmp_path: Path) -> Path:
    """Write a tiny valid hybrid_eval_metrics.json and return its path."""
    path = tmp_path / "hybrid_eval_metrics.json"
    doc: dict[str, Any] = {
        "schema_version": "2.0",
        "created_utc": "2026-06-15T22:00:00Z",
        "producer": {"run_id": "test_run", "model_checkpoint": "checkpoints/best.pt"},
        "mixed": {
            "n": 100,
            "n_positives": 10,
            "n_negatives": 90,
            "metrics": {"auroc": 0.8},
        },
        "iafdb_only": {
            "n": 90,
            "mean_prob_fibrotic": 0.5,
            "fpr_at_0_5": 0.3,
            "p1_prob_fibrotic": 0.05,
        },
    }
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


@pytest.fixture
def valid_model_metadata(tmp_path: Path) -> Path:
    """Write a tiny valid model_metadata.json sidecar and return its path."""
    path = tmp_path / "best.model_metadata.json"
    doc: dict[str, Any] = {
        "schema_version": "1.0",
        "created_utc": "2026-06-15T22:00:00Z",
        "model_artifact": {"filename": "best.onnx", "framework": "onnx"},
        "input": {"name": "signal", "shape": ["?", 1, 512], "dtype": "float32"},
        "output": {
            "name": "logit",
            "shape": ["?", 1],
            "dtype": "float32",
            "semantics": "binary_logit",
        },
        "preprocessing": {
            "expected_fs_hz": 1000.0,
            "expected_trace_samples": 512,
            "bandpass_hz": [30.0, 300.0],
            "normalization": {"scheme": "zscore", "mean": [0.0], "std": [0.42]},
        },
        "decision": {"threshold": 0.5, "class_labels": ["healthy", "fibrotic"]},
        "training_provenance": {"run_id": "test_run"},
    }
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path
