"""Code 128 and QR element encoding tests."""

from zplrender.commands.barcodes import encode_code128_modules
from zplrender.elements import Code128Element, QRCodeElement
from zplrender.parser import parse
from zplrender.renderers.base import RenderOptions
from zplrender.renderers.pillow import render_document


def test_encodes_explicit_code128_subset_b() -> None:
    modules = encode_code128_modules(">:123")

    assert modules.startswith("11010010000")
    assert modules.endswith("1100011101011")
    assert len(modules) == 68


def test_parses_shipping_label_barcode_options_and_prefixes() -> None:
    document = parse(
        "^XA"
        "^FO10,10^BY3,,0^BCN,160,N,N,N^FD>:12345678901^FS"
        '^FO10,200^BQN,2,5^FDLA,{"id":"12345678901"}^FS'
        "^XZ",
        strict=True,
    )

    code128, qr = document.pages[0].elements
    assert isinstance(code128, Code128Element)
    assert code128.module_width == 3
    assert code128.height == 160
    assert code128.interpretation_line is False
    assert isinstance(qr, QRCodeElement)
    assert qr.data == '{"id":"12345678901"}'
    assert qr.magnification == 5
    assert qr.error_correction == "M"
    assert qr.mask is None


def test_renders_barcode_pixels() -> None:
    document = parse(
        "^XA^FO10,10^BY2^BCN,40,N,N,N^FD>:123^FS"
        "^FO10,60^BQN,2,3^FDLA,test^FS^XZ",
        strict=True,
    )

    page = render_document(document, RenderOptions(width=250, height=180))[0].convert("L")

    assert page.getpixel((9, 10)) == 255
    assert page.getpixel((10, 10)) == 0
    assert page.crop((10, 10, 200, 50)).histogram()[0] > 0
    assert page.crop((10, 60, 150, 180)).histogram()[0] > 0
