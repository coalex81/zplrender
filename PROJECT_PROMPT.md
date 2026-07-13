# Project Prompt: Local ZPL II Renderer for Python

I want to create a new Python package, suitable for publication on PyPI, that interprets and renders a useful subset of the ZPL II language locally.

The goal is to convert ZPL code into PNG images and PDF documents without depending on the Labelary API, a Zebra printer, or any external service during rendering.

This project must be an independent implementation and must not imply affiliation with Zebra Technologies.

## Context

I have already evaluated several existing options:

- `zebrafy`: mainly works with `^GF` graphic fields and does not interpret a complete ZPL label.
- `zpl`: mainly generates ZPL and relies on external services for previews.
- `simple-zpl2`: generates ZPL but is not a complete local renderer.
- `zplgrf`: works with GRF graphics but does not render complete labels.
- Labelary: interprets ZPL well, but conversion happens remotely.
- ZPL2PDF and Zebrash: useful external tools, but not pure Python packages with broad ZPL support.

Therefore, I want to build an independent Python interpreter and renderer, starting with a clearly defined subset of ZPL II.

## Project Principles

1. Do not attempt to implement all of ZPL II immediately.
2. Start with an extensible architecture and a useful subset.
3. Use official Zebra documentation as the primary reference.
4. Do not copy large sections of Zebra manuals into the repository.
5. Do not redistribute proprietary Zebra fonts.
6. Use open-source fonts as substitutes and document visual differences.
7. Do not use the Labelary API in production code.
8. Labelary may be used only in optional development or comparison tools, never as a runtime dependency.
9. Unsupported commands must produce structured warnings or configurable exceptions. Never ignore them silently.
10. The library must work offline.
11. Prioritize readable, typed, testable code.
12. Do not build the parser around one large regular expression.
13. Use English for all source code, documentation, comments, diagnostics, tests, commit messages, and public APIs.

## Required Initial Research

Before implementing the renderer, research and document:

- the official ZPL II programming reference;
- syntax and parameters for first-version commands;
- default values;
- persistent printer state;
- format-level and field-level state;
- coordinate systems and orientation;
- character encodings and `^CI`;
- hexadecimal escapes through `^FH`;
- the `^GF` data format;
- ZPL ASCII compression;
- graphic storage through `~DG`;
- graphic recall through `^XG`;
- object deletion through `^ID`;
- multiple `^XA ... ^XZ` blocks;
- blocks that do not generate printable labels;
- dots, DPI, and dpmm conversions;
- firmware- or model-specific differences that may affect rendering.

Create `docs/research.md` and record all consulted sources, implementation decisions, ambiguities, assumptions, and known differences from real Zebra printers.

Do not invent behavior when the documentation is ambiguous. Record the uncertainty and isolate the implementation so it can be corrected later.

## First-Version Scope

The first useful version should be able to interpret and render common logistics labels containing the following commands.

### Structure and comments

```text
^XA
^XZ
^FS
^FX
```

### Positioning and label dimensions

```text
^FO
^FT
^LH
^LT
^LS
^PW
^LL
^PO
^FW
```

### Text

```text
^FD
^FH
^A
^A0
^CF
^FB
^CI
```

### Graphic shapes

```text
^GB
^GC
^GD
^GE
^FR
```

### Barcodes

```text
^BY
^BC
^B3
^BQ
```

### Graphics

```text
^GF
~DG
^XG
^ID
```

### Quantity and print control

```text
^PQ
```

It is not necessary to implement all of these in the first commit. Organize the work into phases and clearly track the status of each command.

## Suggested Architecture

```text
src/
└── zplrender/
    ├── __init__.py
    ├── api.py
    ├── tokenizer.py
    ├── parser.py
    ├── state.py
    ├── document.py
    ├── elements.py
    ├── memory.py
    ├── diagnostics.py
    ├── exceptions.py
    ├── commands/
    │   ├── __init__.py
    │   ├── base.py
    │   ├── structure.py
    │   ├── positioning.py
    │   ├── text.py
    │   ├── shapes.py
    │   ├── graphics.py
    │   ├── barcodes.py
    │   └── printer.py
    └── renderers/
        ├── __init__.py
        ├── base.py
        ├── pillow.py
        └── pdf.py

tests/
├── unit/
├── integration/
├── fixtures/
└── golden/

docs/
├── research.md
├── supported-commands.md
├── architecture.md
└── compatibility.md
```

