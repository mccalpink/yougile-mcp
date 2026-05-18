"""
Integration-тесты для active workspace feature.
Тестируют взаимодействие session_state + resolve_workspace + тулы.
НЕ требуют реального API: мокаем registry.get() -> FakeAuthManager.
Запуск: pytest tests/integration/test_active_workspace.py -m integration
"""
import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.core.session_state import set_active, clear_active, get_active, resolve_workspace
from src.core.session_state import _state
from src.core.exceptions import WorkspaceNotConfiguredError


pytestmark = pytest.mark.integration


class FakeSession:
    """Заглушка ServerSession для тестов: поддерживает __weakref__ (в отличие
    от bare object()), чем удовлетворяет ключу WeakKeyDictionary."""


def make_session():
    """Возвращает новый weakref-совместимый объект сессии."""
    return FakeSession()


def make_ctx(session_obj):
    ctx = MagicMock()
    ctx.session = session_obj
    return ctx


@pytest.fixture
def mock_registry():
    """Registry с тремя workspace'ами: default, main, team."""
    with patch('src.server.registry') as r:
        r.slugs.return_value = ["default", "main", "team"]
        r.get.return_value = MagicMock()
        yield r


@pytest.fixture
def mcp_tools():
    import sys; sys.path.insert(0, 'src')
    from src.server import mcp
    return mcp._tool_manager._tools


@pytest.fixture(autouse=True)
def cleanup_state():
    """Очистка глобального state до и после каждого теста."""
    _state.clear()
    yield
    _state.clear()


class TestActiveWorkspaceIntegration:

    def test_set_then_tools_use_active(self, mock_registry, mcp_tools):
        """
        Сценарий: set_active_workspace("main") -> list_projects() без workspace
        -> resolve_workspace возвращает "main".
        """
        session_obj = make_session()
        ctx = make_ctx(session_obj)
        set_active(session_obj, "main")
        result = resolve_workspace(None, ctx, mock_registry)
        assert result == "main"
        clear_active(session_obj)

    def test_different_sessions_isolated(self, mock_registry):
        """
        Два клиента с разными session объектами не влияют друг на друга.
        """
        session_1 = make_session()
        session_2 = make_session()
        ctx_1 = make_ctx(session_1)
        ctx_2 = make_ctx(session_2)

        set_active(session_1, "main")
        set_active(session_2, "team")

        assert resolve_workspace(None, ctx_1, mock_registry) == "main"
        assert resolve_workspace(None, ctx_2, mock_registry) == "team"

        clear_active(session_1)
        clear_active(session_2)

    def test_explicit_workspace_overrides_session_active(self, mock_registry):
        """
        session active = "main", но тул вызван с workspace="team" явно ->
        resolve_workspace возвращает "team".
        """
        session_obj = make_session()
        ctx = make_ctx(session_obj)
        set_active(session_obj, "main")

        result = resolve_workspace("team", ctx, mock_registry)
        assert result == "team"

        clear_active(session_obj)

    def test_no_session_active_uses_default(self, mock_registry):
        """
        Без set_active_workspace -> resolve_workspace возвращает "default".
        """
        session_obj = make_session()
        ctx = make_ctx(session_obj)
        # Не вызываем set_active
        result = resolve_workspace(None, ctx, mock_registry)
        assert result == "default"

    def test_explicit_default_overrides_session_main(self, mock_registry):
        """
        session active = "main", явный workspace="default" -> возвращает "default".
        """
        session_obj = make_session()
        ctx = make_ctx(session_obj)
        set_active(session_obj, "main")

        result = resolve_workspace("default", ctx, mock_registry)
        assert result == "default"

        clear_active(session_obj)

    def test_set_active_workspace_tool_stores_and_returns(self, mock_registry, mcp_tools):
        """
        Вызов set_active_workspace тула -> возвращает dict + сохраняет в session_state.
        """
        session_obj = make_session()
        ctx = make_ctx(session_obj)
        fn = mcp_tools['set_active_workspace'].fn
        result = asyncio.get_event_loop().run_until_complete(fn(slug="team", ctx=ctx))
        assert result["active_workspace"] == "team"
        assert get_active(session_obj) == "team"
        clear_active(session_obj)

    def test_get_active_workspace_tool_reflects_state(self, mock_registry, mcp_tools):
        """
        get_active_workspace возвращает то, что было установлено через set_active_workspace.
        """
        session_obj = make_session()
        ctx = make_ctx(session_obj)
        set_fn = mcp_tools['set_active_workspace'].fn
        get_fn = mcp_tools['get_active_workspace'].fn

        asyncio.get_event_loop().run_until_complete(set_fn(slug="main", ctx=ctx))
        result = asyncio.get_event_loop().run_until_complete(get_fn(ctx=ctx))

        assert result["active_workspace"] == "main"
        assert result["effective_workspace"] == "main"
        clear_active(session_obj)
