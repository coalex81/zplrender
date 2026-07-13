"""Generate the visual benchmark reference with the Labelary API."""

from __future__ import annotations

import argparse
import urllib.error
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[1]
DEFAULT_SOURCE = PROJECT_ROOT / "tests" / "fixtures" / "zpl" / "shipping_label.zpl"
DEFAULT_OUTPUT = PROJECT_ROOT / "benchmarks" / "reference" / "shipping_label.png"
LABELARY_URL = "https://api.labelary.com/v1/printers/8dpmm/labels/4x6/0/"


def generate_reference(source: Path, output: Path) -> None:
    """Send sanitized ZPL to Labelary and store its PNG rendering."""
    request = urllib.request.Request(
        LABELARY_URL,
        data=source.read_bytes(),
        headers={
            "Accept": "image/png",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "zplrender-benchmark/0.1",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read()
            content_type = response.headers.get_content_type()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Labelary returned HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not reach Labelary: {error.reason}") from error

    if content_type != "image/png" or not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError(f"Labelary returned {content_type}, not a PNG image")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(content)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    generate_reference(arguments.source, arguments.output)
    print(f"Wrote Labelary reference to {arguments.output}")


if __name__ == "__main__":
    main()
