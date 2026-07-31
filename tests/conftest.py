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

from myocard_egm_contracts.schema_info import current_version

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
        f.attrs["schema_version"] = current_version("iafdb_bank")
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
        f.attrs["schema_version"] = current_version("noise_bank")
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
        "schema_version": current_version("noise_bank_run_record"),
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
    """Write a tiny valid synthetic_bank 2.0 to a temp file and return its path.

    Two simulations, two traces each, in the shape the Phase-1.5 Wave-1
    migration produces: today's behavior (one planar-edge stimulus, uniform
    random fibrosis, a density label) expressed through the restructured
    schema, with a theta-spec that records the regime and an empty knob list
    because nothing was swept.
    """
    path = tmp_path / "synthetic_v2.h5"
    str_dtype = h5py.string_dtype(encoding="utf-8")
    n_sims = 2
    n_traces = 4
    trace_len = 192

    def _pairs(height_mm: float) -> list[dict[str, Any]]:
        return [
            {
                "pair_index": i,
                "electrode_indices": [i, i + 1],
                "electrode_row": 0,
                "height_mm": height_mm,
                "midpoint_mm": [17.0 + 2.0 * i, 16.0],
            }
            for i in range(2)
        ]

    heights = [0.5, 0.8]
    densities = [0.05, 0.35]
    realized = [0.048, 0.352]
    labels = [0, 1]  # global-density policy at threshold 0.1

    def _col(values: list[Any]) -> np.ndarray:
        return np.array([json.dumps(v) for v in values], dtype=object)

    with h5py.File(path, "w") as f:
        f.attrs["schema_version"] = current_version("synthetic_bank")
        f.attrs["created_utc"] = "2026-07-30T22:00:00Z"
        f.attrs["description"] = "tiny test fixture"
        f.attrs["fs_hz"] = 1000.0
        f.attrs["trace_duration_ms"] = float(trace_len)
        f.attrs["noise_bank_source"] = ""
        f.attrs["generation_params_json"] = json.dumps(
            {
                "regime": {
                    "geometry": "patch_2d",
                    "cell_model": "aliev_panfilov",
                    "substrate": "uniform_random_fibrosis",
                    "activation": "planar_edge",
                    "electrodes": "centered_grid_2d",
                    "backend": "finitewave",
                    "label_policy": "global_density",
                },
                "knobs": [],
            }
        )

        sims = f.create_group("simulations")
        sims.create_dataset("simulation_id", data=np.arange(n_sims, dtype=np.int64))
        sims.create_dataset("seed", data=np.array([42, 43], dtype=np.int64))
        sims.create_dataset(
            "geometry_json",
            data=_col([{"type": "patch_2d", "size_mm": 40.0, "dr_mm": 0.25}] * n_sims),
            dtype=str_dtype,
        )
        sims.create_dataset(
            "cell_model_json",
            data=_col([{"type": "aliev_panfilov", "ap_time_unit_ms": 12.9}] * n_sims),
            dtype=str_dtype,
        )
        sims.create_dataset(
            "substrate_json",
            data=_col([{"type": "uniform_random_fibrosis", "density": d} for d in densities]),
            dtype=str_dtype,
        )
        sims.create_dataset(
            "substrate_summary_json",
            data=_col([{"realized_density": r} for r in realized]),
            dtype=str_dtype,
        )
        sims.create_dataset(
            "activation_json",
            data=_col([{"type": "planar_edge", "edges": ["top"], "voltage": 1.0}] * n_sims),
            dtype=str_dtype,
        )
        sims.create_dataset(
            "electrodes_json",
            data=_col(
                [
                    {
                        "type": "centered_grid_2d",
                        "n_rows": 5,
                        "n_cols": 5,
                        "spacing_mm": 2.0,
                        "height_mm": h,
                        "pairs": _pairs(h),
                    }
                    for h in heights
                ]
            ),
            dtype=str_dtype,
        )
        sims.create_dataset(
            "backend_json",
            data=_col(
                [{"type": "finitewave", "output_fs_hz": 1000.0, "capture_oversample": 4}] * n_sims
            ),
            dtype=str_dtype,
        )
        sims.create_dataset(
            "label_policy_json",
            data=_col([{"type": "global_density", "thresholds": [0.1]}] * n_sims),
            dtype=str_dtype,
        )
        sims.create_dataset(
            "label_names_json",
            data=_col([{"0": "healthy", "1": "fibrotic"}] * n_sims),
            dtype=str_dtype,
        )

        g = f.create_group("traces")
        g.create_dataset("signal", data=np.zeros((n_traces, trace_len), dtype=np.float32))
        g.create_dataset("simulation_id", data=np.array([0, 0, 1, 1], dtype=np.int64))
        g.create_dataset("pair_index", data=np.array([0, 1, 0, 1], dtype=np.int64))
        g.create_dataset(
            "label",
            data=np.array([labels[0], labels[0], labels[1], labels[1]], dtype=np.int64),
        )
        g.create_dataset("snr_db", data=np.full(n_traces, np.nan, dtype=np.float64))
        g.create_dataset(
            "noise_record", data=np.array([""] * n_traces, dtype=object), dtype=str_dtype
        )
        g.create_dataset(
            "noise_channel", data=np.array([""] * n_traces, dtype=object), dtype=str_dtype
        )
    return path


# ---------------------------------------------------------------------------
# JSON / CSV fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_training_run_record(tmp_path: Path) -> Path:
    """Write a tiny valid run.json and return its path."""
    path = tmp_path / "run.json"
    doc: dict[str, Any] = {
        "schema_version": current_version("training_run_record"),
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
def valid_training_metrics_csv(tmp_path: Path) -> Path:
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
def valid_egm_class_model_metadata(tmp_path: Path) -> Path:
    """Write a tiny valid egm_class_model_metadata JSON sidecar and return its path."""
    path = tmp_path / "best.model_metadata.json"
    doc: dict[str, Any] = {
        "schema_version": current_version("egm_class_model_metadata"),
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
            "normalization": {"scheme": "zscore"},
        },
        "decision": {"threshold": 0.5, "class_labels": ["healthy", "fibrotic"]},
        "training_provenance": {"run_id": "test_run"},
    }
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path
