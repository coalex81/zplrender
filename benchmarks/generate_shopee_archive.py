"""Generate the sanitized seven-label Shopee-style ZIP fixture via Labelary."""

from __future__ import annotations

import base64
import binascii
import io
import time
import urllib.error
import urllib.request
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).parents[1]
SOURCE = PROJECT_ROOT / "tests" / "fixtures" / "zpl" / "shipping_label.zpl"
OUTPUT = PROJECT_ROOT / "tests" / "fixtures" / "archives" / "shopee_shipping_labels.zip"
LABELARY_URL = "https://api.labelary.com/v1/printers/8dpmm/labels/4x6/0/"
MEMBER_NAME = "thermal_zpl_shipping_label.txt"


@dataclass(frozen=True)
class Recipient:
    name: str
    address: str
    postal_code: str
    destination: str
    details: str
    shipment_id: str


RECIPIENTS = (
    Recipient(
        "John Doe",
        "Avenida Paulista 1578, Bela Vista",
        "01310200",
        "Sao Paulo, SP",
        "MASP public entrance",
        "12345678901",
    ),
    Recipient(
        "Jane Doe",
        "Praca da Se s/n, Se",
        "01001000",
        "Sao Paulo, SP",
        "Se Cathedral public square",
        "12345678902",
    ),
    Recipient(
        "Alex Smith",
        "Avenida Pedro Alvares Cabral s/n",
        "04094050",
        "Sao Paulo, SP",
        "Ibirapuera Park public entrance",
        "12345678903",
    ),
    Recipient(
        "Jamie Smith",
        "Praca Maua 1, Centro",
        "20081240",
        "Rio de Janeiro, RJ",
        "Museum of Tomorrow public entrance",
        "12345678904",
    ),
    Recipient(
        "Taylor Brown",
        "Praca dos Tres Poderes s/n",
        "70160900",
        "Brasilia, DF",
        "National Congress public square",
        "12345678905",
    ),
    Recipient(
        "Jordan Lee",
        "Rua Jardim Botanico 1008",
        "22460390",
        "Rio de Janeiro, RJ",
        "Botanical Garden public entrance",
        "12345678906",
    ),
    Recipient(
        "Casey Jones",
        "Largo do Farol da Barra s/n",
        "40140130",
        "Salvador, BA",
        "Barra Lighthouse public square",
        "12345678907",
    ),
)


def customized_zpl(template: str, recipient: Recipient, number: int) -> str:
    """Replace every recipient and shipment field with deterministic fake data."""
    replacements = {
        "^FO120,120^A0N,24,24^FDOrder: 10000^FS": (
            f"^FO120,120^A0N,24,24^FDOrder: {10000 + number}^FS"
        ),
        "^FO250,117^A0N,27,27^FD10000000001^FS": (
            f"^FO250,117^A0N,27,27^FD{10000000001 + number}^FS"
        ),
        "^FO230,210^BY3,,0^BCN,160,N,N,N^FD>:12345678901^FS": (
            f"^FO230,210^BY3,,0^BCN,160,N,N,N^FD>:{recipient.shipment_id}^FS"
        ),
        "^FO95,382^A0N,35,35^FB390,1,0,R^FD123456^FS": (
            f"^FO95,382^A0N,35,35^FB390,1,0,R^FD{recipient.shipment_id[:6]}^FS"
        ),
        "^FO488,378^A0N,45,45^FB400,1,0,L^FD78901^FS": (
            f"^FO488,378^A0N,45,45^FB400,1,0,L^FD{recipient.shipment_id[6:]}^FS"
        ),
        "^FO0,830^A0N,38,38^FB650,1,0,C^FDMON 13/07/2026    NF: 10001^FS": (
            f"^FO0,830^A0N,38,38^FB650,1,0,C^FDMON 13/07/2026    NF: {10001 + number}^FS"
        ),
        "^FO30,965^A0N,33,33^FB600,2,0,L^FH^FDJohn Doe (EXAMPLE)^FS": (
            f"^FO30,965^A0N,33,33^FB600,2,0,L^FH^FD{recipient.name} (EXAMPLE)^FS"
        ),
        "^FO30,1030^A0N,26,26^FB600,2,0,L^FH^FDAddress: Avenida Paulista 1578_2c Bela Vista^FS": (
            "^FO30,1030^A0N,26,26^FB600,2,0,L^FH^FDAddress: "
            f"{recipient.address.replace(',', '_2c')}^FS"
        ),
        "^FO30,1090^A0N,30,30^FDZIP: 01310200^FS": (
            f"^FO30,1090^A0N,30,30^FDZIP: {recipient.postal_code}^FS"
        ),
        "^FO30,1089^A0N,30,30^FDZIP: 01310200^FS": (
            f"^FO30,1089^A0N,30,30^FDZIP: {recipient.postal_code}^FS"
        ),
        "^FO30,1121^A0N,26,26^FB600,2,1000,L^FH^FDDestination: S_C3_A3o Paulo_2c S_C3_A3o Paulo^FS": (
            "^FO30,1121^A0N,26,26^FB600,2,1000,L^FH^FDDestination: "
            f"{recipient.destination.replace(',', '_2c')}^FS"
        ),
        "^FO30,1150^A0N,26,26^FB600,5,0,L^FH^FDDetails: Museu de Arte de S_C3_A3o Paulo_2E Public entrance_2E^FS": (
            f"^FO30,1150^A0N,26,26^FB600,5,0,L^FH^FDDetails: {recipient.details}_2E^FS"
        ),
        '^FO650,985^BY2,2,0^BQN,2,5^FDLA,{"id":"12345678901","t":"lm"}^FS': (
            f'^FO650,985^BY2,2,0^BQN,2,5^FDLA,{{"id":"{recipient.shipment_id}","t":"lm"}}^FS'
        ),
    }
    label = template
    for original, replacement in replacements.items():
        if original not in label:
            raise ValueError(f"Template field not found: {original}")
        label = label.replace(original, replacement)
    return label


