"""
Проверяет backward compat: явный workspace побеждает session active.
Тесты напрямую проверяют resolve_workspace, не МCP тулы.
"""
import pytest
from unittest.mock import MagicMock
from src.core.session_state import resolve_workspace, set_active, clear_active
from src.core.session_state import _state
from src.core.exceptions import WorkspaceNotConfiguredError


class FakeRegistry:
    def __init__(self, slugs):
        self._slugs = slugs

    def slugs(self):
        return self._slugs


class FakeSession:
    """Fake-сессия, поддерживающая weakref."""
    pass


class TestBackwardCompat:
    def setup_method(self):
        self.registry = FakeRegistry(["default", "main", "team"])
        _state.clear()

    def teardown_method(self):
        _state.clear()

    def test_explicit_workspace_overrides_session_active(self):
        """workspace="team" при session active="main" → возвращает "team"."""
        session_obj = FakeSession()
        set_active(session_obj, "main")
        ctx = MagicMock()
        ctx.session = session_obj
        result = resolve_workspace("team", ctx, self.registry)
        assert result == "team"
        clear_active(session_obj)

    def test_explicit_default_overrides_session_active(self):
        """workspace="default" при session active="main" → возвращает "default"."""
        session_obj = FakeSession()
        set_active(session_obj, "main")
        ctx = MagicMock()
        ctx.session = session_obj
        result = resolve_workspace("default", ctx, self.registry)
        assert result == "default"
        clear_active(session_obj)

    def test_none_workspace_with_session_active_uses_active(self):
        """workspace=None при session active="team" → возвращает "team"."""
        session_obj = FakeSession()
        set_active(session_obj, "team")
        ctx = MagicMock()
        ctx.session = session_obj
        result = resolve_workspace(None, ctx, self.registry)
        assert result == "team"
        clear_active(session_obj)

    def test_none_workspace_no_session_uses_default(self):
        """workspace=None без session active → возвращает "default"."""
        ctx = MagicMock()
        ctx.session = FakeSession()  # нет set_active для этого объекта
        result = resolve_workspace(None, ctx, self.registry)
        assert result == "default"

    def test_none_workspace_no_ctx_uses_default(self):
        """workspace=None, ctx=None → возвращает "default" (тест без MCP контекста)."""
        result = resolve_workspace(None, None, self.registry)
        assert result == "default"
