"""Generate one Labelary PNG reference for each label in the ZIP fixture."""

from __future__ import annotations

import argparse
import time
import urllib.error
import urllib.request
from pathlib import Path
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).parents[1]
DEFAULT_ARCHIVE = PROJECT_ROOT / "tests" / "fixtures" / "archives" / "shopee_shipping_labels.zip"
DEFAULT_OUTPUT_DIRECTORY = PROJECT_ROOT / "benchmarks" / "reference" / "shopee_shipping_labels"
ARCHIVE_MEMBER = "thermal_zpl_shipping_label.txt"
LABELARY_URL_TEMPLATE = "https://api.labelary.com/v1/printers/8dpmm/labels/4x6/{index}/"
PAGE_COUNT = 7


def request_png(zpl: bytes, index: int) -> bytes:
    """Render one indexed label from a complete ZPL document as PNG."""
    request = urllib.request.Request(
        LABELARY_URL_TEMPLATE.format(index=index),
        data=zpl,
        headers={
            "Accept": "image/png",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "zplrender-benchmark/0.1",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content = bytes(response.read())
            content_type = response.headers.get_content_type()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Labelary returned HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not reach Labelary: {error.reason}") from error

    if content_type != "image/png" or not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError(f"Labelary returned {content_type}, not a PNG image")
    return content


def generate_archive_png_references(archive: Path, output_directory: Path) -> None:
    """Write seven indexed PNG references from the sanitized archive."""
    with ZipFile(archive) as source_archive:
        zpl = source_archive.read(ARCHIVE_MEMBER)

    output_directory.mkdir(parents=True, exist_ok=True)
    for index in range(PAGE_COUNT):
        output = output_directory / f"page_{index + 1:02}.png"
        output.write_bytes(request_png(zpl, index))
        print(f"Wrote Labelary PNG reference to {output}")
        if index + 1 < PAGE_COUNT:
            time.sleep(0.4)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output-directory", type=Path, default=DEFAULT_OUTPUT_DIRECTORY)
    arguments = parser.parse_args()
    generate_archive_png_references(arguments.archive, arguments.output_directory)


if __name__ == "__main__":
    main()
