# ZPL II research notes

This file records specification research and implementation decisions. The
current content is a focused preliminary pass for the legacy PDF milestone; it
does not complete the broader Phase 1 research checklist.

## Primary sources consulted

- Zebra, *ZPL Commands*: alphabetical command reference and command-index
  starting point.
  <https://docs.zebra.com/us/en/printers/software/zpl-pg/c-zpl-zpl-commands.html>
- Zebra, *^GF — Graphic Field*: compression selector, byte counts, bytes per
  row, and ASCII hexadecimal field data.
  <https://docs.zebra.com/content/tcm/us/en/printers/software/zpl-pg/zpl-commands/%5Egf.html>
- Zebra, *~DG — Download Graphics*: resource naming, storage devices, total
  bytes, row width, and hexadecimal raster representation.
  <https://docs.zebra.com/us/en/printers/software/zpl-pg/zpl-commands/~dg2.html>
- Zebra, *B64 and Z64 Encoding*: envelope format, Base64 encoding, LZ77
  compression, and CRC validation.
  <https://docs.zebra.com/content/tcm/us/en/printers/software/zpl-pg/zb64-encoding-and-compression/b64-and-z64-encoding.html>
- Zebra, *^XG — Recall Graphic*: resource lookup and x/y magnification.
  <https://docs.zebra.com/content/tcm/us/en/printers/software/zpl-pg/zpl-commands/%5Exg.html>
- Zebra, *Deleting Graphics from Memory*: `^ID` behavior and stand-alone
  administrative formats.
  <https://docs.zebra.com/us/en/printers/software/zpl-pg/advanced-techniques/deleting-graphics-from-memory.html>
- Zebra, *^PQ — Print Quantity*: page quantity and defaults.
  <https://docs.zebra.com/us/en/printers/software/zpl-pg/zpl-commands/%5Epq.html>
- Zebra, *^PO — Print Orientation*: coordinate inversion and persistent state.
  <https://docs.zebra.com/us/en/printers/software/zpl-pg/zpl-commands/%5Epo.html>

## Fixture findings and decisions

- Both reference PDFs are 288 by 432 points, exactly 4 by 6 inches.
- The initial density is 203 DPI (approximately 8 dots/mm), yielding nominal
  812 by 1218 dot pages.
- The stored graphics declare 102 bytes per row and 124,236 total bytes. This
  equals 816 byte-aligned pixels by 1,218 rows. The rightmost padding is clipped
  to the 812-dot page.
- `~DG` occurs before `^XA`; parsing only inside label formats is incorrect.
- Each printable stored-graphic format is followed by a stand-alone `^ID`
  format. Page creation must depend on printable content, not merely on seeing
  `^XA` and `^XZ`.
- The fixture CRC is CRC-16/CCITT as exposed by Python's `binascii.crc_hqx`,
  initialized with zero and calculated over the ASCII Base64 payload. All seven
  fixture checksums validate this way.
- The fixture Z64 payloads are zlib-compatible streams and decompress to their
  declared 124,236 bytes.
- `^PO` is persistent printer state according to Zebra documentation. State
  scopes must therefore be explicit even though the fixture sends `^PON`.
- Core rendering accepts ZPL content and does not own archive traversal. This
  keeps ZIP/RAR policy outside the language interpreter.

## Open questions

- Add independent Z64 vectors beyond the legacy fixture before claiming broad
  firmware compatibility. Keep the decompressor behind an interface.
- Determine default `^PW` and `^LL` behavior when they are absent. For these
  fixtures, render options explicitly provide 4 by 6 inches rather than
  pretending a universal printer default.
- Compare open-source barcode libraries for Zebra module sizing, quiet zones,
  Code 128 invocation handling, and QR magnification.
- Measure DejaVu Sans substitutions against the native-label reference and
  document unavoidable metric differences.

## Native legacy label decisions

- Code 128 field origin is the first bar. Required quiet space belongs outside
  the encoded field and must not shift the barcode right from its `^FO`
  coordinate. Matching this behavior reduced the sanitized native benchmark
  from 12.0957% to 7.3394% thresholded pixel difference.

- `^CI28` fields are decoded as UTF-8 after field-local `^FH` byte expansion.
- Font 0 resolves through a registry that prefers system Liberation Sans Narrow
  Bold, with DejaVu Sans Bold and DejaVu Sans fallbacks. The Liberation height
  is calibrated to 103% and `^A0` width scales independently. This reduced the
  sanitized benchmark from 7.3394% to 7.2599%; the substitute is intentionally
  not presented as identical to Zebra font 0.
- `^FB` reduces the available wrap width by the hanging indent on continuation
  lines and expands inter-word spacing on non-final justified lines. A dedicated
  synthetic Labelary fixture covers left, center, right, wrapped, indented, and
  justified blocks; these corrections reduced its visual difference from
  4.0978% to 3.5774%.
- The fixture's `^BC` data begins with `>:` and is encoded explicitly from Code
  128 Start B rather than delegated to a library's automatic subset choice.
- The fixture's restored Labelary reference decodes as Model 2, five-dot
  modules, M error correction, mask 1, and the expected JSON payload. Matching
  it requires automatic numeric segmentation and automatic mask selection for
  `LA,`. This differs from a literal reading of Zebra's documented L switch, so
  the compatibility behavior is isolated for future firmware-specific policy.
