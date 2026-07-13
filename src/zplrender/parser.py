"""ZPL parsing and state-machine orchestration."""

from dataclasses import dataclass, field

from zplrender.commands.graphics import decode_download_graphic, decode_graphic_field
from zplrender.diagnostics import Diagnostic, Severity
from zplrender.document import LabelPage, ParsedDocument
from zplrender.elements import (
    BoxElement,
    Code128Element,
    FieldBlock,
    LabelElement,
    QRCodeElement,
    RasterElement,
    TextElement,
)
from zplrender.exceptions import ZPLError, ZPLSyntaxError
from zplrender.memory import GraphicMemory
from zplrender.tokenizer import Token, tokenize


@dataclass
class _Format:
    x: int = 0
    y: int = 0
    home_x: int = 0
    home_y: int = 0
    quantity: int = 1
    character_set: int = 0
    font: str = "0"
    font_height: int = 30
    font_width: int = 30
    font_orientation: str = "N"
    hex_indicator: str | None = None
    field_block: FieldBlock | None = None
    suppress_field_data: bool = False
    reverse: bool = False
    barcode_module_width: int = 2
    barcode_height: int = 10
    pending_barcode: tuple[str, str] | None = None
    elements: list[LabelElement] = field(default_factory=list)


_IGNORED_COMMANDS = {"^FX", "^MC", "^MM", "^MN", "^PO"}


def parse(source: str, *, strict: bool = False) -> ParsedDocument:
    """Interpret the stored-raster subset used by the legacy archive."""
    memory = GraphicMemory()
    current: _Format | None = None
    pages: list[LabelPage] = []
    diagnostics: list[Diagnostic] = []

    for token in tokenize(source):
        try:
            if token.command == "~DG":
                name, graphic = decode_download_graphic(token.data)
                memory.store(name, graphic)
            elif token.command == "^XA":
                if current is not None:
                    raise ZPLSyntaxError("Nested ^XA format start")
                current = _Format()
            elif token.command == "^XZ":
                if current is None:
                    raise ZPLSyntaxError("^XZ encountered outside a format")
                if current.elements:
                    page = LabelPage(elements=tuple(current.elements))
                    pages.extend(page for _ in range(current.quantity))
                current = None
            elif token.command == "^FO":
                format_state = _require_format(current, token)
                x, y = _parse_pair(token.data, token.command)
                format_state.x = format_state.home_x + x
                format_state.y = format_state.home_y + y
            elif token.command == "^LH":
                format_state = _require_format(current, token)
                format_state.home_x, format_state.home_y = _parse_pair(
                    token.data, token.command
                )
            elif token.command == "^CI":
                format_state = _require_format(current, token)
                format_state.character_set = _nonnegative_int(
                    token.data.split(",", maxsplit=1)[0] or "0", "^CI character set"
                )
            elif token.command == "^A0":
                _apply_font(_require_format(current, token), token.data)
            elif token.command == "^FH":
                format_state = _require_format(current, token)
                format_state.hex_indicator = token.data[:1] or "_"
            elif token.command == "^FB":
                format_state = _require_format(current, token)
                format_state.field_block = _parse_field_block(token.data)
            elif token.command == "^FD":
                format_state = _require_format(current, token)
                if format_state.pending_barcode is not None:
                    format_state.elements.append(_create_barcode(format_state, token.data))
                elif not format_state.suppress_field_data:
                    text = _decode_field_data(
                        token.data,
                        character_set=format_state.character_set,
                        hex_indicator=format_state.hex_indicator,
                    )
                    format_state.elements.append(
                        TextElement(
                            x=format_state.x,
                            y=format_state.y,
                            text=text,
                            font=format_state.font,
                            height=format_state.font_height,
                            width=format_state.font_width,
                            orientation=format_state.font_orientation,
                            block=format_state.field_block,
                            reverse=format_state.reverse,
                        )
                    )
            elif token.command == "^GB":
                format_state = _require_format(current, token)
                format_state.elements.append(_parse_box(format_state, token.data))
            elif token.command == "^FR":
                format_state = _require_format(current, token)
                format_state.reverse = True
            elif token.command == "^GF":
                format_state = _require_format(current, token)
                format_state.elements.append(
                    RasterElement(
                        x=format_state.x,
                        y=format_state.y,
                        graphic=decode_graphic_field(token.data),
                        reverse=format_state.reverse,
                    )
                )
            elif token.command == "^BY":
                format_state = _require_format(current, token)
                _apply_barcode_defaults(format_state, token.data)
            elif token.command in {"^BC", "^BQ"}:
                format_state = _require_format(current, token)
                format_state.pending_barcode = (token.command, token.data)
            elif token.command == "^FS":
                format_state = _require_format(current, token)
                format_state.hex_indicator = None
                format_state.field_block = None
                format_state.suppress_field_data = False
                format_state.reverse = False
                format_state.pending_barcode = None
            elif token.command == "^XG":
                format_state = _require_format(current, token)
                parts = token.data.split(",")
                name = parts[0]
                scale_x = _positive_int(parts[1], "^XG x magnification") if len(parts) > 1 else 1
                scale_y = _positive_int(parts[2], "^XG y magnification") if len(parts) > 2 else 1
                format_state.elements.append(
                    RasterElement(
                        x=format_state.x,
                        y=format_state.y,
                        graphic=memory.recall(name),
                        scale_x=scale_x,
                        scale_y=scale_y,
                    )
                )
            elif token.command == "^PQ":
                format_state = _require_format(current, token)
                quantity_text = token.data.split(",", maxsplit=1)[0]
                format_state.quantity = _positive_int(quantity_text or "1", "^PQ quantity")
            elif token.command == "^ID":
                _require_format(current, token)
                memory.delete(token.data)
            elif token.command in _IGNORED_COMMANDS:
                continue
            else:
                diagnostic = Diagnostic(
                    severity=Severity.WARNING,
                    code="ZPL001",
                    message=f"Unsupported command: {token.command}",
                    offset=token.offset,
                    command=token.command,
                )
                if strict:
                    raise ZPLSyntaxError(diagnostic.message)
                diagnostics.append(diagnostic)
        except ZPLError as error:
            if strict:
                raise
            diagnostics.append(
                Diagnostic(
                    severity=Severity.ERROR,
                    code="ZPL005" if token.command == "~DG" else "ZPL002",
                    message=str(error),
                    offset=token.offset,
                    command=token.command,
                )
            )

    if current is not None:
        missing_format_error = ZPLSyntaxError("Format is missing ^XZ")
        if strict:
            raise missing_format_error
        diagnostics.append(Diagnostic(Severity.ERROR, "ZPL004", str(missing_format_error)))

    return ParsedDocument(pages=tuple(pages), diagnostics=tuple(diagnostics))


