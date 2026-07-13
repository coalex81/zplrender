# zplrender

`zplrender` is an experimental Python package for interpreting and rendering a
useful subset of ZPL II locally.

The current milestone supports stored `~DG` graphics using hexadecimal or Z64
data, simulated printer memory through `^XG` and `^ID`, print quantity through
`^PQ`, and image-backed multipage PDF output. It also renders the native text,
field blocks, boxes, reverse fields, inline `^GF` graphics, Code 128, and QR
commands exercised by the included sanitized shipping-label fixture.

Compatibility is deliberately partial. See `docs/supported-commands.md` for
command-level status. Liberation Sans Narrow Bold is the preferred substitute
for Zebra font 0, with DejaVu fallbacks, so text metrics and line breaks can
still differ from a real printer.

The project is independent and is not affiliated with Zebra Technologies.
Zebra and ZPL are trademarks of their respective owners.

Production label data is not tracked. The realistic fixture under
`tests/fixtures/zpl/` uses synthetic identities and public-landmark addresses;
see `benchmarks/` for its reproducible Labelary visual comparison.

## Development installation

```bash
python -m pip install -e ".[dev]"
```

The public package can then be imported:

```python
import zplrender

print(zplrender.__version__)

zpl = "~DGR:DOT.GRF,1,1,80^XA^FO0,0^XGR:DOT.GRF,1,1^XZ"
zplrender.render_pdf(zpl, "label.pdf")
```

The CLI accepts either a UTF-8 ZPL text file or a ZIP archive containing one or
more ZPL documents:

```bash
zplrender labels.zpl --output labels.pdf
zplrender labels.zip --output labels.pdf --strict
```

The CLI refuses to overwrite an existing PDF. Pass `--force` when replacing
the destination is intentional:

```bash
zplrender labels.zpl --output labels.pdf --force
```

The distribution and import names are temporarily both `zplrender`. The final
distribution name must be checked for availability before publication.
