"""Simulated printer object memory."""

from dataclasses import dataclass, field

from zplrender.elements import RasterGraphic
from zplrender.exceptions import ZPLResourceNotFoundError


def normalize_resource_name(name: str) -> str:
    """Normalize a Zebra resource name for case-insensitive lookup."""
    normalized = name.strip().upper()
    if ":" not in normalized:
        normalized = f"R:{normalized}"
    if "." not in normalized.rsplit(":", maxsplit=1)[-1]:
        normalized = f"{normalized}.GRF"
    return normalized


@dataclass
class GraphicMemory:
    """In-memory simulation of named Zebra graphic resources."""

    _graphics: dict[str, RasterGraphic] = field(default_factory=dict)

    def store(self, name: str, graphic: RasterGraphic) -> None:
        """Store or replace a named graphic."""
        self._graphics[normalize_resource_name(name)] = graphic

    def recall(self, name: str) -> RasterGraphic:
        """Return a named graphic or raise a structured package exception."""
        normalized = normalize_resource_name(name)
        try:
            return self._graphics[normalized]
        except KeyError as error:
            raise ZPLResourceNotFoundError(f"Graphic resource not found: {normalized}") from error

    def delete(self, name: str) -> bool:
        """Delete a named graphic and report whether it existed."""
        return self._graphics.pop(normalize_resource_name(name), None) is not None

    def __len__(self) -> int:
        """Return the number of stored graphics."""
        return len(self._graphics)
