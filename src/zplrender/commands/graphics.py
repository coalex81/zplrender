"""Raster graphic and object-memory commands."""

import base64
import binascii
import zlib

from zplrender.elements import RasterGraphic
from zplrender.exceptions import ZPLGraphicDecodeError


def decode_download_graphic(data: str) -> tuple[str, RasterGraphic]:
    """Decode the parameter body of a ``~DG`` command."""
    parts = data.split(",", maxsplit=3)
    if len(parts) != 4:
        raise ZPLGraphicDecodeError("~DG requires name, total bytes, bytes per row, and data")

    name, total_text, row_text, encoded = parts
    try:
        total_bytes = int(total_text)
        bytes_per_row = int(row_text)
    except ValueError as error:
        raise ZPLGraphicDecodeError("~DG byte counts must be integers") from error

    if total_bytes <= 0 or bytes_per_row <= 0 or total_bytes % bytes_per_row:
        raise ZPLGraphicDecodeError("~DG dimensions are inconsistent")

    bitmap = decode_z64(encoded) if encoded.startswith(":Z64:") else decode_ascii_hex(encoded)
    if len(bitmap) != total_bytes:
        raise ZPLGraphicDecodeError(
            f"~DG decoded {len(bitmap)} bytes, expected {total_bytes}"
        )

    return name, RasterGraphic(
        width=bytes_per_row * 8,
        height=total_bytes // bytes_per_row,
        bytes_per_row=bytes_per_row,
        data=bitmap,
    )


def decode_z64(encoded: str) -> bytes:
    """Decode and validate a Zebra Z64 envelope."""
    parts = encoded.split(":")
    if len(parts) != 4 or parts[0] or parts[1].upper() != "Z64":
        raise ZPLGraphicDecodeError("Invalid Z64 envelope")

    payload, expected_crc = parts[2], parts[3].upper()
    actual_crc = f"{binascii.crc_hqx(payload.encode('ascii'), 0):04X}"
    if actual_crc != expected_crc:
        raise ZPLGraphicDecodeError(
            f"Z64 CRC mismatch: received {expected_crc}, calculated {actual_crc}"
        )

    try:
        return zlib.decompress(base64.b64decode(payload, validate=True))
    except (ValueError, binascii.Error, zlib.error) as error:
        raise ZPLGraphicDecodeError("Invalid Z64 compressed data") from error


def decode_ascii_hex(encoded: str) -> bytes:
    """Decode uncompressed ASCII hexadecimal graphic data."""
    compact = "".join(encoded.split())
    try:
        return bytes.fromhex(compact)
    except ValueError as error:
        raise ZPLGraphicDecodeError("Invalid ~DG ASCII hexadecimal data") from error


def decode_graphic_field(data: str) -> RasterGraphic:
    """Decode an ASCII ``^GF`` field, including Zebra run-length compression."""
    parts = data.split(",", maxsplit=4)
    if len(parts) != 5:
        raise ZPLGraphicDecodeError("^GF requires compression, counts, row width, and data")
    compression, _transmitted, total_text, row_text, encoded = parts
    if (compression or "A").upper() != "A":
        raise ZPLGraphicDecodeError(f"Unsupported ^GF compression type: {compression}")
    try:
        total_bytes = int(total_text)
        bytes_per_row = int(row_text)
    except ValueError as error:
        raise ZPLGraphicDecodeError("^GF byte counts must be integers") from error
    if total_bytes <= 0 or bytes_per_row <= 0 or total_bytes % bytes_per_row:
        raise ZPLGraphicDecodeError("^GF dimensions are inconsistent")

    bitmap = decode_zpl_ascii_compression(
        encoded, bytes_per_row=bytes_per_row, rows=total_bytes // bytes_per_row
    )
    return RasterGraphic(
        width=bytes_per_row * 8,
        height=total_bytes // bytes_per_row,
        bytes_per_row=bytes_per_row,
        data=bitmap,
    )


def decode_zpl_ascii_compression(encoded: str, *, bytes_per_row: int, rows: int) -> bytes:
    """Expand Zebra's ASCII hexadecimal repeat and row shorthand."""
    nibbles_per_row = bytes_per_row * 2
    decoded_rows: list[str] = []
    current = ""
    repeat = 0

    def finish_row(fill: str = "0") -> None:
        nonlocal current
        if len(current) > nibbles_per_row:
            raise ZPLGraphicDecodeError("^GF row exceeds declared width")
        decoded_rows.append(current.ljust(nibbles_per_row, fill))
        current = ""

    for character in encoded:
        if character in "\r\n \t":
            continue
        if character == ":":
            if current:
                finish_row()
            if not decoded_rows:
                raise ZPLGraphicDecodeError("^GF row repetition has no previous row")
            decoded_rows.append(decoded_rows[-1])
        elif character == ",":
            finish_row("0")
        elif character == "!":
            finish_row("F")
        elif character in "GHIJKLMNOPQRSTUVWXY":
            repeat += ord(character) - ord("G") + 1
        elif character in "ghijklmnopqrstuvwxyz":
            repeat += (ord(character) - ord("g") + 1) * 20
        elif character in "0123456789ABCDEFabcdef":
            current += character.upper() * (repeat or 1)
            repeat = 0
            if len(current) == nibbles_per_row:
                finish_row()
            elif len(current) > nibbles_per_row:
                raise ZPLGraphicDecodeError("^GF repeat count exceeds row width")
        else:
            raise ZPLGraphicDecodeError(f"Invalid ^GF compression character: {character!r}")

    if repeat:
        raise ZPLGraphicDecodeError("^GF repeat count is missing a hexadecimal value")
    if current:
        finish_row()
    if len(decoded_rows) != rows:
        raise ZPLGraphicDecodeError(
            f"^GF decoded {len(decoded_rows)} rows, expected {rows}"
        )
    return bytes.fromhex("".join(decoded_rows))
