"""Backend-independent renderer interfaces."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RenderOptions:
    """Physical and raster dimensions used for label rendering."""

    dpi: int = 203
    width: int = 812
    height: int = 1218

    def __post_init__(self) -> None:
        if self.dpi <= 0 or self.width <= 0 or self.height <= 0:
            raise ValueError("DPI and page dimensions must be positive")