The exact layout may be adjusted for a clear technical reason, but keep these responsibilities separate:

- tokenization;
- parsing;
- printer state;
- intermediate document model;
- object memory;
- rendering;
- diagnostics;
- public API.

## Expected Internal Flow

```text
Raw ZPL
  → tokenizer
  → structured commands
  → parser and state machine
  → intermediate document
  → graphical elements
  → Pillow renderer
  → PNG or PDF
```

Do not draw directly during tokenization. The parser must produce an intermediate model that is independent of the graphics backend.

## Command Model

Each command should have its own representation or isolated handler.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class FieldOriginCommand:
    x: int
    y: int
    justification: int | None = None
```

The parser may transform:

```zpl
^FO20,30
^A0N,40,40
^FDHello^FS
```

into an element similar to:

```python
TextElement(
    x=20,
    y=30,
    text="Hello",
    font="0",
    height=40,
    width=40,
    orientation=Orientation.NORMAL,
)
```

## Printer State

Create an explicit printer-state model.

```python
from dataclasses import dataclass


@dataclass
class PrinterState:
    dpi: int = 203
    label_width: int | None = None
    label_length: int | None = None

    home_x: int = 0
    home_y: int = 0
    label_top: int = 0
    label_shift: int = 0

    field_x: int = 0
    field_y: int = 0

    orientation: str = "N"
    default_font: str = "0"
    default_font_height: int = 30
    default_font_width: int = 30

    reverse_print: bool = False
    character_set: int = 0
    field_hex_enabled: bool = False
    field_hex_indicator: str = "_"
```

Adjust the model as research reveals the correct behavior. Carefully distinguish persistent printer state, current format state, current field state, and stored resources.

## Tokenizer Requirements

The tokenizer must account for the following:

- commands normally begin with `^` or `~`;
- `^FD` may contain arbitrary text until `^FS`;
- command-prefix characters may be changed;
- parameter delimiters may be changed;
- several commands may appear on the same line;
- commands may appear without spaces or line breaks;
- files may contain commands before the first `^XA`;
- a file may contain multiple labels;
- not every `^XA ... ^XZ` block generates a page;
- graphics data may be large;
- field data may contain hexadecimal escapes;
- unknown commands must preserve their raw data for diagnostics.

Do not use a general solution such as:

```python
re.findall(r"\^[A-Z0-9]{1,2}.*", zpl)
```

## Text and Encoding

Implement text decoding as a separate layer. It must account for `^CI`, `^FH`, configurable hexadecimal escape indicators, UTF-8 under `^CI28`, invalid byte sequences, and configurable error handling.

Example:

```zpl
^CI28
^FH
^FDS_C3_A3o Paulo^FS
```

must produce:

```text
São Paulo
```

Do not perform hexadecimal substitution across the entire ZPL input. Decode escapes only in the correct field-data context.

## Graphics

The implementation of `^GF` and `~DG` must be modular.

Support or plan for:

- uncompressed hexadecimal data;
- ZPL ASCII compression;
- row repetition;
- character-encoded repeat counts;
- total byte counts;
- bytes per row;
- actual image width;
- metadata validation;
- names such as `R:LOGO.GRF`;
- simulated printer memory;
- graphic recall through `^XG`;
- deletion through `^ID`.

A real-world example to support is:

```zpl
^GFA,800,800,10,,:::::::::::O0FF,M07JFE,...
```

This is not plain hexadecimal. Do not call `bytes.fromhex(data)` before interpreting ZPL ASCII compression.

Design interfaces similar to:

```python
from typing import Protocol


class GraphicDecoder(Protocol):
    def decode(self, command: GraphicFieldCommand) -> RasterGraphic:
        ...
```

Keep parameter parsing, decompression, validation, bitmap creation, positioning, and rendering separate.

## Fonts

Do not include proprietary Zebra fonts.

For the initial version:

- use an open-source font such as DejaVu Sans;
- allow users to configure font files or directories;
- create a mapping between ZPL font identifiers and local fonts;
- document that font metrics may differ from real printers;
- keep the font backend replaceable.

```python
FontRegistry.register(
    zpl_name="0",
    path="/path/to/DejaVuSans.ttf",
)
```

Only bundle a default font if its license permits redistribution.

## Field Blocks (`^FB`)

Implement `^FB` as an isolated layout component. It must account for block width, maximum line count, line spacing, alignment, hanging indent, word wrapping, truncation, and interaction with the selected font.

Create dedicated tests for each behavior. Do not place all `^FB` logic inside the general text renderer.

## Barcodes

Create an abstraction per symbology.

```python
from typing import Protocol


