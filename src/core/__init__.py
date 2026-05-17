"""Core utilities for YouGile MCP server."""

from .auth import AuthManager
from .client import YouGileClient
from .exceptions import (
    YouGileError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
)
from .registry import (
    AuthRegistry,
    WorkspaceInfo,
    WorkspaceNotConfiguredError,
    LEGACY_SLUG,
    registry,
)
from . import models

# Legacy single-tenant manager.
# DEPRECATED: use `registry.get(workspace_slug)` instead.
# Kept for tools that haven't been migrated yet. If a "default" workspace
# is configured via env, mirror its credentials so legacy paths still work.
auth_manager = AuthManager()
if registry.has(LEGACY_SLUG):
    _default_mgr = registry.get(LEGACY_SLUG)
    if _default_mgr.api_key:
        auth_manager.set_credentials(
            _default_mgr.api_key,
            _default_mgr.company_id or "",
        )

__all__ = [
    "AuthManager",
    "AuthRegistry",
    "WorkspaceInfo",
    "WorkspaceNotConfiguredError",
    "LEGACY_SLUG",
    "registry",
    "YouGileClient",
    "YouGileError",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError",
    "models",
    "auth_manager",
]