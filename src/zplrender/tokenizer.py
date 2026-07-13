"""ZPL tokenization."""

from dataclasses import dataclass

from zplrender.exceptions import ZPLSyntaxError


@dataclass(frozen=True)
class Token:
    """One caret or tilde ZPL command with its unparsed parameter data."""

    prefix: str
    name: str
    data: str
    offset: int

    @property
    def command(self) -> str:
        """Return the command identifier, including its prefix."""
        return f"{self.prefix}{self.name}"


def tokenize(source: str) -> tuple[Token, ...]:
    """Split a ZPL stream into commands without relying on line boundaries.

    Command payloads remain opaque here. In particular, large ``~DG`` and
    ``^GF`` data fields are decoded by their dedicated command handlers.
    """
    tokens: list[Token] = []
    position = 0

    while position < len(source):
        caret = source.find("^", position)
        tilde = source.find("~", position)
        starts = [candidate for candidate in (caret, tilde) if candidate >= 0]
        if not starts:
            break

        start = min(starts)
        if start + 2 >= len(source):
            raise ZPLSyntaxError(f"Incomplete command prefix at offset {start}")

        name = source[start + 1 : start + 3].upper()
        if not all(character.isalnum() or character == "@" for character in name):
            raise ZPLSyntaxError(f"Invalid command name at offset {start}: {name!r}")

        next_caret = source.find("^", start + 3)
        next_tilde = source.find("~", start + 3)
        ends = [candidate for candidate in (next_caret, next_tilde) if candidate >= 0]
        end = min(ends) if ends else len(source)

        tokens.append(
            Token(
                prefix=source[start],
                name=name,
                data=source[start + 3 : end].strip("\r\n"),
                offset=start,
            )
        )
        position = end

    return tuple(tokens)
