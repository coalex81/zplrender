"""Barcode encoding isolated from the Pillow page renderer."""

from barcode.charsets import code128  # type: ignore[import-untyped]

from zplrender.exceptions import ZPLRenderError


def encode_code128_modules(data: str) -> str:
    """Encode the supported Zebra Code 128 subset into one-bit modules.

    The first milestone supports the default/explicit Subset B form used by the
    legacy fixture. Other invocation codes fail explicitly rather than being
    silently interpreted as printable data.
    """
    if data.startswith(">:"):
        data = data[2:]
    elif data.startswith(">"):
        raise ZPLRenderError(f"Unsupported Code 128 invocation: {data[:2]}")

    values: list[int] = []
    for character in data:
        value = ord(character) - 32
        if not 0 <= value <= 94:
            raise ZPLRenderError(f"Character is not encodable in Code 128 Subset B: {character!r}")
        values.append(value)

    start = 104
    checksum = (start + sum(index * value for index, value in enumerate(values, 1))) % 103
    patterns = [code128.CODES[start]]
    patterns.extend(code128.CODES[value] for value in values)
    patterns.append(code128.CODES[checksum])
    patterns.extend((code128.STOP, "11"))
    return "".join(patterns)
