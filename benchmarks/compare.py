"""Compare zplrender output with the stored Labelary reference."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from zplrender import render


PROJECT_ROOT = Path(__file__).parents[1]
DEFAULT_SOURCE = PROJECT_ROOT / "tests" / "fixtures" / "zpl" / "shipping_label.zpl"
DEFAULT_REFERENCE = PROJECT_ROOT / "benchmarks" / "reference" / "shipping_label.png"


@dataclass(frozen=True)
class Region:
    """Named label area measured independently."""

    name: str
    box: tuple[int, int, int, int]


@dataclass(frozen=True)
class RegionDifference:
    """Thresholded difference metrics for one label area."""

    region: Region
    differing_pixels: int
    total_pixels: int
    contribution_pixels: int

    @property
    def percentage(self) -> float:
        return self.differing_pixels * 100 / self.total_pixels

    @property
    def contribution_percentage(self) -> float:
        if not self.contribution_pixels:
            return 0.0
        return self.differing_pixels * 100 / self.contribution_pixels


REGIONS = (
    Region("header", (0, 0, 812, 210)),
    Region("barcode", (0, 210, 812, 450)),
    Region("routing", (0, 450, 812, 780)),
    Region("routing_details", (0, 780, 812, 950)),
    Region("recipient", (0, 950, 650, 1218)),
    Region("qr", (650, 950, 812, 1218)),
)


def _load_images(source: Path, reference_path: Path) -> tuple[Image.Image, Image.Image]:
    actual = render(source.read_text(encoding="utf-8"), strict=True).pages[0].convert("L")
    with Image.open(reference_path) as reference_image:
        reference = reference_image.convert("L")
    if actual.size != reference.size:
        raise ValueError(f"Image sizes differ: zplrender={actual.size}, reference={reference.size}")
    return actual, reference


def _differing_pixels(actual: Image.Image, reference: Image.Image) -> int:
    return sum(
        (actual_pixel < 128) != (reference_pixel < 128)
        for actual_pixel, reference_pixel in zip(actual.tobytes(), reference.tobytes())
    )


def thresholded_pixel_difference(source: Path, reference_path: Path) -> float:
    """Return the percentage of black/white pixels that differ."""
    actual, reference = _load_images(source, reference_path)
    differing = _differing_pixels(actual, reference)
    return differing * 100 / (actual.width * actual.height)


def regional_differences(source: Path, reference_path: Path) -> tuple[RegionDifference, ...]:
    """Measure difference rate and total-error contribution by label region."""
    actual, reference = _load_images(source, reference_path)
    total_differing = _differing_pixels(actual, reference)
    results: list[RegionDifference] = []
    for region in REGIONS:
        actual_crop = actual.crop(region.box)
        reference_crop = reference.crop(region.box)
        results.append(
            RegionDifference(
                region=region,
                differing_pixels=_differing_pixels(actual_crop, reference_crop),
                total_pixels=actual_crop.width * actual_crop.height,
                contribution_pixels=total_differing,
            )
        )
    return tuple(results)


def print_report(source: Path, reference_path: Path) -> None:
    """Print the overall baseline and a ranked regional error table."""
    difference = thresholded_pixel_difference(source, reference_path)
    print(f"Thresholded pixel difference: {difference:.4f}%")
    print()
    print(f"{'Region':<18} {'Difference':>12} {'Contribution':>14}  Bounds")
    for result in sorted(
        regional_differences(source, reference_path),
        key=lambda item: item.differing_pixels,
        reverse=True,
    ):
        print(
            f"{result.region.name:<18} {result.percentage:>11.4f}% "
            f"{result.contribution_percentage:>13.2f}%  {result.region.box}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    arguments = parser.parse_args()
    print_report(arguments.source, arguments.reference)


if __name__ == "__main__":
    main()
