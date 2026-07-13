"""CLI input adapter and error-reporting tests."""

import sys
from pathlib import Path
from zipfile import ZipFile

from zplrender.cli import main, read_zpl_input


def test_reads_zpl_member_from_zip(tmp_path: Path) -> None:
    archive_path = tmp_path / "labels.zip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("ignore.bin", b"\xff\xfe")
        archive.writestr("label.txt", "~DGR:A.GRF,1,1,80^XA^FO0,0^XGR:A.GRF,1,1^XZ")

    assert read_zpl_input(archive_path).startswith("~DGR:A.GRF")


def test_rejects_pdf_as_input_without_traceback(
    tmp_path: Path, monkeypatch: object, capsys: object
) -> None:
    pdf_path = tmp_path / "reference.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(sys, "argv", ["zplrender", str(pdf_path)])  # type: ignore[attr-defined]

    exit_code = main()
    captured = capsys.readouterr()  # type: ignore[attr-defined]

    assert exit_code == 2
    assert "PDF files are outputs" in captured.err
    assert "Traceback" not in captured.err


def test_reports_no_printable_pages_without_traceback(
    tmp_path: Path, monkeypatch: object, capsys: object
) -> None:
    zpl_path = tmp_path / "unsupported.zpl"
    zpl_path.write_text("^XA^FXNo printable fields^FS^XZ", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["zplrender", str(zpl_path)])  # type: ignore[attr-defined]

    exit_code = main()
    captured = capsys.readouterr()  # type: ignore[attr-defined]

    assert exit_code == 2
    assert "without printable label pages" in captured.err
    assert "Traceback" not in captured.err


def test_refuses_to_overwrite_existing_output(
    tmp_path: Path, monkeypatch: object, capsys: object
) -> None:
    zpl_path = tmp_path / "label.zpl"
    output_path = tmp_path / "label.pdf"
    zpl_path.write_text("^XA^FO0,0^GB10,10,1^FS^XZ", encoding="utf-8")
    original = b"existing PDF"
    output_path.write_bytes(original)
    monkeypatch.setattr(  # type: ignore[attr-defined]
        sys, "argv", ["zplrender", str(zpl_path), "--output", str(output_path)]
    )

    exit_code = main()
    captured = capsys.readouterr()  # type: ignore[attr-defined]

    assert exit_code == 2
    assert "Output file already exists" in captured.err
    assert "use --force to replace it" in captured.err
    assert output_path.read_bytes() == original


def test_force_overwrites_existing_output(
    tmp_path: Path, monkeypatch: object, capsys: object
) -> None:
    zpl_path = tmp_path / "label.zpl"
    output_path = tmp_path / "label.pdf"
    zpl_path.write_text("^XA^FO0,0^GB10,10,1^FS^XZ", encoding="utf-8")
    output_path.write_bytes(b"existing PDF")
    monkeypatch.setattr(  # type: ignore[attr-defined]
        sys,
        "argv",
        ["zplrender", str(zpl_path), "--output", str(output_path), "--force"],
    )

    exit_code = main()
    captured = capsys.readouterr()  # type: ignore[attr-defined]

    assert exit_code == 0
    assert "Rendered 1 page(s)" in captured.out
    assert output_path.read_bytes().startswith(b"%PDF")
