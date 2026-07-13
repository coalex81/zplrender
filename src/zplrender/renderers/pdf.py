"""PDF rendering backend."""

from collections.abc import Sequence
from os import PathLike

from PIL import Image

from zplrender.exceptions import ZPLRenderError


def save_pdf(pages: Sequence[Image.Image], output: str | PathLike[str], *, dpi: int) -> None:
    """Save rendered pages as one image-backed PDF."""
    if not pages:
        raise ZPLRenderError("Cannot create a PDF without printable label pages")

    first, *remaining = (page.convert("1") for page in pages)
    first.save(
        output,
        format="PDF",
        save_all=True,
        append_images=remaining,
        resolution=float(dpi),
    )
