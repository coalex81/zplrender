"""Native text parsing and rendering tests."""

from zplrender.elements import TextElement
from zplrender.parser import parse
from zplrender.renderers.base import RenderOptions
from zplrender.renderers.pillow import render_document


def test_decodes_utf8_hex_and_applies_label_home() -> None:
    document = parse(
        "^XA^CI28^LH5,15^FO20,10^A0N,24,24^FH^FDS_C3_A3o Paulo^FS^XZ",
        strict=True,
    )

    element = document.pages[0].elements[0]
    assert isinstance(element, TextElement)
    assert (element.x, element.y) == (25, 25)
    assert element.text == "São Paulo"
    assert (element.height, element.width) == (24, 24)


def test_wraps_and_centers_field_block() -> None:
    document = parse(
        "^XA^FO10,10^A0N,20,20^FB100,2,0,C^FDalpha beta gamma^FS^XZ",
        strict=True,
    )

    pages = render_document(document, RenderOptions(width=200, height=100))

    assert len(pages) == 1
    assert pages[0].getbbox() == (0, 0, 200, 100)
