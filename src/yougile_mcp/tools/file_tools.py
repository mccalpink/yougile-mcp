"""
YouGile Files MCP tools.

File upload (1 endpoint):
- POST /upload-file   multipart/form-data
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from mcp.server.fastmcp import Context
from ...core.registry import registry
from ...core.client import YouGileClient
from ...core.exceptions import YouGileError, ValidationError
from ...api import files


# ---------------------------------------------------------------------------
# Path validation — prevent the agent from exfiltrating .env, SSH keys, etc.
# ---------------------------------------------------------------------------

_BLOCKED_PATH_PATTERNS = (
    "credentials",
    "secret",
    "password",
    ".env",
    ".ssh",
    "private_key",
)


def _get_upload_roots() -> list[Path]:
    """Return the list of directories from which uploads are allowed.

    Override with YOUGILE_UPLOAD_ROOTS=/dir1:/dir2 (colon-separated). Defaults
    to the user's home directory — NEVER allow root '/'.
    """
    raw = os.environ.get("YOUGILE_UPLOAD_ROOTS")
    if raw:
        return [
            Path(p).expanduser().resolve()
            for p in raw.split(":")
            if p.strip()
        ]
    return [Path.home().resolve()]


def _validate_upload_path(path: str) -> Path:
    """Canonicalize and validate `path` before reading the file.

    Raises ValidationError if the path is outside the configured allowlist,
    is a dotfile, or matches a sensitive-name pattern. The error message uses
    only the basename — never the full path — so it cannot leak filesystem
    layout via tool output.
    """
    if not path or not isinstance(path, str):
        raise ValidationError("path must be a non-empty string", field="path")

    p = Path(path).expanduser().resolve()

    if not p.exists():
        raise ValidationError(f"File '{p.name}' not found", field="path")
    if not p.is_file():
        raise ValidationError(
            f"'{p.name}' is not a regular file", field="path"
        )

    roots = _get_upload_roots()
    if not any(str(p).startswith(str(root) + os.sep) or str(p) == str(root) for root in roots):
        raise ValidationError(
            f"Path '{p.name}' is outside the allowed upload roots or matches "
            f"a blocked pattern. Configure YOUGILE_UPLOAD_ROOTS=/dir1:/dir2 "
            f"to allow specific directories.",
            field="path",
        )

    if p.name.startswith("."):
        raise ValidationError(
            f"Dotfile uploads are blocked ('{p.name}')", field="path"
        )

    path_lower = str(p).lower()
    for pat in _BLOCKED_PATH_PATTERNS:
        if pat in path_lower:
            raise ValidationError(
                f"Path matches blocked pattern '{pat}'. Move the file out of "
                f"sensitive-named directories first.",
                field="path",
            )

    return p


async def upload_file_tool(
    path: str,
    filename: Optional[str] = None,
    workspace: str = "default",
    ctx: Context = None,
) -> Dict[str, Any]:
    """Upload a local file to YouGile.

    Args:
        workspace: workspace slug (see list_workspaces).
        path: absolute path to the file on the server filesystem. Must reside
            inside one of the directories listed in YOUGILE_UPLOAD_ROOTS
            (defaults to the user's home directory). Dotfiles and paths whose
            name suggests secrets (`credentials`, `secret`, `password`,
            `.env`, `.ssh`, `private_key`) are rejected.
        filename: override the name reported to YouGile (defaults to basename(path)).

    Returns:
        FileUploadDto: {"result": "ok", "url": "/user-data/...", "fullUrl": "https://..."}
    """
    try:
        path = path.strip() if isinstance(path, str) else path
        resolved = _validate_upload_path(path)

        size = resolved.stat().st_size
        if ctx:
            # Log basename only — never the resolved full path.
            await ctx.info(f"Uploading file '{resolved.name}' ({size} bytes)")

        async with YouGileClient(registry.get(workspace)) as client:
            result = await files.upload_file_multipart(
                client, str(resolved), filename=filename
            )

        if ctx:
            await ctx.info(
                f"Successfully uploaded '{resolved.name}'. URL: "
                f"{result.get('url') or result.get('fullUrl')}"
            )
        return result

    except ValidationError as e:
        if ctx:
            await ctx.error(f"Validation failed: {e.message}")
        raise
    except YouGileError as e:
        if ctx:
            await ctx.error(f"API error while uploading file: {e.message}")
        raise
    except Exception as e:
        if ctx:
            await ctx.error(f"Unexpected error: {str(e)}")
        raise
