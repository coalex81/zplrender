"""Graphic download decoding tests."""

import base64
import binascii
import zlib

import pytest

from zplrender.commands.graphics import (
    decode_download_graphic,
    decode_graphic_field,
    decode_z64,
    decode_zpl_ascii_compression,
)
from zplrender.exceptions import ZPLGraphicDecodeError


def _z64(data: bytes) -> str:
    payload = base64.b64encode(zlib.compress(data)).decode("ascii")
    crc = binascii.crc_hqx(payload.encode("ascii"), 0)
    return f":Z64:{payload}:{crc:04X}"


def test_decodes_z64_download_and_dimensions() -> None:
    name, graphic = decode_download_graphic(f"R:ONE.GRF,2,1,{_z64(bytes([0x80, 0x01]))}")

    assert name == "R:ONE.GRF"
    assert graphic.width == 8
    assert graphic.height == 2
    assert graphic.data == bytes([0x80, 0x01])


def test_rejects_z64_crc_mismatch() -> None:
    encoded = _z64(b"data")

    with pytest.raises(ZPLGraphicDecodeError, match="CRC mismatch"):
        decode_z64(f"{encoded[:-4]}0000")


def test_rejects_inconsistent_download_size() -> None:
    with pytest.raises(ZPLGraphicDecodeError, match="decoded 1 bytes, expected 2"):
        decode_download_graphic("R:ONE.GRF,2,1,80")


def test_decodes_ascii_repeat_counts_row_fills_and_row_repetition() -> None:
    decoded = decode_zpl_ascii_compression("H8,:!", bytes_per_row=1, rows=4)

    assert decoded == bytes([0x88, 0x00, 0x00, 0xFF])


def test_decodes_inline_graphic_metadata() -> None:
    graphic = decode_graphic_field("A,2,2,1,8001")

    assert (graphic.width, graphic.height) == (8, 2)
    assert graphic.data == bytes([0x80, 0x01])
