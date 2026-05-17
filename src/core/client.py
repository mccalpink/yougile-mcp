"""
HTTP client wrapper for YouGile API.
Handles requests, retries, rate limiting, and error handling.
"""

import asyncio
from typing import Optional, Dict, Any, Union
import httpx
from ..config import settings
from .auth import AuthManager
from .exceptions import (
    YouGileError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    NotFoundError,
)


class YouGileClient:
    """HTTP client for YouGile API with built-in error handling and retries."""
    
    def __init__(self, auth_manager: Optional[AuthManager] = None):
        self.auth_manager = auth_manager or AuthManager()
        self.base_url = settings.yougile_base_url
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(settings.yougile_timeout),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=100),
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    async def _auto_reinitialize(self):
        """Automatically reinitialize authentication if possible.

        Refreshes the legacy single-tenant credentials and propagates them to
        both the local AuthManager (so the current request can proceed) and
        the multi-tenant registry under the `default` slug (so subsequent
        tool calls that look up workspace='default' see the new key too).
        """
        if all([settings.yougile_email, settings.yougile_password, settings.yougile_company_id]):
            # Import here to avoid circular imports
            from .. import server
            from . import auth
            await server.initialize_auth()
            # Update local auth_manager with global credentials
            if auth.auth_manager.is_authenticated():
                self.auth_manager.set_credentials(
                    auth.auth_manager.api_key,
                    auth.auth_manager.company_id
                )
                # initialize_auth() already mirrors into the registry on
                # success; this is a defensive safety net in case the
                # control flow ever changes.
                try:
                    server._mirror_legacy_into_registry(
                        auth.auth_manager.api_key,
                        auth.auth_manager.company_id,
                    )
                except Exception:
                    # Mirroring is best-effort here; failure must not abort
                    # the in-flight request.
                    pass
    
    async def request(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make an authenticated request to YouGile API."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        
        # Use basic headers for auth endpoints, auth headers for others
        if path.startswith("/auth/") or path.startswith("/api-v2/auth/"):
            headers = self.auth_manager.get_basic_headers()
        else:
            # Auto-reinitialize if not authenticated
            if not self.auth_manager.is_authenticated():
                await self._auto_reinitialize()
            headers = self.auth_manager.get_auth_headers()
            
        full_url = f"/api-v2{path}" if not path.startswith("/api-v2") else path
        
        for attempt in range(settings.yougile_max_retries + 1):
            try:
                response = await self._client.request(
                    method=method,
                    url=full_url,
                    json=json,
                    params=params,
                    headers=headers,
                    **kwargs
                )
                
                return self._handle_response(response)
                
            except httpx.TimeoutException:
                if attempt == settings.yougile_max_retries:
                    raise YouGileError("Request timeout")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except httpx.NetworkError as e:
                if attempt == settings.yougile_max_retries:
                    raise YouGileError(f"Network error: {str(e)}")
                await asyncio.sleep(2 ** attempt)
        
        raise YouGileError("Max retries exceeded")
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Handle HTTP response and convert errors to exceptions.

        Error messages are augmented with actionable hints so the LLM can
        self-correct without an extra round-trip to read docs.
        """
        if response.status_code == 200 or response.status_code == 201:
            try:
                return response.json()
            except ValueError:
                return {"success": True, "data": response.text}

        # Handle error responses
        error_data = {}
        try:
            error_data = response.json()
        except ValueError:
            error_data = {"error": response.text or f"HTTP {response.status_code}"}

        # YouGile responses often carry both "error" and "message"; prefer
        # whichever is set, falling back to the HTTP status.
        api_error = error_data.get("error") or error_data.get("message") or f"HTTP {response.status_code}"
        path = response.request.url.path if response.request else ""

        if response.status_code == 401:
            hint = (
                "Authentication failed. Check the YOUGILE_KEY_<WORKSPACE> env "
                "var for the workspace you targeted (or YOUGILE_API_KEY for "
                "the legacy 'default' slug); the key may have been revoked, "
                "rotated, or never set. Use list_workspaces to confirm which "
                "slugs are configured."
            )
            raise AuthenticationError(f"{api_error}. {hint}")
        elif response.status_code == 403:
            hint = (
                "Permission denied. The API key targeting this workspace "
                "lacks access to the requested resource (project / board / "
                "user). Verify the key owner's role with get_me."
            )
            raise AuthorizationError(f"{api_error}. {hint}")
        elif response.status_code == 404:
            hint = (
                "Resource not found. If you expect it to exist, retry the "
                "matching list_* call with include_deleted=true (tasks, "
                "boards, columns, webhooks all support soft-delete), or "
                "verify the workspace slug is correct."
            )
            raise NotFoundError(f"{api_error}. {hint}")
        elif response.status_code == 429:
            hint = (
                "Rate limit exceeded (50 req/min per company). Wait ~60s "
                "before retrying. Avoid loops that call get_string_sticker / "
                "get_string_sticker_state per item — cache list_string_stickers."
            )
            raise RateLimitError(f"{api_error}. {hint}")
        elif response.status_code == 400 and "/tasks" in path:
            hint = (
                "Bad request to /tasks. Common causes: "
                "(1) deadline missing required blockedPoints=[] and links=[] "
                "(use set_task_deadline to auto-populate); "
                "(2) color value not in enum (must be one of task-primary, "
                "task-gray, task-red, task-pink, task-yellow, task-green, "
                "task-turquoise, task-blue, task-violet); "
                "(3) subtasks array contains non-UUID strings; "
                "(4) assigned array contains non-UUID strings; "
                "(5) stickers value not a string state-id (use '-' to detach, "
                "'empty' to clear)."
            )
            raise YouGileError(f"{api_error}. {hint}", status_code=400, details=error_data)
        elif response.status_code == 400:
            hint = (
                "Bad request. The API rejected the payload — check required "
                "fields and value formats against the OpenAPI schema."
            )
            raise YouGileError(f"{api_error}. {hint}", status_code=400, details=error_data)
        else:
            raise YouGileError(api_error, status_code=response.status_code, details=error_data)
    
    # Convenience methods
    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make GET request."""
        return await self.request("GET", path, params=params)
    
    async def post(self, path: str, json: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make POST request.""" 
        return await self.request("POST", path, json=json, params=params)
    
    async def put(self, path: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make PUT request."""
        return await self.request("PUT", path, json=json)
    
    async def delete(self, path: str) -> Dict[str, Any]:
        """Make DELETE request."""
        return await self.request("DELETE", path)