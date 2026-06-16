"""ValidationResult dataclass: the return type of every validator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of validating a file against one of the schemas.

    Attributes
    ----------
    ok
        True iff the file conformed cleanly.
    path
        Path that was checked.
    issues
        Tuple of human-readable issue messages. Empty when ok is True.
        Each message is prefixed with the JSON-Schema path of the offending
        field (e.g., ``"traces/signal: ..."``) where applicable.

    The class supports truthiness so callers can write::

        if not validate_iafdb_healthy_bank(path):
            ...
    """

    ok: bool
    path: Path
    issues: tuple[str, ...] = field(default_factory=tuple)

    def __bool__(self) -> bool:
        return self.ok

    @classmethod
    def passing(cls, path: Path) -> ValidationResult:
        """Construct a passing result."""
        return cls(ok=True, path=path, issues=())

    @classmethod
    def failing(cls, path: Path, issues: list[str] | tuple[str, ...]) -> ValidationResult:
        """Construct a failing result. ``issues`` is materialized into a tuple."""
        return cls(ok=False, path=path, issues=tuple(issues))
