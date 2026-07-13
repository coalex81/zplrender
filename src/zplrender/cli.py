"""Command-line entry point."""

import argparse
import sys
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from zplrender.api import render_pdf
from zplrender.exceptions import ZPLError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render ZPL text or a ZIP archive to PDF offline.")
    parser.add_argument("input", type=Path, help="ZPL text file or ZIP archive")
    parser.add_argument("--output", "-o", type=Path, help="PDF output path")
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace the output file if it already exists",
    )
    parser.add_argument("--dpi", type=int, default=203)
    parser.add_argument("--width", type=int, default=812, help="Page width in dots")
    parser.add_argument("--height", type=int, default=1218, help="Page height in dots")
    parser.add_argument("--strict", action="store_true")
    return parser


def read_zpl_input(input_path: Path) -> str:
    """Read ZPL from a plain text file or concatenate ZPL members from a ZIP."""
    if input_path.suffix.lower() == ".pdf":
        raise ValueError("PDF files are outputs; provide a ZPL text file or ZIP archive")
    if input_path.suffix.lower() == ".zip":
        return _read_zip(input_path)

    try:
        source = input_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError(f"Input is not a UTF-8 ZPL text file: {input_path}") from error
    if not _contains_zpl(source):
        raise ValueError(f"No complete ZPL format found in: {input_path}")
    return source


def _read_zip(input_path: Path) -> str:
    documents: list[str] = []
    try:
        with ZipFile(input_path) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                try:
                    source = archive.read(member).decode("utf-8-sig")
                except UnicodeDecodeError:
                    continue
                if _contains_zpl(source):
                    documents.append(source)
    except BadZipFile as error:
        raise ValueError(f"Invalid ZIP archive: {input_path}") from error

    if not documents:
        raise ValueError(f"No ZPL documents found in ZIP archive: {input_path}")
    return "\n".join(documents)


def _contains_zpl(source: str) -> bool:
    normalized = source.upper()
    return "^XA" in normalized and "^XZ" in normalized


def main() -> int:
    """Run the command-line application."""
    arguments = _build_parser().parse_args()
    output = arguments.output or arguments.input.with_suffix(".pdf")
    try:
        if (
            arguments.input.suffix.lower() != ".pdf"
            and output.exists()
            and not arguments.force
        ):
            raise FileExistsError(
                f"Output file already exists: {output} (use --force to replace it)"
            )
        source = read_zpl_input(arguments.input)
        result = render_pdf(
            source,
            output,
            dpi=arguments.dpi,
            width=arguments.width,
            height=arguments.height,
            strict=arguments.strict,
        )
    except (OSError, ValueError, ZPLError) as error:
        print(f"zplrender: error: {error}", file=sys.stderr)
        return 2

    for diagnostic in result.diagnostics:
        print(f"{diagnostic.severity.value}: {diagnostic.code}: {diagnostic.message}")
    print(f"Rendered {len(result.pages)} page(s) to {output}")
    return 0
