"""myocard-egm-contracts — cross-language data-format schemas + validators.

The JSON Schemas in ``schemas/`` are the master truth. Python consumers get
Pydantic models that were generated from those schemas; C++ consumers will
(eventually) get equivalent structs the same way.

Public API surface (all re-exported here for convenience):

- **Schema models** — Pydantic v2 ``BaseModel`` classes, one per format. Use
  for type-safe construction, ``.model_validate(data)`` for incoming JSON, and
  ``.model_dump()`` for outgoing data.
- **Schema source files** — the raw ``.schema.json`` files are also shipped in
  the wheel under ``myocard_egm_contracts.schemas`` and can be loaded via
  ``importlib.resources`` for tools that want the JSON Schema directly.
- **Validators** — file-level conformance checkers (``validate_*``). These open
  the actual HDF5 / CSV / JSON file, map it onto the schema-shaped envelope,
  and run ``jsonschema`` validation.

Example::

    from myocard_egm_contracts import iafdb_healthy_bank
    from myocard_egm_contracts.validators import validate_iafdb_healthy_bank

    # Type-safe construction (raises pydantic.ValidationError on bad input).
    bank = iafdb_healthy_bank.IafdbHealthyBank.model_validate(some_dict)

    # File-level conformance check (returns ValidationResult).
    result = validate_iafdb_healthy_bank(Path("iafdb_healthy_v1.h5"))
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
        hybrid_eval_metrics,
        iafdb_healthy_bank,
        metrics,
        model_metadata,
        predictions,
        run_record,
        synthetic_bank,
    )
except ImportError:  # pragma: no cover — happens only before first codegen run
    hybrid_eval_metrics = None  # type: ignore[assignment]
    iafdb_healthy_bank = None  # type: ignore[assignment]
    metrics = None  # type: ignore[assignment]
    model_metadata = None  # type: ignore[assignment]
    predictions = None  # type: ignore[assignment]
    run_record = None  # type: ignore[assignment]
    synthetic_bank = None  # type: ignore[assignment]

# Re-export the validators so consumers can `from myocard_egm_contracts
# import validate_synthetic_bank` without knowing about the subpackage.
from myocard_egm_contracts.validators import (
    ValidationResult,
    validate_hybrid_eval_metrics,
    validate_iafdb_healthy_bank,
    validate_metrics,
    validate_model_metadata,
    validate_predictions,
    validate_run_record,
    validate_synthetic_bank,
)

try:
    __version__ = metadata.version("myocard-egm-contracts")
except metadata.PackageNotFoundError:  # pragma: no cover — editable install w/o metadata
    __version__ = "0.0.0+unknown"


__all__ = [
    "ValidationResult",
    "__version__",
    "hybrid_eval_metrics",
    "iafdb_healthy_bank",
    "metrics",
    "model_metadata",
    "predictions",
    "run_record",
    "synthetic_bank",
    "validate_hybrid_eval_metrics",
    "validate_iafdb_healthy_bank",
    "validate_metrics",
    "validate_model_metadata",
    "validate_predictions",
    "validate_run_record",
    "validate_synthetic_bank",
]
