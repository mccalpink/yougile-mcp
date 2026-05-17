"""
YouGile Files MCP tools.

File upload (1 endpoint):
- POST /upload-file   multipart/form-data
"""

import os
from typing import Dict, Any, Optional
from mcp.server.fastmcp import Context
from ...core.registry import registry
from ...core.client import YouGileClient
from ...core.exceptions import YouGileError, ValidationError
from ...api import files


async def upload_file_tool(
    workspace: str,
    path: str,
    filename: Optional[str] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """Upload a local file to YouGile.

    Args:
        workspace: workspace slug (see list_workspaces).
        path: absolute path to the file on the server filesystem.
        filename: override the name reported to YouGile (defaults to basename(path)).

    Returns:
        FileUploadDto: {"result": "ok", "url": "/user-data/...", "fullUrl": "https://..."}
    """
    try:
        if not path or not isinstance(path, str):
            raise ValidationError("path must be a non-empty string", field="path")
        path = path.strip()
        if not os.path.isabs(path):
            raise ValidationError(
                "path must be absolute (e.g. /tmp/file.png)", field="path"
            )
        if not os.path.exists(path):
            raise ValidationError(f"file not found: {path}", field="path")
        if not os.path.isfile(path):
            raise ValidationError(f"path is not a regular file: {path}", field="path")

        size = os.path.getsize(path)
        if ctx:
            await ctx.info(f"Uploading file: {path} ({size} bytes)")

        async with YouGileClient(registry.get(workspace)) as client:
            result = await files.upload_file_multipart(client, path, filename=filename)

        if ctx:
            await ctx.info(
                f"Successfully uploaded file. URL: {result.get('url') or result.get('fullUrl')}"
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
