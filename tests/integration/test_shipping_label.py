"""Integration and visual-regression coverage for the sanitized shipping label."""

import hashlib
from pathlib import Path

from PIL import Image

from zplrender import ZPLDocument, render, render_pdf
from zplrender.cli import read_zpl_input
from zplrender.elements import TextElement


PROJECT_ROOT = Path(__file__).parents[2]
LABEL = PROJECT_ROOT / "tests" / "fixtures" / "zpl" / "shipping_label.zpl"
REFERENCE = PROJECT_ROOT / "benchmarks" / "reference" / "shipping_label.png"
ARCHIVE = PROJECT_ROOT / "tests" / "fixtures" / "archives" / "shopee_shipping_labels.zip"
ARCHIVE_REFERENCES = PROJECT_ROOT / "benchmarks" / "reference" / "shopee_shipping_labels"


def _shipping_label_source() -> str:
    return LABEL.read_text(encoding="utf-8")


def _pixel_is_black(image: Image.Image, position: tuple[int, int]) -> bool:
    pixel = image.getpixel(position)
    if not isinstance(pixel, (int, float)):
        raise TypeError(f"Expected a grayscale pixel, got {pixel!r}")
    return pixel < 128


def _difference_percentage(actual: Image.Image, reference: Image.Image) -> float:
    differing = sum(
        (actual_pixel < 128) != (reference_pixel < 128)
        for actual_pixel, reference_pixel in zip(actual.tobytes(), reference.tobytes())
    )
    return differing * 100 / (actual.width * actual.height)


def test_renders_sanitized_shipping_label() -> None:
    result = render(_shipping_label_source(), strict=True)

    assert len(result.pages) == 1
    assert result.diagnostics == ()
    assert {page.size for page in result.pages} == {(812, 1218)}
    assert all(page.getbbox() == (0, 0, 812, 1218) for page in result.pages)


def test_writes_shipping_label_pdf(tmp_path: Path) -> None:
    output = tmp_path / "label.pdf"

    result = render_pdf(_shipping_label_source(), output, strict=True)

    assert len(result.pages) == 1
    assert output.read_bytes().startswith(b"%PDF-")
    assert output.stat().st_size > 5_000


def test_renders_seven_sanitized_raster_labels_from_shopee_zip() -> None:
    source = read_zpl_input(ARCHIVE)
    result = render(source, strict=True)

    assert source.count("~DGR:LABEL") == 7
    assert source.count("^XGR:LABEL") == 7
    assert source.count("^IDR:LABEL") == 7
    assert len(result.pages) == 7
    assert result.diagnostics == ()
    assert {page.size for page in result.pages} == {(812, 1218)}
    assert all(page.getbbox() == (0, 0, 812, 1218) for page in result.pages)


def test_shopee_zip_pages_match_labelary_png_references() -> None:
    pages = render(read_zpl_input(ARCHIVE), strict=True).pages
    references = sorted(ARCHIVE_REFERENCES.glob("page_*.png"))

    assert len(pages) == len(references) == 7
    for page, reference_path in zip(pages, references):
        actual = page.convert("L")
        with Image.open(reference_path) as reference_image:
            reference = reference_image.convert("L")
        assert actual.size == reference.size == (812, 1218)
        differing = sum(
            (actual_pixel < 128) != (reference_pixel < 128)
            for actual_pixel, reference_pixel in zip(actual.tobytes(), reference.tobytes())
        )
        assert differing == 0


def test_native_label_renders_text_with_utf8_escapes() -> None:
    document = ZPLDocument.parse(_shipping_label_source())
    result = document.render()

    texts = [
        element.text
        for element in document.parsed.pages[0].elements
        if isinstance(element, TextElement)
    ]
    assert len(result.pages) == 1
    assert result.pages[0].size == (812, 1218)
    assert result.pages[0].getbbox() == (0, 0, 812, 1218)
    joined_text = " ".join(texts)
    assert "John Doe" in joined_text
    assert "Avenida Paulista" in joined_text
    assert "São Paulo" in joined_text
    unsupported = {diagnostic.command for diagnostic in result.diagnostics}
    assert "^GF" not in unsupported
    assert "^GB" not in unsupported
    assert "^FR" not in unsupported
    assert "^BY" not in unsupported
    assert "^BC" not in unsupported
    assert "^BQ" not in unsupported


def test_native_label_visual_regressions_for_reverse_text_and_qr_gap() -> None:
    page = render(_shipping_label_source(), strict=True).pages[0].convert("L")

    route_box = page.crop((20, 570, 160, 710))
    assert route_box.crop((70, 0, 140, 140)).histogram()[255] > 500
    assert page.crop((165, 585, 200, 725)).histogram()[0] == 0

    dispatch_text = page.crop((325, 160, 785, 195))
    assert dispatch_text.histogram()[0] > 500

    qr_gap = page.crop((655, 1125, 780, 1145))
    assert qr_gap.histogram()[0] == 0

    qr_bits = "".join(
        "1" if _pixel_is_black(page, (655 + column * 5 + 2, 1000 + row * 5 + 2)) else "0"
        for row in range(25)
        for column in range(25)
    )
    assert hashlib.sha256(qr_bits.encode()).hexdigest() == (
        "6acbb08ec3712421b4b427a3c972e1484727a30ea6e18e0ed92afbe230bf1d11"
    )


def test_visual_difference_from_labelary_stays_below_baseline() -> None:
    actual = render(_shipping_label_source(), strict=True).pages[0].convert("L")
    with Image.open(REFERENCE) as reference_image:
        reference = reference_image.convert("L")

    assert actual.size == reference.size
    assert _difference_percentage(actual, reference) < 8.0


def test_visual_regions_preserve_barcode_origin_improvement() -> None:
    actual = render(_shipping_label_source(), strict=True).pages[0].convert("L")
    with Image.open(REFERENCE) as reference_image:
        reference = reference_image.convert("L")
    regions = {
        "header": (0, 0, 812, 210),
        "barcode": (0, 210, 812, 450),
        "routing": (0, 450, 812, 780),
        "routing_details": (0, 780, 812, 950),
        "recipient": (0, 950, 650, 1218),
        "qr": (650, 950, 812, 1218),
    }
    differences = {
        name: _difference_percentage(actual.crop(box), reference.crop(box))
        for name, box in regions.items()
    }

    assert max(differences, key=differences.__getitem__) == "routing"
    assert differences["barcode"] < 1.5
    assert differences["routing"] > differences["recipient"]
    assert differences["qr"] < 5.0
