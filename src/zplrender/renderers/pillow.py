"""Pillow raster rendering backend."""

from PIL import Image, ImageDraw, ImageFont, ImageOps
import qrcode  # type: ignore[import-untyped]
from qrcode import constants as qr_constants

from zplrender.commands.barcodes import encode_code128_modules
from zplrender.document import LabelPage, ParsedDocument
from zplrender.elements import (
    BoxElement,
    Code128Element,
    FieldBlock,
    QRCodeElement,
    RasterElement,
    RasterGraphic,
    TextElement,
)
from zplrender.fonts import DEFAULT_FONT_REGISTRY
from zplrender.renderers.base import RenderOptions


def render_document(document: ParsedDocument, options: RenderOptions) -> tuple[Image.Image, ...]:
    """Render all printable pages to one-bit Pillow images."""
    return tuple(render_page(page, options) for page in document.pages)


def render_page(page: LabelPage, options: RenderOptions) -> Image.Image:
    """Render one label page with clipping at its configured boundaries."""
    canvas = Image.new("1", (options.width, options.height), color=1)
    for element in page.elements:
        if isinstance(element, RasterElement):
            _paste_raster(canvas, element)
        elif isinstance(element, TextElement):
            _draw_text(canvas, element)
        elif isinstance(element, BoxElement):
            _draw_box(canvas, element)
        elif isinstance(element, Code128Element):
            _draw_code128(canvas, element)
        elif isinstance(element, QRCodeElement):
            _draw_qr(canvas, element)
    return canvas


def _paste_raster(canvas: Image.Image, element: RasterElement) -> None:
    image = _graphic_to_image(element.graphic)
    if element.reverse:
        image = ImageOps.invert(image.convert("L")).convert("1")
    if element.scale_x != 1 or element.scale_y != 1:
        image = image.resize(
            (image.width * element.scale_x, image.height * element.scale_y),
            resample=Image.Resampling.NEAREST,
        )
    canvas.paste(image, (element.x, element.y))


def _graphic_to_image(graphic: RasterGraphic) -> Image.Image:
    # Pillow mode 1 treats set bits as white; ZPL treats set bits as black.
    image = Image.frombytes("1", (graphic.width, graphic.height), graphic.data)
    return ImageOps.invert(image.convert("L")).convert("1")


