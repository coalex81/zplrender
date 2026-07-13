"""Native box and reverse-field rendering tests."""

from zplrender.parser import parse
from zplrender.renderers.base import RenderOptions
from zplrender.renderers.pillow import render_document


def test_draws_filled_box_with_reversed_text() -> None:
    document = parse(
        "^XA^FO10,10^GB100,40,40^FS^FO10,10^A0N,24,24^FR^FDOK^FS^XZ",
        strict=True,
    )

    page = render_document(document, RenderOptions(width=120, height=60))[0]

    assert page.getpixel((12, 12)) == 0
    assert page.crop((10, 10, 110, 50)).convert("L").histogram()[255] > 0


def test_draws_zero_height_horizontal_line() -> None:
    document = parse("^XA^FO5,10^GB50,0,3^FS^XZ", strict=True)

    page = render_document(document, RenderOptions(width=60, height=20))[0]

    assert page.getpixel((5, 10)) == 0
    assert page.getpixel((54, 12)) == 0


def test_reverse_text_inverts_white_background_to_black() -> None:
    document = parse("^XA^FO5,5^A0N,24,24^FR^FDVisible^FS^XZ", strict=True)

    page = render_document(document, RenderOptions(width=120, height=40))[0].convert("L")

    assert page.crop((5, 5, 100, 35)).histogram()[0] > 0
