"""Stored-resource parser behavior tests."""

from zplrender.parser import parse


def test_administrative_delete_format_does_not_create_page() -> None:
    source = (
        "~DGR:ONE.GRF,1,1,80"
        "^XA^FO0,0^XGR:ONE.GRF,1,1^PQ2,0,0,N^XZ"
        "^XA^IDR:ONE.GRF^FS^XZ"
    )

    document = parse(source, strict=True)

    assert len(document.pages) == 2
    assert document.diagnostics == ()


def test_missing_resource_produces_diagnostic_in_permissive_mode() -> None:
    document = parse("^XA^FO0,0^XGR:MISSING.GRF,1,1^XZ")

    assert document.pages == ()
    assert len(document.diagnostics) == 1
    assert document.diagnostics[0].code == "ZPL002"
    assert "not found" in document.diagnostics[0].message
