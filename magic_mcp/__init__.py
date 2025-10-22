"""Magic MCP package exposing the MCP server application."""

from .server import app, MagicSquareResult, generate_magic_square

__all__ = [
    "app",
    "MagicSquareResult",
    "generate_magic_square",
]
