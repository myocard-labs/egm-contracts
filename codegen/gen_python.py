"""Generate Pydantic models from the JSON Schema files in schemas/.

Run from the repo root::

    python codegen/gen_python.py

Writes one .py file per .schema.json into ``src/myocard_egm_contracts/_generated/python/``.
The generated files are committed to the repo so consumers do not need
``datamodel-code-generator`` installed. CI re-runs this script and asserts
the output is unchanged — see the ``codegen-drift`` job in ``.github/workflows/ci.yml``.

Convention: the JSON Schema files are the master truth (see the
``feedback-schemas-json-schema-first`` memory). Never edit generated code by hand;
edit the schema and re-run this script.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = REPO_ROOT / "src" / "myocard_egm_contracts" / "schemas"
OUTPUT_DIR = REPO_ROOT / "src" / "myocard_egm_contracts" / "_generated" / "python"


def _gen_one(schema_path: Path, output_path: Path) -> None:
    """Run datamodel-code-generator on one schema file."""
    cmd = [
        sys.executable,
        "-m",
        "datamodel_code_generator",
        "--input",
        str(schema_path),
        "--input-file-type",
        "jsonschema",
        "--output",
        str(output_path),
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--target-python-version",
        "3.10",
        "--use-schema-description",
        "--use-field-description",
        "--field-constraints",
        "--use-double-quotes",
        "--snake-case-field",
        "--collapse-root-models",
        # Reproducibility: no timestamp in the generated header (CI drift check
        # would otherwise fail on every run since the header changes).
        "--disable-timestamp",
        # Explicit formatters silence the FutureWarning about default behavior
        # changing in a future datamodel-code-generator release.
        "--formatters",
        "black",
        "isort",
    ]
    print(f"  {schema_path.name} -> {output_path.relative_to(REPO_ROOT)}")
    subprocess.run(cmd, check=True)


def main() -> int:
    if not SCHEMAS_DIR.is_dir():
        print(f"ERROR: schemas dir not found: {SCHEMAS_DIR}", file=sys.stderr)
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Clean stale generated files before regenerating so renames/deletions
    # in schemas/ are reflected here. Keep .gitkeep so the directory survives.
    for stale in OUTPUT_DIR.glob("*.py"):
        stale.unlink()

    schemas = sorted(SCHEMAS_DIR.glob("*.schema.json"))
    if not schemas:
        print(f"ERROR: no .schema.json files found in {SCHEMAS_DIR}", file=sys.stderr)
        return 1

    print(f"Generating {len(schemas)} Pydantic model file(s)...")
    for schema_path in schemas:
        # foo.schema.json -> foo.py
        stem = schema_path.name.replace(".schema.json", "")
        output_path = OUTPUT_DIR / f"{stem}.py"
        _gen_one(schema_path, output_path)

    # Generate an __init__.py that re-exports each model.
    init_lines = [
        '"""Auto-generated from JSON Schemas in ../../schemas/.',
        "",
        "Do not edit by hand. Regenerate via ``python codegen/gen_python.py``.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
    ]
    for schema_path in schemas:
        stem = schema_path.name.replace(".schema.json", "")
        init_lines.append(f"from . import {stem}  # noqa: F401")
    init_lines.append("")
    (OUTPUT_DIR / "__init__.py").write_text("\n".join(init_lines), encoding="utf-8")
    print(f"Wrote {OUTPUT_DIR / '__init__.py'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