def _draw_text(canvas: Image.Image, element: TextElement) -> None:
    font = DEFAULT_FONT_REGISTRY.load(element.font, element.height)
    horizontal_scale = element.width / element.height
    lines = _layout_lines(element.text, font, element.block, horizontal_scale)
    draw = ImageDraw.Draw(canvas)
    line_height = element.height + (element.block.line_spacing if element.block else 0)

    for index, line in enumerate(lines):
        x = element.x
        line_width = element.block.width if element.block is not None else 0
        if element.block is not None:
            text_width = _text_width(line, font, horizontal_scale)
            block_x = element.x
            block_width = element.block.width
            if element.reverse:
                black_run = _contiguous_black_run(
                    canvas, element.x, element.y + index * line_height
                )
                if black_run is not None:
                    block_x, run_end = black_run
                    block_width = run_end - block_x
            indent = element.block.hanging_indent if index > 0 else 0
            line_width = max(0, block_width - indent)
            line_x = block_x + min(indent, block_width)
            if element.block.alignment == "C":
                x = line_x + max(0, (line_width - text_width) // 2)
            elif element.block.alignment == "R":
                x = line_x + max(0, line_width - text_width)
            else:
                x = line_x
        position = (x, element.y + index * line_height)
        if (
            element.block is not None
            and element.block.alignment == "J"
            and index < len(lines) - 1
            and " " in line
        ):
            _draw_justified_text(
                canvas,
                position,
                line,
                font,
                horizontal_scale,
                line_width,
                reverse=element.reverse,
            )
        else:
            _draw_text_at(
                canvas,
                draw,
                position,
                line,
                font,
                horizontal_scale,
                reverse=element.reverse,
            )


def _draw_text_at(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    horizontal_scale: float,
    *,
    reverse: bool,
) -> None:
    if reverse:
        _invert_text(canvas, position, text, font, horizontal_scale)
    elif horizontal_scale != 1:
        _draw_scaled_text(canvas, position, text, font, horizontal_scale, reverse=False)
    else:
        draw.text(position, text, font=font, fill=0, spacing=0)


def _draw_justified_text(
    canvas: Image.Image,
    position: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    horizontal_scale: float,
    width: int,
    *,
    reverse: bool,
) -> None:
    words = text.split()
    word_widths = [_text_width(word, font, horizontal_scale) for word in words]
    gap = max(0.0, (width - sum(word_widths)) / (len(words) - 1))
    draw = ImageDraw.Draw(canvas)
    x = float(position[0])
    for word, word_width in zip(words, word_widths):
        _draw_text_at(
            canvas,
            draw,
            (round(x), position[1]),
            word,
            font,
            horizontal_scale,
            reverse=reverse,
        )
        x += word_width + gap


def _invert_text(
    canvas: Image.Image,
    position: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    horizontal_scale: float,
) -> None:
    if horizontal_scale != 1:
        _draw_scaled_text(canvas, position, text, font, horizontal_scale, reverse=True)
        return
    mask = Image.new("L", canvas.size, color=0)
    ImageDraw.Draw(mask).text(position, text, font=font, fill=255, spacing=0)
    grayscale = canvas.convert("L")
    inverted = ImageOps.invert(grayscale)
    grayscale.paste(inverted, (0, 0), mask)
    canvas.paste(grayscale.convert("1"))


def _draw_scaled_text(
    canvas: Image.Image,
    position: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    horizontal_scale: float,
    *,
    reverse: bool,
) -> None:
    left, _top, right, bottom = font.getbbox(text)
    local_left = min(0, left)
    mask = Image.new(
        "L",
        (max(1, round(right - local_left)), max(1, round(bottom))),
        color=0,
    )
    ImageDraw.Draw(mask).text((-local_left, 0), text, font=font, fill=255, spacing=0)
    mask = mask.resize(
        (max(1, round(mask.width * horizontal_scale)), mask.height),
        resample=Image.Resampling.NEAREST,
    )
    x = position[0] + round(local_left * horizontal_scale)
    if reverse:
        target = canvas.crop((x, position[1], x + mask.width, position[1] + mask.height))
        inverted = ImageOps.invert(target.convert("L"))
        canvas.paste(inverted.convert("1"), (x, position[1]), mask)
    else:
        ink = Image.new("1", mask.size, color=0)
        canvas.paste(ink, (x, position[1]), mask)


def _contiguous_black_run(canvas: Image.Image, x: int, y: int) -> tuple[int, int] | None:
    if not (0 <= x < canvas.width and 0 <= y < canvas.height):
        return None
    if canvas.getpixel((x, y)) != 0:
        return None

    start = x
    while start > 0 and canvas.getpixel((start - 1, y)) == 0:
        start -= 1
    end = x + 1
    while end < canvas.width and canvas.getpixel((end, y)) == 0:
        end += 1
    return start, end


def _layout_lines(
    text: str,
    font: ImageFont.FreeTypeFont,
    block: FieldBlock | None,
    horizontal_scale: float,
) -> list[str]:
    if block is None:
        return [text]

    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        indent = block.hanging_indent if lines else 0
        available_width = max(1, block.width - indent)
        if _text_width(candidate, font, horizontal_scale) <= available_width:
            current = candidate
        else:
            lines.append(current)
            current = word
            if len(lines) >= block.max_lines:
                return lines
    lines.append(current)
    return lines[: block.max_lines]


def _text_width(text: str, font: ImageFont.FreeTypeFont, horizontal_scale: float) -> int:
    left, _top, right, _bottom = font.getbbox(text)
    return round((right - left) * horizontal_scale)


def _draw_box(canvas: Image.Image, element: BoxElement) -> None:
    draw = ImageDraw.Draw(canvas)
    width = element.width or element.thickness
    height = element.height or element.thickness
    coordinates = (element.x, element.y, element.x + width - 1, element.y + height - 1)
    color = 1 if element.color == "W" or element.reverse else 0
    radius = round(min(width, height) * element.rounding / 16)
    if radius:
        draw.rounded_rectangle(
            coordinates,
            radius=radius,
            outline=color,
            width=min(element.thickness, width, height),
        )
    else:
        draw.rectangle(
            coordinates,
            outline=color,
            width=min(element.thickness, width, height),
        )


def _draw_code128(canvas: Image.Image, element: Code128Element) -> None:
    modules = encode_code128_modules(element.data)
    width = len(modules) * element.module_width
    barcode = Image.new("1", (width, element.height), color=1)
    draw = ImageDraw.Draw(barcode)
    x = 0
    for module in modules:
        if module == "1":
            draw.rectangle(
                (x, 0, x + element.module_width - 1, element.height - 1),
                fill=0,
            )
        x += element.module_width
    if element.reverse:
        barcode = ImageOps.invert(barcode.convert("L")).convert("1")
    canvas.paste(barcode, (element.x, element.y))


def _draw_qr(canvas: Image.Image, element: QRCodeElement) -> None:
    correction = {
        "L": qr_constants.ERROR_CORRECT_L,
        "M": qr_constants.ERROR_CORRECT_M,
        "Q": qr_constants.ERROR_CORRECT_Q,
        "H": qr_constants.ERROR_CORRECT_H,
    }[element.error_correction]
    code = qrcode.QRCode(
        version=None,
        error_correction=correction,
        box_size=element.magnification,
        border=0,
        mask_pattern=element.mask,
    )
    code.add_data(element.data, optimize=2)
    code.make(fit=True)
    image = code.make_image(fill_color="black", back_color="white").convert("1")
    if element.reverse:
        image = ImageOps.invert(image.convert("L")).convert("1")
    canvas.paste(image, (element.x, element.y))
