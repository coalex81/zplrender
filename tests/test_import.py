"""Package installation and import smoke tests."""

import zplrender


def test_package_is_importable() -> None:
    assert zplrender.__version__ == "0.1.0"


def test_document_can_be_created_from_source() -> None:
    document = zplrender.ZPLDocument.parse("^XA^XZ")

    assert document.source == "^XA^XZ"
    assert document.parsed.pages == ()