def _require_format(current: _Format | None, token: Token) -> _Format:
    if current is None:
        raise ZPLSyntaxError(f"{token.command} encountered outside a format")
    return current


def _parse_pair(data: str, command: str) -> tuple[int, int]:
    parts = data.split(",")
    try:
        return int(parts[0] or "0"), int(parts[1] or "0") if len(parts) > 1 else 0
    except ValueError as error:
        raise ZPLSyntaxError(f"{command} coordinates must be integers") from error


def _positive_int(value: str, description: str) -> int:
    try:
        result = int(value)
    except ValueError as error:
        raise ZPLSyntaxError(f"{description} must be an integer") from error
    if result < 1:
        raise ZPLSyntaxError(f"{description} must be positive")
    return result


def _nonnegative_int(value: str, description: str) -> int:
    try:
        result = int(value)
    except ValueError as error:
        raise ZPLSyntaxError(f"{description} must be an integer") from error
    if result < 0:
        raise ZPLSyntaxError(f"{description} cannot be negative")
    return result


def _apply_font(format_state: _Format, data: str) -> None:
    parts = data.split(",")
    orientation = (parts[0] or "N").upper()
    if orientation != "N":
        raise ZPLSyntaxError(f"Unsupported ^A0 orientation: {orientation}")
    format_state.font = "0"
    format_state.font_orientation = orientation
    if len(parts) > 1 and parts[1]:
        format_state.font_height = _positive_int(parts[1], "^A0 height")
    if len(parts) > 2 and parts[2]:
        format_state.font_width = _positive_int(parts[2], "^A0 width")
    elif len(parts) > 1 and parts[1]:
        format_state.font_width = format_state.font_height


def _parse_field_block(data: str) -> FieldBlock:
    parts = data.split(",")
    width = _positive_int(parts[0], "^FB width")
    max_lines = (
        _positive_int(parts[1], "^FB maximum lines") if len(parts) > 1 and parts[1] else 1
    )
    line_spacing = int(parts[2]) if len(parts) > 2 and parts[2] else 0
    alignment = (parts[3] if len(parts) > 3 and parts[3] else "L").upper()
    if alignment not in {"L", "C", "R", "J"}:
        raise ZPLSyntaxError(f"Unsupported ^FB alignment: {alignment}")
    hanging_indent = (
        _nonnegative_int(parts[4], "^FB hanging indent")
        if len(parts) > 4 and parts[4]
        else 0
    )
    return FieldBlock(width, max_lines, line_spacing, alignment, hanging_indent)


