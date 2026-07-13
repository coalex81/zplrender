"""Structured parser and renderer diagnostics."""

from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    """Diagnostic severity."""

    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class Diagnostic:
    """A structured issue found while interpreting ZPL."""

    severity: Severity
    code: str
    message: str
    offset: int | None = None
    command: str | None = None
