"""Все файлы whitelist'а SKILL_FILES должны быть доступны через MCP
как concrete resources (не URI template) — fix Codex Round 2 new blocker.

FastMCP URI template `{path}` (RFC 6570 level 1) парсит только один
path segment — `references/tool-keys.md` не матчился. Поэтому каждый
файл регистрируется концертным URI программно.
"""
import asyncio

import pytest

import sys
sys.path.insert(0, "src")
from src.server import mcp  # noqa: E402
from src.yougile_mcp.resources.skill_template import SKILL_FILES  # noqa: E402


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.mark.parametrize("relpath", SKILL_FILES)
def test_skill_file_resource_readable(relpath):
    uri = f"yougile://skill-template/{relpath}"
    result = _run(mcp.read_resource(uri))
    # mcp.read_resource возвращает list[ReadResourceContents]
    contents = list(result)
    assert contents, f"No content returned for {uri}"
    text = contents[0].content
    assert isinstance(text, str)
    assert len(text) > 0


def test_no_skill_template_left_in_templates_registry():
    """Проверка что мы реально ушли от URI template и не оставили его
    параллельно concrete resources (двойная регистрация маскировала бы баг)."""
    template_uris = [
        t.uri_template for t in mcp._resource_manager._templates.values()
    ]
    assert not any("skill-template" in u for u in template_uris), (
        f"yougile://skill-template/{{path}} template ещё зарегистрирован: {template_uris}"
    )


def test_all_skill_files_in_resources_registry():
    """Все 8 файлов whitelist'а есть в _resources (concrete URI)."""
    registered = set(mcp._resource_manager._resources.keys())
    for relpath in SKILL_FILES:
        uri = f"yougile://skill-template/{relpath}"
        assert uri in registered, f"{uri} not registered as concrete resource"
