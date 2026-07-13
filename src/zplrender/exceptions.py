"""Package-specific exception hierarchy."""


class ZPLError(Exception):
    """Base exception for zplrender failures."""


class ZPLSyntaxError(ZPLError):
    """Raised when the ZPL command stream is malformed."""


class ZPLGraphicDecodeError(ZPLError):
    """Raised when graphic data cannot be decoded or validated."""


class ZPLResourceNotFoundError(ZPLError):
    """Raised when a format recalls a resource that is not in printer memory."""


class ZPLRenderError(ZPLError):
    """Raised when a document cannot be rendered."""
