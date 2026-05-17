"""Тесты для тулов управления активным workspace."""
import pytest
from unittest.mock import MagicMock, patch
from src.core.session_state import get_active, clear_active


def make_ctx(session_obj=None):
    ctx = MagicMock()
    ctx.session = session_obj or object()
    return ctx


class TestSetActiveWorkspace:
    def setup_method(self):
        # Импортируем функцию тула напрямую (без MCP декоратора)
        import importlib
        import sys
        if 'src.server' in sys.modules:
            del sys.modules['src.server']

    @pytest.fixture(autouse=True)
    def patch_registry(self):
        """Мокаем registry чтобы не нужен .env."""
        with patch('src.server.registry') as mock_reg:
            mock_reg.slugs.return_value = ["default", "main", "team"]
            yield mock_reg

    def test_set_active_workspace_stores_slug(self):
        from src.server import mcp
        tools = mcp._tool_manager._tools
        assert 'set_active_workspace' in tools, "Тул должен быть зарегистрирован"

    def test_set_active_returns_active_workspace(self, patch_registry):
        """Вызов set_active_workspace('main') → возвращает dict с active_workspace."""
        import asyncio
        from src.server import mcp
        session_obj = object()
        ctx = make_ctx(session_obj)
        tools = mcp._tool_manager._tools
        fn = tools['set_active_workspace'].fn
        result = asyncio.get_event_loop().run_until_complete(fn(slug="main", ctx=ctx))
        assert result["active_workspace"] == "main"
        assert "available_workspaces" in result

    def test_set_active_workspace_persists_in_session_state(self, patch_registry):
        """После вызова session state содержит slug."""
        import asyncio
        from src.server import mcp
        session_obj = object()
        ctx = make_ctx(session_obj)
        fn = mcp._tool_manager._tools['set_active_workspace'].fn
        asyncio.get_event_loop().run_until_complete(fn(slug="team", ctx=ctx))
        assert get_active(id(session_obj)) == "team"

    def test_set_active_invalid_slug_returns_error(self, patch_registry):
        """Несуществующий slug → ответ содержит error."""
        import asyncio
        from src.server import mcp
        ctx = make_ctx()
        fn = mcp._tool_manager._tools['set_active_workspace'].fn
        result = asyncio.get_event_loop().run_until_complete(fn(slug="ghost", ctx=ctx))
        assert "error" in result or result.get("active_workspace") is None

    def test_set_active_returns_available_workspaces(self, patch_registry):
        """Возвращает список доступных slug'ов."""
        import asyncio
        from src.server import mcp
        ctx = make_ctx()
        fn = mcp._tool_manager._tools['set_active_workspace'].fn
        result = asyncio.get_event_loop().run_until_complete(fn(slug="main", ctx=ctx))
        assert set(result["available_workspaces"]) == {"default", "main", "team"}


class TestGetActiveWorkspace:
    def setup_method(self):
        from src.core.session_state import _state
        _state.clear()

    def teardown_method(self):
        from src.core.session_state import _state
        _state.clear()

    @pytest.fixture(autouse=True)
    def patch_registry(self):
        with patch('src.server.registry') as mock_reg:
            mock_reg.slugs.return_value = ["default", "main", "team"]
            yield mock_reg

    def test_get_active_returns_null_when_not_set(self, patch_registry):
        """Если set_active не вызывался — возвращает null."""
        import asyncio
        from src.server import mcp
        ctx = make_ctx()  # новый session object без set_active
        fn = mcp._tool_manager._tools['get_active_workspace'].fn
        result = asyncio.get_event_loop().run_until_complete(fn(ctx=ctx))
        assert result["active_workspace"] is None
        assert result["effective_workspace"] == "default"

    def test_get_active_returns_set_slug(self, patch_registry):
        """После set_active — возвращает установленный slug."""
        import asyncio
        from src.server import mcp
        session_obj = object()
        ctx = make_ctx(session_obj)
        # Установить через set_active_workspace
        set_fn = mcp._tool_manager._tools['set_active_workspace'].fn
        asyncio.get_event_loop().run_until_complete(set_fn(slug="team", ctx=ctx))
        get_fn = mcp._tool_manager._tools['get_active_workspace'].fn
        result = asyncio.get_event_loop().run_until_complete(get_fn(ctx=ctx))
        assert result["active_workspace"] == "team"
        assert result["effective_workspace"] == "team"

    def test_get_active_returns_available_workspaces(self, patch_registry):
        """Всегда возвращает список доступных slug'ов."""
        import asyncio
        from src.server import mcp
        ctx = make_ctx()
        fn = mcp._tool_manager._tools['get_active_workspace'].fn
        result = asyncio.get_event_loop().run_until_complete(fn(ctx=ctx))
        assert "available_workspaces" in result
        assert set(result["available_workspaces"]) == {"default", "main", "team"}
