# Supported commands

Status values are `planned`, `partial`, `implemented`, and `verified`.

| Command | Status | Tested | Notes |
| --- | --- | --- | --- |
| `^XA` | verified | Yes | Starts a format |
| `^XZ` | verified | Yes | Ends a format; empty administrative formats do not create pages |
| `^FS` | implemented | Yes | Finishes text field-level state |
| `^FO` | verified | Yes | Positions raster graphics and native text |
| `~DG` | verified | Yes | Uncompressed hexadecimal and Z64 graphic downloads |
| `^XG` | verified | Yes | Named graphic recall with integer x/y magnification |
| `^ID` | verified | Yes | Deletes an exact named graphic resource |
| `^PQ` | verified | Yes | Produces the requested number of page copies |
| `^MM` | partial | Yes | Parsed and ignored for raster output |
| `^MN` | partial | Yes | Parsed and ignored for raster output |
| `^PO` | partial | Yes | Normal orientation is accepted; inversion is not implemented |
| `^FX` | implemented | Yes | Consumed without creating a field |
| `^LH` | implemented | Yes | Applies label-home offsets to field origins |
| `^A0` | partial | Yes | Registry-backed font 0, normal orientation, independent height/width dimensions |
| `^FD` | implemented | Yes | Creates decoded text fields |
| `^FH` | implemented | Yes | Configurable field-local hexadecimal indicator |
| `^FB` | partial | Yes | Width, line limit, spacing, left/center/right alignment, indent |
| `^GB` | implemented | Yes | Boxes, rounded outlines, and zero-width/height lines |
| `^FR` | partial | Yes | Reversed text, raster, and box fields |
| `^BY` | partial | Yes | Module width and default barcode height |
| `^BC` | partial | Yes | Normal Code 128 Subset B, `>:` invocation, height, interpretation flags |
| `^BQ` | partial | Yes | Normal Model 2 QR, automatic `LA,` data, magnification, correction, mask |
| `^GF` | implemented | Yes | ASCII hexadecimal and Zebra run-length compression |
