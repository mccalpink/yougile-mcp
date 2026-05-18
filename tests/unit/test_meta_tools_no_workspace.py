"""Тесты что мета-тулы (describe_response, setup_yougile_skill) НЕ требуют
configured workspace и НЕ падают с WorkspaceNotConfiguredError на чистом
сервере без YOUGILE_KEY_*.

См. review-fixes B3: эти тулы не делают API-вызовов, требовать workspace
было багом — ломало онбординг новых пользователей.
"""
import asyncio
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, "src")
from src.server import mcp  # noqa: E402


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def empty_registry():
    """AuthRegistry без единого ключа — имитирует свежеустановленный MCP."""
    with patch("src.server.registry") as r:
        r.slugs.return_value = []
        yield r


def test_describe_response_works_with_empty_registry(empty_registry):
    fn = mcp._tool_manager._tools["describe_response"].fn
    result = _run(fn(entity="task"))
    assert "entity" in result
    assert result["entity"] == "task"


def test_describe_response_overview_works_with_empty_registry(empty_registry):
    fn = mcp._tool_manager._tools["describe_response"].fn
    result = _run(fn())
    assert "entities" in result


def test_describe_response_ignores_workspace_arg(empty_registry):
    fn = mcp._tool_manager._tools["describe_response"].fn
    # Передаём заведомо не настроенный workspace — не должно падать.
    result = _run(fn(entity="task", workspace="nonexistent"))
    assert "entity" in result


def test_setup_yougile_skill_works_with_empty_registry(empty_registry):
    fn = mcp._tool_manager._tools["setup_yougile_skill"].fn
    result = _run(fn())
    assert "files" in result
    assert "default_target_dir" in result


def test_setup_yougile_skill_ignores_workspace_arg(empty_registry):
    fn = mcp._tool_manager._tools["setup_yougile_skill"].fn
    result = _run(fn(workspace="nonexistent"))
    assert "files" in result
