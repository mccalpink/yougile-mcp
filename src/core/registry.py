"""
AuthRegistry — multi-tenant authentication manager for YouGile MCP.

Holds one AuthManager per workspace slug. Each workspace = one YouGile company API key.
Loads configuration from environment variables on construction:

    YOUGILE_KEY_<SLUG>=<api-key>       # required, defines the workspace
    YOUGILE_LABEL_<SLUG>="Human name"  # optional, for list_workspaces UI
    YOUGILE_COMPANY_<SLUG>=<uuid>      # optional, used by /auth/* re-init

Backwards compatibility: legacy single-tenant env (YOUGILE_API_KEY [+ YOUGILE_COMPANY_ID])
becomes workspace slug "default".

Slug normalization: env suffix is lower-cased; underscore stays underscore.
Examples:
    YOUGILE_KEY_MAIN          → slug "main"
    YOUGILE_KEY_CLIENT_ACME   → slug "client_acme"
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .auth import AuthManager
from .exceptions import ValidationError

_KEY_RE = re.compile(r"^YOUGILE_KEY_(.+)$")
_LABEL_RE = re.compile(r"^YOUGILE_LABEL_(.+)$")
_COMPANY_RE = re.compile(r"^YOUGILE_COMPANY_(.+)$")

LEGACY_SLUG = "default"


def _load_env_with_dotenv() -> dict:
    """Merge process env with .env file values. Process env wins on conflict.

    Without this, ``AuthRegistry`` would only see variables that the shell
    exported. Pydantic Settings reads ``.env`` into its own instance but does
    *not* mutate ``os.environ``, so the registry would miss every
    ``YOUGILE_KEY_*`` defined only in ``.env``.
    """
    merged: dict = {}
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        try:
            from dotenv import dotenv_values

            for k, v in dotenv_values(env_path).items():
                if v is not None:
                    merged[k] = v
        except ImportError:
            # python-dotenv not installed; rely on real env only
            pass
    # Real environment always wins over .env values
    merged.update(os.environ)
    return merged


class WorkspaceNotConfiguredError(ValidationError):
    """Raised when a tool requests a workspace slug that has no API key configured."""

    def __init__(self, slug: str, available: list[str]):
        msg = (
            f"Workspace '{slug}' is not configured. "
            f"Available workspaces: {sorted(available) or '(none)'}. "
            f"Set YOUGILE_KEY_{slug.upper()}=<api-key> in .env."
        )
        super().__init__(msg, field="workspace")
        self.slug = slug
        self.available = sorted(available)


@dataclass
class WorkspaceInfo:
    """Public, secret-free description of a configured workspace."""

    slug: str
    label: Optional[str]
    has_company_id: bool

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "label": self.label or self.slug,
            "has_company_id": self.has_company_id,
        }


class AuthRegistry:
    """
    Multi-tenant registry of YouGile API keys.

    One instance per process. Read environment exactly once at construction;
    callers may reload() if env changes (test scenarios).
    """

    def __init__(self, env: Optional[dict] = None) -> None:
        self._managers: dict[str, AuthManager] = {}
        self._labels: dict[str, Optional[str]] = {}
        self._load(env if env is not None else _load_env_with_dotenv())

    # ----- public API -----

    def get(self, workspace: str = LEGACY_SLUG) -> AuthManager:
        """Return the AuthManager for the given workspace slug.

        Raises WorkspaceNotConfiguredError if slug is unknown.
        """
        slug = self._normalize(workspace)
        if slug not in self._managers:
            raise WorkspaceNotConfiguredError(slug, list(self._managers.keys()))
        return self._managers[slug]

    def list_workspaces(self) -> list[WorkspaceInfo]:
        """Return public metadata for all configured workspaces (no keys)."""
        return [
            WorkspaceInfo(
                slug=slug,
                label=self._labels.get(slug),
                has_company_id=bool(self._managers[slug].company_id),
            )
            for slug in sorted(self._managers.keys())
        ]

    def has(self, workspace: str) -> bool:
        return self._normalize(workspace) in self._managers

    def slugs(self) -> list[str]:
        return sorted(self._managers.keys())

    def reload(self, env: Optional[dict] = None) -> None:
        """Drop existing state and re-read environment. Mainly for tests."""
        self._managers.clear()
        self._labels.clear()
        self._load(env if env is not None else _load_env_with_dotenv())

    # ----- helpers -----

    @staticmethod
    def _normalize(slug: str) -> str:
        if not slug or not slug.strip():
            raise ValidationError("Workspace slug cannot be empty", field="workspace")
        return slug.strip().lower()

    def _load(self, env: dict) -> None:
        # 1. Multi-tenant keys
        labels: dict[str, str] = {}
        company_ids: dict[str, str] = {}
        for name, value in env.items():
            if not value:
                continue
            if m := _KEY_RE.match(name):
                slug = m.group(1).lower()
                if slug in self._managers:
                    # Case-collision is a configuration bug — silently dropping
                    # one of the keys would route tool calls to the wrong
                    # company. Fail loud at startup instead.
                    collisions = [
                        n for n in env.keys()
                        if _KEY_RE.match(n) and _KEY_RE.match(n).group(1).lower() == slug
                    ]
                    raise ValueError(
                        f"Duplicate workspace slug '{slug}' from env vars "
                        f"{sorted(collisions)}. Slug comparison is "
                        f"case-insensitive — rename one of the env vars "
                        f"to avoid silent routing to the wrong company."
                    )
                self._managers[slug] = AuthManager(api_key=value.strip())
            elif m := _LABEL_RE.match(name):
                labels[m.group(1).lower()] = value.strip()
            elif m := _COMPANY_RE.match(name):
                company_ids[m.group(1).lower()] = value.strip()

        # Attach labels and company ids that have a matching key
        for slug, label in labels.items():
            if slug in self._managers:
                self._labels[slug] = label
        for slug, cid in company_ids.items():
            if slug in self._managers:
                self._managers[slug].set_credentials(
                    self._managers[slug].api_key, cid
                )

        # 2. Legacy single-tenant env → slug "default"
        legacy_key = env.get("YOUGILE_API_KEY")
        legacy_cid = env.get("YOUGILE_COMPANY_ID")
        if legacy_key:
            if LEGACY_SLUG in self._managers:
                # already provided as YOUGILE_KEY_DEFAULT — prefer explicit
                pass
            else:
                mgr = AuthManager(api_key=legacy_key.strip())
                if legacy_cid:
                    mgr.set_credentials(legacy_key.strip(), legacy_cid.strip())
                self._managers[LEGACY_SLUG] = mgr
                # If user gave a label for "default", apply
                if LEGACY_SLUG not in self._labels and "YOUGILE_LABEL_DEFAULT" in env:
                    self._labels[LEGACY_SLUG] = env["YOUGILE_LABEL_DEFAULT"]


# Global instance (lazy-init pattern would force every import path through a
# function; the registry is cheap, so just construct on import).
registry = AuthRegistry()