class BarcodeRenderer(Protocol):
    def render(
        self,
        data: str,
        options: BarcodeOptions,
    ) -> RasterGraphic:
        ...
```

Start with Code 128 through `^BC`, Code 39 through `^B3`, and QR Code through `^BQ`.

Account for `^BY`, barcode height, module width, wide-to-narrow ratio, orientation, human-readable lines, check digits, quiet zones, Code 128 subset-selection sequences, and QR data beginning with `LA,`.

Do not assume an external barcode library reproduces Zebra dimensions exactly. Isolate it behind an interface.

## Rendering Backend

Use Pillow for the initial backend. The first PDF implementation may be generated from rendered page images.

```python
from typing import Protocol


class Renderer(Protocol):
    def render_page(
        self,
        page: LabelPage,
        options: RenderOptions,
    ) -> RenderedPage:
        ...
```

Do not couple the parser directly to Pillow.

## Public API

Desired examples:

```python
from zplrender import render

result = render(zpl, dpi=203)
result.pages[0].save("label.png")
result.to_pdf("labels.pdf")
```

```python
from zplrender import ZPLDocument

document = ZPLDocument.parse(zpl)
result = document.render(dpi=203)

for index, page in enumerate(result.pages, start=1):
    page.save(f"label-{index}.png")
```

```python
from zplrender import render_pdf, render_png

render_png(zpl, "label.png", dpi=203)
render_pdf(zpl, "labels.pdf", dpi=203)
```

Clearly define multiple-label behavior:

- `render()` returns all pages;
- `render_png()` requires one page or supports an output-name pattern;
- `render_pdf()` includes all rendered pages.

## Command-Line Interface

Create:

```bash
zplrender input.zpl
```

Desired options:

```bash
zplrender input.zpl --output labels.pdf
zplrender input.zpl --format png
zplrender input.zpl --dpi 203
zplrender input.zpl --strict
zplrender input.zpl --show-warnings
```

The CLI must infer format from the output extension, default to PDF, return non-zero exit codes for errors, and print unsupported-command warnings. Stdin support may be added later.

## Diagnostics

Implement structured diagnostics.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Diagnostic:
    severity: Severity
    code: str
    message: str
    offset: int | None = None
    command: str | None = None
```

Suggested codes:

```text
ZPL001 — unknown command
ZPL002 — invalid parameter
ZPL003 — command outside a format
ZPL004 — field missing ^FS
ZPL005 — invalid graphic data
ZPL006 — font substitution
ZPL007 — invalid encoding
ZPL008 — resource not found in memory
```

Support permissive and strict modes.

## Exceptions

```python
class ZPLError(Exception):
    pass


class ZPLSyntaxError(ZPLError):
    pass


class ZPLUnsupportedCommandError(ZPLError):
    pass


class ZPLRenderError(ZPLError):
    pass


class ZPLGraphicDecodeError(ZPLError):
    pass


class ZPLResourceNotFoundError(ZPLError):
    pass
```

## Tests

Use `pytest` and `pytest-cov`.

Create unit tests for tokenizer behavior, optional parameters, empty numeric parameters, adjacent commands, multiple formats, `^FH`, `^CI28`, coordinates, orientation, shapes, graphic memory, `^GF` decompression, barcodes, unknown commands, and strict/permissive modes.

Create integration tests that render complete pages. Use golden-image tests under `tests/golden/`. Compare pixels, normalized hashes, or dimensions rather than PNG file bytes.

Required fixtures include simple text, UTF-8 with `^FH`, boxes, Code 128, QR Code, multiple labels, and administrative blocks such as:

```zpl
^XA
^IDR:DEMO.GRF
^FS
^XZ
```

That administrative block must not automatically create a blank page.

## Compatibility Comparison Tool

Create an optional tool at `tools/compare_images.py` that accepts two images, normalizes dimensions, computes pixel differences, writes a diff image, and reports a difference percentage.

Do not call Labelary during normal tests. Network-dependent tests must be disabled by default and marked with:

```python
@pytest.mark.network
```

## Code Quality

Configure `ruff`, `mypy`, `pytest`, and `pytest-cov` in `pyproject.toml`.

