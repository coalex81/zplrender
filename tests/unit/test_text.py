"""Native text parsing and rendering tests."""

from zplrender.elements import FieldBlock, TextElement
from zplrender.fonts import DEFAULT_FONT_REGISTRY
from zplrender.parser import parse
from zplrender.renderers.base import RenderOptions
from zplrender.renderers.pillow import _layout_lines, render_document


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


def test_hanging_indent_reduces_width_of_wrapped_lines() -> None:
    font = DEFAULT_FONT_REGISTRY.load("0", 40)
    block = FieldBlock(width=350, max_lines=3, line_spacing=5, hanging_indent=60)

    lines = _layout_lines(
        "HANGING INDENT WRAPS SECOND AND THIRD LINES",
        font,
        block,
        horizontal_scale=1.0,
    )

    assert lines == ["HANGING INDENT", "WRAPS SECOND", "AND THIRD"]


def test_justified_field_wraps_before_expanding_word_spacing() -> None:
    font = DEFAULT_FONT_REGISTRY.load("0", 40)
    block = FieldBlock(width=650, max_lines=2, line_spacing=5, alignment="J")

    lines = _layout_lines(
        "JUSTIFIED WORDS EXPAND TO BOTH EDGES ON A WRAPPED LINE",
        font,
        block,
        horizontal_scale=1.0,
    )

    assert lines == ["JUSTIFIED WORDS EXPAND TO BOTH", "EDGES ON A WRAPPED LINE"]
