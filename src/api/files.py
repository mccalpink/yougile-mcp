"""YouGile Files API client (1 endpoint)."""

import os
from typing import Dict, Any, Optional

import httpx

from ..core.client import YouGileClient
from ..core.exceptions import (
    YouGileError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
)
from ..config import settings


async def upload_file_multipart(
    client: YouGileClient,
    path: str,
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    """Upload a file from local filesystem via multipart/form-data.

    Reuses the open httpx.AsyncClient and auth headers from `YouGileClient`,
    but performs a direct request because YouGileClient.request always sends JSON.

    Returns the parsed FileUploadDto: {"result", "url", "fullUrl"}.
    """
    if not client._client:
        raise RuntimeError(
            "Client not initialized. Use 'async with YouGileClient(...)' context."
        )

    if not path or not isinstance(path, str):
        raise YouGileError("upload_file: 'path' must be a non-empty string")
    if not os.path.isfile(path):
        raise YouGileError(f"upload_file: file not found at path: {path}")

    # Re-initialize auth if needed (mirrors YouGileClient.request behaviour).
    if not client.auth_manager.is_authenticated():
        await client._auto_reinitialize()

    headers = client.auth_manager.get_auth_headers()
    # httpx sets the multipart Content-Type with boundary automatically; remove any default.
    headers = {k: v for k, v in headers.items() if k.lower() != "content-type"}

    fname = filename or os.path.basename(path)
    full_url = "/api-v2/upload-file"

    last_exc: Optional[Exception] = None
    for attempt in range(settings.yougile_max_retries + 1):
        try:
            with open(path, "rb") as fh:
                response = await client._client.post(
                    full_url,
                    headers=headers,
                    files={"file": (fname, fh)},
                )
            return _handle_upload_response(response)
        except httpx.TimeoutException as e:
            last_exc = e
            if attempt == settings.yougile_max_retries:
                raise YouGileError("Upload request timeout")
        except httpx.NetworkError as e:
            last_exc = e
            if attempt == settings.yougile_max_retries:
                raise YouGileError(f"Network error during upload: {str(e)}")
    # Fallback (should be unreachable)
    raise YouGileError(f"Upload failed after retries: {last_exc}")


def _handle_upload_response(response: httpx.Response) -> Dict[str, Any]:
    """Mirror of YouGileClient._handle_response, scoped to upload semantics."""
    if response.status_code in (200, 201):
        try:
            return response.json()
        except ValueError:
            return {"result": "ok", "data": response.text}

    error_data: Dict[str, Any] = {}
    try:
        error_data = response.json()
    except ValueError:
        error_data = {"error": response.text or f"HTTP {response.status_code}"}

    error_message = error_data.get("error", f"HTTP {response.status_code}")

    if response.status_code == 401:
        raise AuthenticationError(error_message)
    if response.status_code == 403:
        raise AuthorizationError(error_message)
    if response.status_code == 404:
        raise NotFoundError(error_message)
    if response.status_code == 429:
        raise RateLimitError(error_message)
    raise YouGileError(error_message, status_code=response.status_code, details=error_data)