Requirements:

- Python 3.11 or newer;
- type hints for public interfaces;
- reasonable initial coverage;
- public documentation;
- no unnecessary dependencies;
- no circular imports;
- no mutable global state;
- small functions;
- dataclasses for models;
- enums for orientation, severity, and other closed sets.

Development commands:

```bash
python -m pytest
python -m ruff check .
python -m mypy src
```

## Packaging

Use a `src` layout and configure the project for eventual PyPI publication.

The `pyproject.toml` must contain a temporary package name, version `0.1.0`, description, license, runtime dependencies, optional development dependencies, CLI entry point, classifiers, and minimum Python version.

Before selecting a final name, check whether it already exists on PyPI. If that cannot be verified, use a clearly marked temporary name such as:

```text
zplrender
zpl-renderer
pyzplrender
zpl2image
```

Do not publish anything automatically.

## License and Notices

Prefer MIT or Apache-2.0. Create `LICENSE` and `NOTICE`.

The notice should state that the project is independent, Zebra and ZPL are trademarks of their respective owners, no proprietary Zebra fonts are included, compatibility is partial, and behavior may differ across printer models and firmware versions.

Do not make definitive legal claims. Prepare text for human review.

## Documentation

Create a README containing project purpose, experimental status, installation, API examples, CLI examples, supported and unsupported commands, limitations, font differences, compatibility policy, contribution instructions, and test commands.

Create `docs/supported-commands.md` with:

```text
Command | Status | Tested | Notes
```

Allowed statuses:

```text
planned
partial
implemented
verified
```

## Development Phases

### Phase 1 — Foundation

- research the specification;
- create `pyproject.toml`;
- create the package structure;
- configure tests, Ruff, and mypy;
- define models, diagnostics, and exceptions;
- implement the basic tokenizer;
- implement `^XA`, `^XZ`, `^FS`, and `^FX`;
- add tests.

### Phase 2 — Basic text rendering

- implement `^FO`;
- implement `^FD`;
- implement `^A0`;
- implement `^PW` and `^LL`;
- render text and pages using Pillow;
- generate PNG output;
- add simple PDF output;
- add visual tests.

### Phase 3 — Encoding and layout

- `^CI`;
- `^FH`;
- `^FB`;
- `^LH`;
- `^LT`;
- `^LS`;
- orientation handling.

### Phase 4 — Shapes

- `^GB`;
- `^GC`;
- `^GD`;
- `^GE`;
- `^FR`.

### Phase 5 — Barcodes

- `^BY`;
- `^BC`;
- `^B3`;
- `^BQ`.

### Phase 6 — Graphics

- hexadecimal `^GF`;
- ZPL ASCII compression;
- `~DG`;
- `^XG`;
- `^ID`;
- simulated printer memory.

### Phase 7 — Robustness

- multiple formats;
- unknown commands;
- strict mode;
- diagnostics;
- complete CLI;
- documentation;
- benchmarks;
- compatibility tests.

## Acceptance Criteria for the First Delivery

The first delivery does not need to complete every phase. At minimum, it must:

1. create the complete initial repository structure;
2. provide `pyproject.toml`;
3. install with `pip install -e ".[dev]"`;
4. pass `pytest`, `ruff check .`, and `mypy src`;
5. interpret the following ZPL:

```zpl
^XA
^PW812
^LL1218
^FO50,50
^A0N,50,50
^FDHello World^FS
^XZ
```

6. generate a PNG with approximately correct text placement;
7. generate a one-page PDF;
8. support multiple simple labels;
9. produce diagnostics for unknown commands;
10. include a README and architecture documentation;
11. perform no network calls;
12. have no runtime dependency on Labelary.

## Working Method

Before changing files:

1. inspect the repository;
2. present a short plan;
3. identify unresolved design decisions;
4. perform the initial research;
5. implement one coherent phase at a time;
6. run all tests;
7. fix failures;
8. summarize changes;
9. list limitations and next steps.

Do not implement the entire project in one massive change.

Create small, logical commits when the environment allows it, but do not push or publish anything without explicit authorization.

When the ZPL specification is ambiguous:

- consult primary documentation;
- record the decision in `docs/research.md`;
- add a test representing the decision;
- isolate the behavior so it can be corrected later.

Start with research and Phase 1. Continue into a minimal Phase 2 proof of concept only if all previous tests remain green.