def _decode_field_data(data: str, *, character_set: int, hex_indicator: str | None) -> str:
    if hex_indicator is None:
        return data

    decoded = bytearray()
    position = 0
    while position < len(data):
        if (
            data[position] == hex_indicator
            and position + 2 < len(data)
            and all(
                character in "0123456789abcdefABCDEF"
                for character in data[position + 1 : position + 3]
            )
        ):
            decoded.append(int(data[position + 1 : position + 3], 16))
            position += 3
        else:
            decoded.extend(data[position].encode("utf-8"))
            position += 1

    encoding = "utf-8" if character_set == 28 else "latin-1"
    try:
        return decoded.decode(encoding)
    except UnicodeDecodeError as error:
        raise ZPLSyntaxError(f"Invalid {encoding} field data") from error


def _parse_box(format_state: _Format, data: str) -> BoxElement:
    parts = data.split(",")
    width = _nonnegative_int(parts[0] or "0", "^GB width")
    height = _nonnegative_int(parts[1] or "0", "^GB height") if len(parts) > 1 else 0
    thickness = _positive_int(parts[2], "^GB thickness") if len(parts) > 2 and parts[2] else 1
    color = (parts[3] if len(parts) > 3 and parts[3] else "B").upper()
    rounding = _nonnegative_int(parts[4], "^GB rounding") if len(parts) > 4 and parts[4] else 0
    if color not in {"B", "W"}:
        raise ZPLSyntaxError(f"Unsupported ^GB color: {color}")
    if rounding > 8:
        raise ZPLSyntaxError("^GB rounding must be between 0 and 8")
    return BoxElement(
        x=format_state.x,
        y=format_state.y,
        width=width,
        height=height,
        thickness=thickness,
        color=color,
        rounding=rounding,
        reverse=format_state.reverse,
    )


def _apply_barcode_defaults(format_state: _Format, data: str) -> None:
    parts = data.split(",")
    if parts[0]:
        format_state.barcode_module_width = _positive_int(parts[0], "^BY module width")
    if len(parts) > 2 and parts[2]:
        format_state.barcode_height = _nonnegative_int(parts[2], "^BY height")


def _create_barcode(format_state: _Format, data: str) -> Code128Element | QRCodeElement:
    assert format_state.pending_barcode is not None
    command, parameters = format_state.pending_barcode
    parts = parameters.split(",")
    orientation = (parts[0] or "N").upper()
    if orientation != "N":
        raise ZPLSyntaxError(f"Unsupported {command} orientation: {orientation}")

    if command == "^BC":
        height = (
            _positive_int(parts[1], "^BC height")
            if len(parts) > 1 and parts[1]
            else format_state.barcode_height
        )
        interpretation = not (len(parts) > 2 and parts[2].upper() == "N")
        above = len(parts) > 3 and parts[3].upper() == "Y"
        return Code128Element(
            x=format_state.x,
            y=format_state.y,
            data=data,
            height=height,
            module_width=format_state.barcode_module_width,
            interpretation_line=interpretation,
            interpretation_above=above,
            reverse=format_state.reverse,
        )

    model = _positive_int(parts[1], "^BQ model") if len(parts) > 1 and parts[1] else 2
    if model != 2:
        raise ZPLSyntaxError("Only QR Code Model 2 is supported")
    magnification = (
        _positive_int(parts[2], "^BQ magnification") if len(parts) > 2 and parts[2] else 2
    )
    error_correction = (parts[3] if len(parts) > 3 and parts[3] else "Q").upper()
    if error_correction not in {"H", "Q", "M", "L"}:
        raise ZPLSyntaxError(f"Unsupported ^BQ error correction: {error_correction}")
    mask: int | None = int(parts[4]) if len(parts) > 4 and parts[4] else 7
    qr_data = data
    if len(data) >= 3 and data[0] in "HQML" and data[1:3] == "A,":
        # The legacy Zebra-compatible reference uses automatic segmentation,
        # standard M correction, and automatic mask selection for ``LA,``.
        # Keep this isolated so broader firmware variants can be added later.
        error_correction = "M"
        mask = None
        qr_data = data[3:]
    return QRCodeElement(
        x=format_state.x,
        y=format_state.y,
        data=qr_data,
        magnification=magnification,
        error_correction=error_correction,
        mask=mask,
        reverse=format_state.reverse,
    )
