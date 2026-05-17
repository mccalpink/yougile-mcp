"""Smoke-тест: все read-тулы принимают include параметр без ошибки импорта."""
import inspect
import pytest


def test_task_tools_have_include_param():
    from src.yougile_mcp.tools.task_tools import (
        list_tasks_tool, get_task_tool, list_task_summaries_tool, get_tasks_by_date_tool
    )
    for fn in (list_tasks_tool, get_task_tool, list_task_summaries_tool, get_tasks_by_date_tool):
        params = inspect.signature(fn).parameters
        assert "include" in params, f"{fn.__name__} не имеет параметра include"
        assert "verbosity" in params, f"{fn.__name__} не имеет параметра verbosity"


def test_project_tools_have_include_param():
    from src.yougile_mcp.tools.project_tools import list_projects_tool, get_project_tool
    for fn in (list_projects_tool, get_project_tool):
        params = inspect.signature(fn).parameters
        assert "include" in params, f"{fn.__name__} не имеет параметра include"


def test_board_tools_have_include_param():
    from src.yougile_mcp.tools.board_tools import list_boards_tool, get_board_tool
    for fn in (list_boards_tool, get_board_tool):
        params = inspect.signature(fn).parameters
        assert "include" in params, f"{fn.__name__} не имеет параметра include"


def test_user_tools_have_include_param():
    from src.yougile_mcp.tools.user_tools import list_users_tool, get_user_tool, get_me_tool
    for fn in (list_users_tool, get_user_tool, get_me_tool):
        params = inspect.signature(fn).parameters
        assert "include" in params, f"{fn.__name__} не имеет параметра include"


def test_chat_tools_have_include_param():
    from src.yougile_mcp.tools.chat_tools import (
        list_group_chats_tool, get_group_chat_tool,
        get_chat_messages_tool, get_chat_message_tool, get_task_comments_tool,
    )
    for fn in (list_group_chats_tool, get_group_chat_tool,
               get_chat_messages_tool, get_chat_message_tool, get_task_comments_tool):
        params = inspect.signature(fn).parameters
        assert "include" in params, f"{fn.__name__} не имеет параметра include"


def test_sticker_tools_have_include_param():
    from src.yougile_mcp.tools.sticker_tools import list_string_stickers_tool, get_string_sticker_tool
    for fn in (list_string_stickers_tool, get_string_sticker_tool):
        params = inspect.signature(fn).parameters
        assert "include" in params, f"{fn.__name__} не имеет параметра include"


def test_webhook_tools_have_include_param():
    from src.yougile_mcp.tools.webhook_tools import list_webhooks_tool
    params = inspect.signature(list_webhooks_tool).parameters
    assert "include" in params
