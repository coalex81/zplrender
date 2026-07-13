"""Font selection and sizing policy for ZPL printer fonts."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from PIL import ImageFont

from zplrender.exceptions import ZPLRenderError


@dataclass(frozen=True)
class FontSpec:
    """Ordered substitutes and metric calibration for one printer font."""

    candidates: tuple[str, ...]
    size_scale: float = 1.0


class FontRegistry:
    """Resolve supported ZPL fonts through deterministic fallback policies."""

    def __init__(self, specifications: dict[str, FontSpec] | None = None) -> None:
        self._specifications = specifications or {
            "0": FontSpec(
                candidates=(
                    "LiberationSansNarrow-Bold.ttf",
                    "DejaVuSans-Bold.ttf",
                    "DejaVuSans.ttf",
                ),
                size_scale=1.03,
            )
        }

    def load(self, name: str, height: int) -> ImageFont.FreeTypeFont:
        """Load a calibrated substitute at the requested ZPL character height."""
        specification = self._specifications.get(name)
        if specification is None:
            raise ZPLRenderError(f"Unsupported printer font: {name}")
        size = max(1, round(height * specification.size_scale))
        return _load_first_available(specification.candidates, size)


@lru_cache(maxsize=128)
def _load_first_available(candidates: tuple[str, ...], size: int) -> ImageFont.FreeTypeFont:
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    raise ZPLRenderError("No supported open-source font substitute was found")


DEFAULT_FONT_REGISTRY = FontRegistry()
