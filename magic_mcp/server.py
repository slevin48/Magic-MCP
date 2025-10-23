"""MCP server implementation that exposes a magic square generation tool."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

import numpy as np
import requests
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from requests import Response

API_URL = "https://matlab-0j1h.onrender.com/mymagic/mymagic"


@dataclass(slots=True)
class MagicSquareResult:
    """Structured result returned by the :func:`generate_magic_square` tool.

    Attributes
    ----------
    size:
        The order of the square returned by the remote API.
    square:
        A NumPy array representation of the magic square.
    metadata:
        Additional information returned by the API. The raw JSON payload is
        preserved so callers can inspect debugging output or other fields that
        are not explicitly parsed.
    """

    size: int
    square: np.ndarray
    metadata: Dict[str, Any]

    def as_dict(self) -> Dict[str, Any]:
        """Serialize the result into JSON-friendly primitives."""

        data: Dict[str, Any] = {
            "size": self.size,
            "square": self.square.tolist(),
        }
        if self.metadata:
            data["metadata"] = self.metadata
        return data


def _extract_square(payload: Any) -> Optional[Iterable[Iterable[Any]]]:
    """Recursively search for a square matrix-like structure within *payload*."""

    if isinstance(payload, dict):
        # Prioritise common keys used by the MATLAB API but gracefully fall back
        # to a generic search so the parser remains resilient to schema changes.
        preferred_keys = (
            "magic_square",
            "magicSquare",
            "square",
            "result",
            "data",
            "output",
        )
        for key in preferred_keys:
            if key in payload:
                candidate = _extract_square(payload[key])
                if candidate is not None:
                    return candidate
        for value in payload.values():
            candidate = _extract_square(value)
            if candidate is not None:
                return candidate
        return None

    if isinstance(payload, list):
        if payload and all(isinstance(row, list) for row in payload):
            # Ensure each row has the same length and the entries are numeric.
            width = len(payload[0])
            if all(len(row) == width for row in payload) and all(
                all(isinstance(cell, (int, float)) for cell in row) for row in payload
            ):
                return payload
        for item in payload:
            candidate = _extract_square(item)
            if candidate is not None:
                return candidate
        return None

    return None


def _extract_size(payload: Any) -> Optional[int]:
    """Find an integer field that likely represents the magic square order."""

    if isinstance(payload, dict):
        candidate_keys = ("n", "size", "squareSize", "order")
        for key in candidate_keys:
            value = payload.get(key)
            if isinstance(value, int) and value > 0:
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)
        for value in payload.values():
            result = _extract_size(value)
            if result is not None:
                return result
    return None


def _extract_debug(payload: Any) -> Optional[Any]:
    """Locate debug-style information for inclusion in the metadata payload."""

    if isinstance(payload, dict):
        for key in ("debug", "logs", "diagnostics", "metadata"):
            if key in payload:
                return payload[key]
        for value in payload.values():
            result = _extract_debug(value)
            if result is not None:
                return result
    return None


def _parse_magic_square_response(payload: Any, requested_size: int) -> MagicSquareResult:
    square_data = _extract_square(payload)
    if square_data is None:
        raise ValueError("Magic square data was not present in the service response.")

    array = np.array(square_data, dtype=float)
    if array.ndim != 2 or array.shape[0] != array.shape[1]:
        raise ValueError("Response did not contain a square matrix structure.")

    # Normalise integer values when possible so downstream consumers get clean
    # integer matrices but retain float information if required.
    if np.allclose(array, np.rint(array)):
        array = np.rint(array).astype(int)

    resolved_size = requested_size or _extract_size(payload) or array.shape[0]
    if resolved_size != array.shape[0]:
        raise ValueError(
            "Mismatch between requested size and the matrix returned by the service."
        )

    metadata: Dict[str, Any] = {}
    if isinstance(payload, dict):
        metadata = dict(payload)
        debug_info = _extract_debug(metadata)
        if debug_info is not None:
            metadata.setdefault("debug", debug_info)
    else:
        metadata = {"response": payload}

    return MagicSquareResult(size=resolved_size, square=array, metadata=metadata)


app = FastMCP(
    name="Magic MCP",
    instructions=(
        "Generate magic squares using the hosted MATLAB service backing the "
        "Magic MCP demo."
    ),
    stateless_http=True,
)


@app.tool(
    title="Generate Magic Square",
    description="Generate an n x n magic square.",
)
def generate_magic_square(
    size: int = Field(description="The order of the magic square to generate."),
    debug: bool = Field(
        default=False,
        description="Return additional debug information from the backend service.",
    ),
) -> Dict[str, Any]:
    """Generate a magic square of *size* using the remote MATLAB API."""

    if size <= 0:
        raise ValueError("Magic square size must be a positive integer.")

    payload: Dict[str, Any] = {"n": size}
    if debug:
        payload["debug"] = True

    try:
        response: Response = requests.post(API_URL, json=payload, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:  # pragma: no cover - network guard
        raise RuntimeError("Failed to contact the MATLAB magic square service.") from exc

    try:
        data = response.json()
    except ValueError as exc:  # pragma: no cover - depends on remote service
        raise RuntimeError("Magic square service did not return valid JSON.") from exc

    result = _parse_magic_square_response(data, size)
    return result.as_dict()


if __name__ == "__main__":  # pragma: no cover - manual execution entry point
    app.run(transport="streamable-http")
