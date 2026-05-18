"""Quick assertions on the contents of the API Usage Guide prompt.

The prompt is what agents pull via `prompts/get api_usage_guide` to learn
how to drive this MCP. If a key concept disappears from the text, agents
will silently miss it — these checks pin the most load-bearing topics.
"""
import sys

sys.path.insert(0, "src")

from src.server import mcp  # noqa: E402
from src.yougile_mcp.prompts.workflow_prompts import (  # noqa: E402
    api_usage_guide_prompt,
)


def test_prompt_registered_and_counts():
    """Tool / resource / prompt totals — agents inspect prompts/list."""
    assert len(mcp._tool_manager._tools) == 59
    assert len(mcp._resource_manager._resources) == 11
    assert len(mcp._prompt_manager._prompts) == 12
    assert "api_usage_guide" in mcp._prompt_manager._prompts


def test_prompt_covers_multi_tenant_and_active_workspace():
    text = api_usage_guide_prompt()
    assert "list_workspaces" in text
    assert "set_active_workspace" in text
    assert "get_active_workspace" in text
    assert "YOUGILE_KEY_" in text


def test_prompt_covers_verbosity_and_include():
    text = api_usage_guide_prompt()
    assert "verbosity" in text
    for level in ("compact", "full", "custom"):
        assert level in text
    assert "include[]" in text or 'include=["' in text


def test_prompt_covers_describe_response():
    text = api_usage_guide_prompt()
    assert "describe_response" in text


def test_prompt_covers_skill_install_via_resources():
    text = api_usage_guide_prompt()
    assert "setup_yougile_skill" in text
    assert "yougile://skill-template" in text
    assert "sha256" in text
    assert "briefing.md" in text
    # MCP не пишет на диск
    assert "never writes" in text.lower() or "not write" in text.lower()


def test_prompt_covers_quirks_and_html_and_pitfalls():
    text = api_usage_guide_prompt()
    text_lower = text.lower()
    assert "normalis" in text_lower or "auto-heal" in text_lower
    assert "HTML" in text
    assert "<br>" in text
    assert "MILLISECOND" in text.upper()