def render_with_labelary(zpl: str) -> Image.Image:
    """Render sanitized ZPL through the external reference API."""
    request = urllib.request.Request(
        LABELARY_URL,
        data=zpl.encode("utf-8"),
        headers={
            "Accept": "image/png",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "zplrender-benchmark/0.1",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Labelary returned HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not reach Labelary: {error.reason}") from error
    image = Image.open(io.BytesIO(content)).convert("L")
    if image.size != (812, 1218):
        raise RuntimeError(f"Unexpected Labelary image size: {image.size}")
    black_ratio = sum(pixel < 128 for pixel in image.tobytes()) / (image.width * image.height)
    if not 0.01 < black_ratio < 0.30:
        raise RuntimeError(f"Suspicious Labelary black-pixel ratio: {black_ratio:.2%}")
    return image


def pack_bitmap(image: Image.Image) -> tuple[bytes, int]:
    """Pack thresholded pixels into Zebra's one-bit, byte-aligned rows."""
    bytes_per_row = (image.width + 7) // 8
    pixels = image.tobytes()
    bitmap = bytearray(bytes_per_row * image.height)
    for y in range(image.height):
        for x in range(image.width):
            if pixels[y * image.width + x] < 128:
                bitmap[y * bytes_per_row + x // 8] |= 0x80 >> (x % 8)
    return bytes(bitmap), bytes_per_row


def z64(data: bytes) -> str:
    """Encode a bitmap using Zebra's Z64 envelope."""
    payload = base64.b64encode(zlib.compress(data)).decode("ascii")
    crc = binascii.crc_hqx(payload.encode("ascii"), 0)
    return f":Z64:{payload}:{crc:04X}"


def build_archive(output: Path = OUTPUT) -> None:
    """Render seven fake labels and store them in a reproducible ZIP archive."""
    template = SOURCE.read_text(encoding="utf-8")
    formats: list[str] = []
    for number, recipient in enumerate(RECIPIENTS):
        image = render_with_labelary(customized_zpl(template, recipient, number))
        bitmap, bytes_per_row = pack_bitmap(image)
        name = f"R:LABEL{number + 1:02}.GRF"
        formats.extend(
            (
                f"~DG{name},{len(bitmap)},{bytes_per_row},{z64(bitmap)}",
                f"^XA^FO0,0^XG{name},1,1^FS^PQ1^XZ",
                f"^XA^ID{name}^FS^XZ",
            )
        )
        if number + 1 < len(RECIPIENTS):
            time.sleep(0.4)

    member = "\n".join(formats).encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    info = zipfile.ZipInfo(MEMBER_NAME, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(info, member)
    print(f"Wrote {len(RECIPIENTS)} sanitized raster labels to {output}")


if __name__ == "__main__":
    build_archive()
