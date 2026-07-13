"""Compare zplrender output with the stored Labelary reference."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from zplrender import render


PROJECT_ROOT = Path(__file__).parents[1]
DEFAULT_SOURCE = PROJECT_ROOT / "tests" / "fixtures" / "zpl" / "shipping_label.zpl"
DEFAULT_REFERENCE = PROJECT_ROOT / "benchmarks" / "reference" / "shipping_label.png"


def thresholded_pixel_difference(source: Path, reference_path: Path) -> float:
    """Return the percentage of black/white pixels that differ."""
    actual = render(source.read_text(encoding="utf-8"), strict=True).pages[0].convert("L")
    with Image.open(reference_path) as reference_image:
        reference = reference_image.convert("L")
    if actual.size != reference.size:
        raise ValueError(f"Image sizes differ: zplrender={actual.size}, reference={reference.size}")

    differing = sum(
        (actual_pixel < 128) != (reference_pixel < 128)
        for actual_pixel, reference_pixel in zip(actual.tobytes(), reference.tobytes())
    )
    return differing * 100 / (actual.width * actual.height)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    arguments = parser.parse_args()
    difference = thresholded_pixel_difference(arguments.source, arguments.reference)
    print(f"Thresholded pixel difference: {difference:.4f}%")


if __name__ == "__main__":
    main()
