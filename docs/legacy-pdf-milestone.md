# Legacy PDF milestone

## Goal

Render representative ZPL inputs into offline PDF files without Labelary, a
Zebra printer, or another external rendering service. Private source material
is kept outside version control; tests use a sanitized fixture.

This milestone covers two input styles that exercise different parts of the
interpreter:

1. `tests/fixtures/zpl/shipping_label.zpl` describes a sanitized label using
   text, shapes, barcodes, and a project-owned geometric parcel mark.
2. The original source material also exercised stored compressed graphics,
   simulated printer memory, recalls, printing, and deletion. Focused unit
   tests preserve that command coverage without tracking private labels.

Both reference PDFs use 4 by 6 inch pages (288 by 432 PDF points). Rendering at
203 DPI therefore produces a nominal page of 812 by 1218 dots. Stored graphic
rows are byte-aligned, so a source bitmap may be slightly wider than the
printable page; the renderer must clip it to the page bounds.

## Commands required by the fixtures

### Native label fixture

| Command | Required behavior |
| --- | --- |
| `^XA`, `^XZ` | Start and finish a format |
| `^MC` | Parse and retain map-clear state; no visible effect is required yet |
| `^CI28` | Select UTF-8 field decoding |
| `^LH` | Apply the label-home offset |
| `^FX` | Consume comments without creating fields |
| `^FO` | Position the next field |
| `^A0` | Select scalable font 0, dimensions, and orientation |
| `^FD`, `^FS` | Capture and finish field data |
| `^FH` | Decode hexadecimal byte escapes within field data only |
| `^FB` | Wrap and align text inside field blocks |
| `^GB` | Draw boxes and lines, including zero-height lines |
| `^FR` | Reverse the pixels covered by the current field |
| `^BY` | Set barcode module defaults |
| `^BC` | Render Code 128 and interpret Zebra invocation sequences such as `>:` |
| `^BQ` | Render QR Code and handle the `LA,` data prefix |
| `^GF` | Decode inline ASCII-compressed raster graphics |

### Stored-raster archive

| Command | Required behavior |
| --- | --- |
| `~DG` | Download a named graphic before a format begins |
| `^MM`, `^MN` | Parse print/media settings; no visible effect is required yet |
| `^PO` | Preserve print-orientation state (`N` in the fixture) |
| `^FO` | Position the recalled bitmap |
| `^XG` | Recall and magnify a named graphic from simulated memory |
| `^PQ` | Emit the requested number of page copies |
| `^ID` | Delete the named graphic from simulated memory |

The archive uses `:Z64:<base64>:<crc>` data in `~DG`. Supporting ordinary ZPL
ASCII run-length compression alone is not enough. The decoder must validate
the envelope and metadata, Base64-decode it, decompress it, verify the declared
byte count and row width, and report invalid CRC or content through structured
diagnostics. CRC behavior must be confirmed with specification fixtures before
strict validation is enabled by default.

## Required processing pipeline

```text
bytes or text input
  -> tokenizer
  -> command parser and printer state
  -> simulated graphic memory
  -> backend-independent label pages
  -> 1-bit or grayscale Pillow canvases
  -> multipage PDF
```

The tokenizer must recognize commands before the first `^XA`, keep large
graphic payloads intact, and process adjacent commands without relying on line
breaks. A `^XA ... ^XZ` block that only deletes a resource is administrative
and must not create a blank PDF page.

## Modules to implement

- `tokenizer.py`: offsets, caret/tilde commands, field-data boundaries, and
  opaque graphic payloads.
- `commands/`: typed command models and parameter parsing for the commands in
  the tables above.
- `state.py`: persistent printer state, current-format state, and field state.
- `memory.py`: named raster resources keyed by device, name, and extension.
- `document.py` and `elements.py`: pages plus text, shape, barcode, and raster
  elements independent of Pillow.
- `renderers/pillow.py`: dot-accurate raster canvas, clipping, field reversal,
  fonts, barcodes, and graphics.
- `renderers/pdf.py`: convert all rendered pages into one PDF while preserving
  the 4 by 6 inch physical page size.
- `api.py`: `render`, `render_pdf`, and `ZPLDocument.parse(...).render(...)`.
- `cli.py`: accept plain ZPL initially; ZIP input can remain a separate input
  adapter until the renderer itself is stable.

## Dependencies and isolated backends

The first implementation needs Pillow for canvas drawing, font rendering, PNG,
and image-backed PDF output. Barcode generation should sit behind internal
interfaces. A small Code 128 and QR dependency may be selected after comparing
its module widths and quiet zones with the reference PDFs; Zebra-specific data
prefixes and dimensions remain package logic rather than library assumptions.

Liberation Sans Narrow Bold is the preferred substitute for Zebra font 0, with
DejaVu fallbacks behind a font registry. Metric differences are documented and
no proprietary fonts are bundled.

ZIP and RAR traversal shown in the legacy experiments is not part of the core
renderer. The core API consumes ZPL bytes or text. A later input layer may add
ZIP support; RAR support should remain optional because it adds a system or
third-party dependency.

## Implementation order

1. Tokenize all commands in both fixtures and preserve raw payloads.
2. Split printable and administrative formats correctly.
3. Implement `~DG` Z64 decoding, graphic memory, `^XG`, `^ID`, and `^PQ`.
4. Render the seven stored-raster labels to a multipage 4 by 6 inch PDF.
5. Add positioning, text decoding, font rendering, field blocks, shapes, and
   field reversal for the native label.
6. Add Code 128, QR Code, and inline `^GF` ASCII decompression.
7. Render the native fixture and compare it with its reference PDF.
8. Expose the public PDF API and CLI only after the internal pipeline is stable.

This order produces a useful offline seven-page PDF early while retaining the
interpreter architecture needed for non-rasterized labels.

## Acceptance tests

- The package performs no network calls.
- The sanitized shipping label produces one 4 by 6 inch PDF page.
- Stored `~DG` resources are decoded and can be deleted after use.
- Administrative `^ID` formats create no additional pages.
- UTF-8 hexadecimal escapes render `São`, `Praça`, and other
  accented text correctly.
- The native page contains a scannable Code 128 barcode and QR Code.
- Rendered raster dimensions, page count, and physical PDF dimensions match the
  reference files.
- Image comparisons use rasterized PDF pages and tolerance-based pixel metrics,
  not PDF byte equality.
- Unknown or malformed commands and graphics produce structured diagnostics;
  strict mode raises package exceptions.

## Explicitly deferred

- Complete ZPL II compatibility.
- Exact Zebra proprietary font metrics.
- Printer media handling, cutting, pausing, and thermal behavior.
- RAR input as a mandatory runtime feature.
- Perfect reproduction across printer models and firmware versions.
