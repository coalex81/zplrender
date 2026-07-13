"""Backend-independent document model."""

from dataclasses import dataclass

from zplrender.diagnostics import Diagnostic
from zplrender.elements import LabelElement


@dataclass(frozen=True)
class LabelPage:
    """A backend-independent printable label."""

    elements: tuple[LabelElement, ...]


@dataclass(frozen=True)
class ParsedDocument:
    """Pages and diagnostics produced by the ZPL interpreter."""

    pages: tuple[LabelPage, ...]
    diagnostics: tuple[Diagnostic, ...]
