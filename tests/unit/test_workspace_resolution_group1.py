"""
Проверяет что get_* и list_* тулы правильно разрешают workspace.
Тест без реального API-вызова — мокаем registry и session_state.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


TOOLS_GROUP1 = [
    "get_board", "get_chat_message", "get_column", "get_group_chat",
    "get_me", "get_project", "get_sprint_sticker_state", "get_string_sticker",
    "get_string_sticker_state", "get_task", "get_task_chat_subscribers",
    "get_task_comments", "get_user", "list_boards", "list_columns",
    "list_group_chats",
]


@pytest.fixture
def mock_registry():
    with patch('src.server.registry') as r:
        r.slugs.return_value = ["default", "main"]
        r.get.return_value = MagicMock()  # fake AuthManager
        yield r


def make_ctx(session_obj=None):
    ctx = MagicMock()
    ctx.session = session_obj or object()
    return ctx


class TestWorkspaceSignatureGroup1:
    def test_all_tools_have_optional_workspace(self):
        """Все тулы group1 имеют workspace: ... | None = None."""
        import inspect
        import sys; sys.path.insert(0, 'src')
        from src.server import mcp
        tools = mcp._tool_manager._tools
        for name in TOOLS_GROUP1:
            assert name in tools, f"Тул {name} не найден"
            sig = inspect.signature(tools[name].fn)
            assert 'workspace' in sig.parameters, f"{name}: нет workspace параметра"
            param = sig.parameters['workspace']
            assert param.default is None, (
                f"{name}: workspace default должен быть None, а не '{param.default}'"
            )
