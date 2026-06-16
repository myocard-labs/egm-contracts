"""CI guard: verify schema_version bumps on schema changes.

For every modified ``.schema.json`` file in
``src/myocard_egm_contracts/schemas/``, compare its ``schema_version``
constant on this branch vs the merge base. If the schema file changed
but the version constant did not, fail with a clear error message.

Bypass: add the ``skip-schema-bump`` label to the PR for non-substantive
changes (description-only edits, internal $defs reshuffling, formatting).
The CI workflow checks for that label before invoking this script.

Run from repo root::

    python tools/check_schema_versions.py

In CI, set ``BASE_REF`` (or rely on the ``GITHUB_BASE_REF`` env var GitHub
provides on pull_request events). For local dry-runs against ``release``::

    BASE_REF=release python tools/check_schema_versions.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCHEMA_DIR = Path("src/myocard_egm_contracts/schemas")


def _extract_version(schema_dict: dict) -> str | None:
    """Pull the ``schema_version`` constant out of a schema dict.

    Returns the enum-of-one value, falling back to ``const`` if a schema
    hasn't been migrated to the enum pattern yet.
    """
    entry = schema_dict.get("properties", {}).get("schema_version")
    if not isinstance(entry, dict):
        return None
    enum_vals = entry.get("enum")
    if isinstance(enum_vals, list) and len(enum_vals) == 1:
        return str(enum_vals[0])
    const = entry.get("const")
    if const is not None:
        return str(const)
    return None


def _changed_schemas(base_ref: str) -> list[Path]:
    """List schema files that differ from base_ref to HEAD."""
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            f"{base_ref}...HEAD",
            "--",
            str(SCHEMA_DIR / "*.schema.json"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return [Path(p) for p in result.stdout.strip().splitlines() if p]


def _version_at(ref: str, path: Path) -> str | None:
    """Extract version from the file as it existed at ``ref`` (or None if absent)."""
    try:
        content = subprocess.run(
            ["git", "show", f"{ref}:{path}"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except subprocess.CalledProcessError:
        return None  # file did not exist at ref (new schema)
    try:
        return _extract_version(json.loads(content))
    except json.JSONDecodeError:
        return None


def main() -> int:
    base_ref = os.environ.get("BASE_REF") or os.environ.get("GITHUB_BASE_REF") or "origin/release"
    # Normalize: if BASE_REF is a bare branch name, prefix with origin/.
    if base_ref and not base_ref.startswith("origin/") and "/" not in base_ref:
        base_ref = f"origin/{base_ref}"

    print(f"Comparing schema versions against base: {base_ref}")

    try:
        changed = _changed_schemas(base_ref)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: git diff failed: {e.stderr}", file=sys.stderr)
        return 2

    if not changed:
        print("No schema changes detected. Nothing to check.")
        return 0

    failed: list[tuple[Path, str | None]] = []
    new_schemas: list[Path] = []

    for schema_path in changed:
        if not schema_path.exists():
            print(f"DELETED  {schema_path}")
            continue

        try:
            current = json.loads(schema_path.read_text())
        except json.JSONDecodeError as e:
            print(f"ERROR: {schema_path} is not valid JSON: {e}", file=sys.stderr)
            return 2

        new_version = _extract_version(current)
        old_version = _version_at(base_ref, schema_path)

        if old_version is None:
            print(f"NEW      {schema_path}  (version={new_version})")
            new_schemas.append(schema_path)
            continue

        if new_version == old_version:
            print(f"DRIFT    {schema_path}  version unchanged at {old_version!r}")
            failed.append((schema_path, new_version))
        else:
            print(f"BUMPED   {schema_path}  {old_version!r} -> {new_version!r}")

    if failed:
        print()
        print("ERROR: schema files changed without bumping schema_version.")
        print()
        for path, ver in failed:
            print(f"  - {path} (still {ver!r})")
        print()
        print("Either:")
        print("  1. Bump the schema_version constant inside the schema, OR")
        print("  2. Add label 'skip-schema-bump' to the PR for non-substantive")
        print("     changes (description fixes, internal $defs refactor, formatting).")
        print()
        print("See project/schema_evolution.md for the full rule.")
        return 1

    print()
    print(f"OK: {len(changed)} schema change(s) all bumped (or new).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
