"""Tokenizer tests for adjacent and pre-format commands."""

from zplrender.tokenizer import tokenize


def test_tokenizes_download_before_adjacent_format() -> None:
    tokens = tokenize("~DGR:ONE.GRF,1,1,80^XA^FO0,0^XGR:ONE.GRF,1,1^FS^XZ")

    assert [token.command for token in tokens] == [
        "~DG",
        "^XA",
        "^FO",
        "^XG",
        "^FS",
        "^XZ",
    ]
    assert tokens[0].data == "R:ONE.GRF,1,1,80"
