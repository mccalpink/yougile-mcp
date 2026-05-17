#!/usr/bin/env python3
"""
YouGile MCP server entry point.

Usage:
    python run_server.py                  # stdio (default, backwards-compatible)
    python run_server.py --http           # streamable HTTP on YOUGILE_HOST:YOUGILE_PORT
    YOUGILE_TRANSPORT=http python ...     # same, via env

HTTP env vars:
    YOUGILE_HOST=127.0.0.1   (default)
    YOUGILE_PORT=3000        (default)
    YOUGILE_HTTP_PATH=/mcp   (default)

Run one HTTP server per host and point all MCP clients at its URL — this avoids
spinning up one Python interpreter per Claude/Cursor/IDE session (~90 MB each).
"""

import os
import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))


def _resolve_transport() -> str:
    if "--http" in sys.argv:
        return "http"
    if "--stdio" in sys.argv:
        return "stdio"
    return os.environ.get("YOUGILE_TRANSPORT", "stdio").lower()


def main() -> None:
    transport = _resolve_transport()

    # Import after sys.path manipulation
    from src.server import mcp, run_legacy_init

    # Legacy single-tenant auto-init (only if YOUGILE_API_KEY / EMAIL+PASSWORD set).
    # Multi-tenant workspaces from YOUGILE_KEY_<SLUG> are loaded eagerly by the
    # registry on import — no async work needed there.
    run_legacy_init()

    if transport == "http":
        host = os.environ.get("YOUGILE_HOST", "127.0.0.1")
        port = int(os.environ.get("YOUGILE_PORT", "3000"))
        path = os.environ.get("YOUGILE_HTTP_PATH", "/mcp")
        try:
            mcp.settings.host = host
            mcp.settings.port = port
            mcp.settings.streamable_http_path = path
        except AttributeError:
            # Older FastMCP — fall through; mcp.run() will use its own defaults.
            pass
        print(
            f"[yougile-mcp] starting streamable HTTP on http://{host}:{port}{path}",
            file=sys.stderr,
        )
        mcp.run(transport="streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
