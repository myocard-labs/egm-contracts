"""myocard-egm-contracts — cross-language data-format schemas + validators.

The JSON Schemas in ``schemas/`` are the master truth. Python consumers get
Pydantic models that were generated from those schemas; C++ consumers will
(eventually) get equivalent structs the same way.

Public API surface (all re-exported here for convenience):

- **Schema models** — Pydantic v2 ``BaseModel`` classes, one per format. Use
  for type-safe construction, ``.model_validate(data)`` for incoming JSON, and
  ``.model_dump()`` for outgoing data. The ``common`` module holds the shared
  stable-id types (``ArtifactId`` / ``FigureId`` / ``PaperId``) referenced
  cross-file by the other schemas; consumers can validate an id via e.g.
  ``myocard_egm_contracts.common.ArtifactId(value)``.
- **Schema source files** — the raw ``.schema.json`` files are also shipped in
  the wheel under ``myocard_egm_contracts.schemas`` and can be loaded via
  ``importlib.resources`` for tools that want the JSON Schema directly.
- **Validators** — file-level conformance checkers (``validate_*``). These open
  the actual HDF5 / CSV / JSON file, map it onto the schema-shaped envelope,
  and run ``jsonschema`` validation.
- **Role vocabulary** — the generated ``Role`` enum + the id-prefix-to-role map
  ``ROLE_PREFIXES`` (single-sourced in ``codegen/roles.json``), plus the
  hand-written ``role_of(id)`` classifier over them. Lets a consumer map a
  stable artifact id to its pipeline role one way.

Example::

    from myocard_egm_contracts import iafdb_bank
    from myocard_egm_contracts.validators import validate_iafdb_bank

    # Type-safe construction (raises pydantic.ValidationError on bad input).
    bank = iafdb_bank.IafdbBank.model_validate(some_dict)

    # File-level conformance check (returns ValidationResult).
    result = validate_iafdb_bank(Path("iafdb_v1.h5"))
    if not result.ok:
        for issue in result.issues:
            print(issue)
"""

from __future__ import annotations

from importlib import metadata

# Re-export generated Pydantic model modules. These are produced by
# ``python codegen/gen_python.py`` from the JSON Schemas in ./schemas/
# and committed to the repo. If you see an ImportError here on a fresh
# clone, run ``pip install -e ".[dev]" && python codegen/gen_python.py``.
try:
    from myocard_egm_contracts._generated.python import (
        common,
        egm_class_model_metadata,
        figure_spec,
        iafdb_bank,
        noise_bank,
        noise_bank_run_record,
        observation,
        phase_manifest,
        synthetic_bank,
        training_metrics,
        training_run_record,
    )
except ImportError:  # pragma: no cover — happens only before first codegen run
    common = None  # type: ignore[assignment]
    egm_class_model_metadata = None  # type: ignore[assignment]
    figure_spec = None  # type: ignore[assignment]
    iafdb_bank = None  # type: ignore[assignment]
    noise_bank = None  # type: ignore[assignment]
    noise_bank_run_record = None  # type: ignore[assignment]
    observation = None  # type: ignore[assignment]
    phase_manifest = None  # type: ignore[assignment]
    synthetic_bank = None  # type: ignore[assignment]
    training_metrics = None  # type: ignore[assignment]
    training_run_record = None  # type: ignore[assignment]

# Re-export the validators so consumers can `from myocard_egm_contracts
# import validate_synthetic_bank` without knowing about the subpackage.
# Re-export the schema introspection API. Consumers (e.g. myocard-egm-data
# writers and readers) should pull schema versions, CSV column orders, and
# type maps through these helpers rather than redeclaring them.
from myocard_egm_contracts.roles import ROLE_PREFIXES, Role, role_of
from myocard_egm_contracts.schema_info import (
    csv_column_order,
    csv_required_columns,
    current_version,
    field_type_map,
    get_schema,
    supported_versions,
)
from myocard_egm_contracts.validators import (
    ValidationResult,
    validate_egm_class_model_metadata,
    validate_figure_spec,
    validate_iafdb_bank,
    validate_noise_bank,
    validate_noise_bank_run_record,
    validate_observation,
    validate_phase_manifest,
    validate_synthetic_bank,
    validate_training_metrics,
    validate_training_run_record,
)

try:
    __version__ = metadata.version("myocard-egm-contracts")
except metadata.PackageNotFoundError:  # pragma: no cover — editable install w/o metadata
    __version__ = "0.0.0+unknown"


__all__ = [
    "ROLE_PREFIXES",
    "Role",
    "ValidationResult",
    "__version__",
    "common",
    "csv_column_order",
    "csv_required_columns",
    "current_version",
    "egm_class_model_metadata",
    "field_type_map",
    "figure_spec",
    "get_schema",
    "iafdb_bank",
    "noise_bank",
    "noise_bank_run_record",
    "observation",
    "phase_manifest",
    "role_of",
    "supported_versions",
    "synthetic_bank",
    "training_metrics",
    "training_run_record",
    "validate_egm_class_model_metadata",
    "validate_figure_spec",
    "validate_iafdb_bank",
    "validate_noise_bank",
    "validate_noise_bank_run_record",
    "validate_observation",
    "validate_phase_manifest",
    "validate_synthetic_bank",
    "validate_training_metrics",
    "validate_training_run_record",
]
