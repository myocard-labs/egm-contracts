"""Tests for the public schema introspection API."""

from __future__ import annotations

import pytest

from myocard_egm_contracts.schema_info import (
    csv_column_order,
    csv_required_columns,
    current_version,
    field_type_map,
    get_schema,
    supported_versions,
)

# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------


def test_supported_versions_returns_enum_for_each_schema() -> None:
    """Every versioned schema should advertise its allowed schema_version
    values as a non-empty tuple. If this returns empty for a schema that
    is supposed to be versioned, the enum was dropped accidentally."""
    for name in (
        "synthetic_bank",
        "iafdb_bank",
        "noise_bank",
        "noise_bank_run_record",
        "run_record",
        "hybrid_eval_metrics",
        "model_metadata",
    ):
        versions = supported_versions(name)
        assert len(versions) >= 1, f"{name} has no schema_version enum"


def test_current_version_is_the_last_supported() -> None:
    """current_version is what writers should stamp; by convention it's
    the newest entry in the schema's enum (the last). Confirms the
    contract a writer relies on."""
    versions = supported_versions("synthetic_bank")
    assert current_version("synthetic_bank") == versions[-1]


def test_metrics_has_no_schema_version() -> None:
    """metrics.schema.json describes one row of a CSV, not a versioned
    document; it has no schema_version field. supported_versions should
    return an empty tuple and current_version should raise."""
    assert supported_versions("metrics") == ()
    with pytest.raises(ValueError, match="has no schema_version field"):
        current_version("metrics")


# ---------------------------------------------------------------------------
# CSV column order
# ---------------------------------------------------------------------------


def test_metrics_csv_column_order_falls_back_to_properties() -> None:
    """metrics.schema.json has no x-csv-column-order extension; the helper
    falls back to the properties insertion order. Confirms the fallback
    path works."""
    columns = csv_column_order("metrics")
    assert columns[0] == "epoch"
    assert "val_auroc" in columns


# ---------------------------------------------------------------------------
# Required columns + field type map
# ---------------------------------------------------------------------------


def test_metrics_required_columns() -> None:
    """The metrics schema marks epoch / lr / train_loss / val_loss /
    epoch_seconds as required and non-nullable. csv_required_columns
    returns that set so readers can refuse a malformed row."""
    required = csv_required_columns("metrics")
    assert {"epoch", "lr", "train_loss", "val_loss", "epoch_seconds"}.issubset(required)


def test_field_type_map_normalizes_nullable_types() -> None:
    """val_auroc is declared as ["number", "null"] (nullable); the helper
    returns both elements as a tuple. epoch is just "integer" and returns
    a one-tuple. Catches a regression where a nullable column gets coerced
    to non-nullable."""
    types = field_type_map("metrics")
    assert types["epoch"] == ("integer",)
    assert "null" in types["val_auroc"]
    assert "number" in types["val_auroc"]


# ---------------------------------------------------------------------------
# Raw schema escape hatch
# ---------------------------------------------------------------------------


def test_get_schema_returns_dict_with_expected_top_level_keys() -> None:
    """The raw schema dict should at least have $schema and title for any
    well-formed JSON-Schema-Draft-2020-12 file. This is the escape hatch
    for tools that need to do their own walking."""
    schema = get_schema("synthetic_bank")
    assert schema.get("$schema", "").startswith("https://json-schema.org/draft/")
    assert schema.get("title") == "SyntheticBank"


def test_get_schema_raises_for_unknown_name() -> None:
    """A typo or non-existent schema name should fail loudly with a
    FileNotFoundError, not silently return an empty dict."""
    with pytest.raises(FileNotFoundError):
        get_schema("not_a_real_schema")
