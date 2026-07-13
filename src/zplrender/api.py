"""High-level public API."""

from dataclasses import dataclass
from os import PathLike

from PIL import Image

from zplrender.diagnostics import Diagnostic
from zplrender.document import ParsedDocument
from zplrender.parser import parse
from zplrender.renderers.base import RenderOptions
from zplrender.renderers.pdf import save_pdf
from zplrender.renderers.pillow import render_document


@dataclass
class RenderResult:
    """Rendered Pillow pages and interpreter diagnostics."""

    pages: tuple[Image.Image, ...]
    diagnostics: tuple[Diagnostic, ...]
    dpi: int

    def to_pdf(self, output: str | PathLike[str]) -> None:
        """Save all rendered pages to one PDF."""
        save_pdf(self.pages, output, dpi=self.dpi)


@dataclass(frozen=True)
class ZPLDocument:
    """A parsed, backend-independent ZPL document."""

    source: str
    parsed: ParsedDocument

    @classmethod
    def parse(cls, source: str, *, strict: bool = False) -> "ZPLDocument":
        """Create a document from raw ZPL source."""
        return cls(source=source, parsed=parse(source, strict=strict))

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        """Return diagnostics produced while interpreting the source."""
        return self.parsed.diagnostics

    def render(
        self,
        *,
        dpi: int = 203,
        width: int = 812,
        height: int = 1218,
    ) -> RenderResult:
        """Render every printable label in the document."""
        options = RenderOptions(dpi=dpi, width=width, height=height)
        return RenderResult(
            pages=render_document(self.parsed, options),
            diagnostics=self.parsed.diagnostics,
            dpi=dpi,
        )


def render(
    source: str,
    *,
    dpi: int = 203,
    width: int = 812,
    height: int = 1218,
    strict: bool = False,
) -> RenderResult:
    """Parse and render all printable labels in a ZPL stream."""
    return ZPLDocument.parse(source, strict=strict).render(
        dpi=dpi,
        width=width,
        height=height,
    )


def render_pdf(
    source: str,
    output: str | PathLike[str],
    *,
    dpi: int = 203,
    width: int = 812,
    height: int = 1218,
    strict: bool = False,
) -> RenderResult:
    """Parse ZPL and save every printable label to a PDF."""
    result = render(
        source,
        dpi=dpi,
        width=width,
        height=height,
        strict=strict,
    )
    result.to_pdf(output)
    return result
