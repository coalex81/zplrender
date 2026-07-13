"""Graphical element models."""

from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True)
class RasterGraphic:
    """A decoded, one-bit printer bitmap."""

    width: int
    height: int
    bytes_per_row: int
    data: bytes


@dataclass(frozen=True)
class RasterElement:
    """A raster graphic placed on a label page."""

    x: int
    y: int
    graphic: RasterGraphic
    scale_x: int = 1
    scale_y: int = 1
    reverse: bool = False


@dataclass(frozen=True)
class FieldBlock:
    """Text wrapping and alignment options from ``^FB``."""

    width: int
    max_lines: int = 1
    line_spacing: int = 0
    alignment: str = "L"
    hanging_indent: int = 0


@dataclass(frozen=True)
class TextElement:
    """Decoded text placed independently of a rendering backend."""

    x: int
    y: int
    text: str
    font: str = "0"
    height: int = 30
    width: int = 30
    orientation: str = "N"
    block: FieldBlock | None = None
    reverse: bool = False


@dataclass(frozen=True)
class BoxElement:
    """A box or line described by ``^GB``."""

    x: int
    y: int
    width: int
    height: int
    thickness: int = 1
    color: str = "B"
    rounding: int = 0
    reverse: bool = False


@dataclass(frozen=True)
class Code128Element:
    """A Code 128 barcode field."""

    x: int
    y: int
    data: str
    height: int
    module_width: int = 2
    interpretation_line: bool = True
    interpretation_above: bool = False
    reverse: bool = False


@dataclass(frozen=True)
class QRCodeElement:
    """A QR Code Model 2 field."""

    x: int
    y: int
    data: str
    magnification: int = 2
    error_correction: str = "Q"
    mask: int | None = None
    reverse: bool = False


LabelElement: TypeAlias = (
    RasterElement | TextElement | BoxElement | Code128Element | QRCodeElement
)
