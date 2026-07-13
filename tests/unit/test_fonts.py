"""Printer-font registry and independent width-scaling tests."""

from PIL import ImageOps

from zplrender.fonts import DEFAULT_FONT_REGISTRY
from zplrender.parser import parse
from zplrender.renderers.base import RenderOptions
from zplrender.renderers.pillow import render_document


def test_calibrates_font_zero_height() -> None:
    font = DEFAULT_FONT_REGISTRY.load("0", 100)

    assert font.size == 103


def test_scales_font_zero_width_independently_from_height() -> None:
    normal = parse("^XA^FO10,10^A0N,40,40^FDTEST^FS^XZ", strict=True)
    wide = parse("^XA^FO10,10^A0N,40,80^FDTEST^FS^XZ", strict=True)
    options = RenderOptions(width=400, height=100)

    normal_page = render_document(normal, options)[0]
    wide_page = render_document(wide, options)[0]
    normal_box = ImageOps.invert(normal_page.convert("L")).getbbox()
    wide_box = ImageOps.invert(wide_page.convert("L")).getbbox()

    assert normal_box is not None
    assert wide_box is not None
    normal_width = normal_box[2] - normal_box[0]
    wide_width = wide_box[2] - wide_box[0]
    assert wide_width >= normal_width * 1.9
