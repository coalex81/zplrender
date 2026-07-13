"""Generate native and seven-label PDF benchmark references with Labelary."""

from __future__ import annotations

import argparse
import urllib.error
import urllib.request
from pathlib import Path
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).parents[1]
DEFAULT_NATIVE_SOURCE = PROJECT_ROOT / "tests" / "fixtures" / "zpl" / "shipping_label.zpl"
DEFAULT_ARCHIVE = (
    PROJECT_ROOT / "tests" / "fixtures" / "archives" / "shopee_shipping_labels.zip"
)
DEFAULT_OUTPUT_DIRECTORY = PROJECT_ROOT / "benchmarks" / "reference"
ARCHIVE_MEMBER = "thermal_zpl_shipping_label.txt"
LABELARY_URL = "https://api.labelary.com/v1/printers/8dpmm/labels/4x6/"


def request_pdf(zpl: bytes) -> bytes:
    """Render a complete ZPL document as a single- or multi-page PDF."""
    request = urllib.request.Request(
        LABELARY_URL,
        data=zpl,
        headers={
            "Accept": "application/pdf",
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

    if content_type != "application/pdf" or not content.startswith(b"%PDF-"):
        raise RuntimeError(f"Labelary returned {content_type}, not a PDF")
    return content


def generate_pdf_references(native_source: Path, archive: Path, output_directory: Path) -> None:
    """Write the one-page native and seven-page archive PDF references."""
    with ZipFile(archive) as source_archive:
        archive_zpl = source_archive.read(ARCHIVE_MEMBER)

    references = {
        "shipping_label.pdf": native_source.read_bytes(),
        "shopee_shipping_labels.pdf": archive_zpl,
    }
    output_directory.mkdir(parents=True, exist_ok=True)
    for filename, zpl in references.items():
        output = output_directory / filename
        output.write_bytes(request_pdf(zpl))
        print(f"Wrote Labelary PDF reference to {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-source", type=Path, default=DEFAULT_NATIVE_SOURCE)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output-directory", type=Path, default=DEFAULT_OUTPUT_DIRECTORY)
    arguments = parser.parse_args()
    generate_pdf_references(
        arguments.native_source,
        arguments.archive,
        arguments.output_directory,
    )


if __name__ == "__main__":
    main()
